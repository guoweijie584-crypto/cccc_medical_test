"""REST API for the glucose-management self-evolution demo."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.cccc_native.vendored_cccc import ensure_vendored_cccc_on_path

ensure_vendored_cccc_on_path()

from config.settings import PATIENT_DATA_FILE
from config.settings import mask_api_key, read_runtime_llm_settings, write_runtime_llm_settings
from src.agents import GlucoseManagementWorkflow
from src.evolution import EvaluatorAgent, build_ui_report, run_demo_evaluation
from src.evolution import get_evaluation_service, VALID_LABELS, VALID_FAILURE_TAGS
from src.evolution import HumanEvalEvolutionLoop
from src.llm_client import get_llm_client
from src.memory import get_memory_agent
from src.cccc_native.runtime_manager import (
    apply_llm_config_to_group,
    list_group_actors,
    list_native_groups,
    load_actor_llm_config,
    save_actor_llm_config,
    set_group_state,
    start_group,
    stop_group,
)

PROJECT_ROOT = Path(__file__).resolve().parent

app = FastAPI(
    title="Glucose Management Demo API",
    description="API for the multi-agent glucose-management self-evolution demo.",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsultationRequest(BaseModel):
    patient_id: str
    query: str


class LLMConfigRequest(BaseModel):
    api_key: str = ""
    api_base: str = ""
    model: str = ""
    clear_api_key: bool = False


class NativeActorLlmConfigRequest(BaseModel):
    default: Dict[str, str] = {}
    actors: Dict[str, Dict[str, str]] = {}


class NativeGroupActionRequest(BaseModel):
    target: str
    state: str = ""


class MemoryCreateRequest(BaseModel):
    patient_id: str
    category: str = "general"
    content: str
    priority: int = 3
    disclosure: str = ""


class MemoryUpdateRequest(BaseModel):
    content: str
    priority: Optional[int] = None
    disclosure: Optional[str] = None


class CreatePendingEvaluationRequest(BaseModel):
    patient_id: str
    query: str
    response: str
    expert_opinions: Dict[str, str] = {}


class SubmitEvaluationRequest(BaseModel):
    label: str  # GOOD / BAD / NEUTRAL / ERROR
    safety: Optional[str] = None
    personalized: Optional[bool] = None
    advice_direction: Optional[str] = None
    reviewer_notes: str = ""
    reviewer_id: str = ""
    failure_tags: List[str] = []


_report_lock = threading.Lock()
_cached_report: Optional[Dict[str, Any]] = None
_cached_report_mode: Optional[str] = None
_ui_report_path = PROJECT_ROOT / "tests" / "output" / "latest_demo" / "ui_report.json"


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _pick_primary_record(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = raw.get(key)
    if isinstance(value, list) and value:
        first = value[0]
        return first if isinstance(first, dict) else {}
    return value if isinstance(value, dict) else {}


def _normalize_glucose_type(raw_type: str) -> str:
    text = str(raw_type or "").strip()
    if "空腹" in text:
        return "fasting"
    if "餐后" in text:
        return "post_meal"
    return "random"


def _load_raw_patients() -> List[Dict[str, Any]]:
    if not PATIENT_DATA_FILE.exists():
        return []
    payload = json.loads(PATIENT_DATA_FILE.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return list(payload.get("patients") or payload.get("data") or [])
    return []


def _normalize_patient(raw: Dict[str, Any]) -> Dict[str, Any]:
    patient_id = str(raw.get("患者UUID") or raw.get("patient_id") or "").strip()
    basic = dict(raw.get("基础信息") or {})
    patient_info = _pick_primary_record(basic, "u_patient")
    base_info = _pick_primary_record(basic, "u_patient_base_info")

    name = str(patient_info.get("姓名") or patient_info.get("name") or patient_id[-6:] or "Unknown").strip()
    age = _safe_int(patient_info.get("年龄") or base_info.get("年龄"), 0)
    gender = str(patient_info.get("性别") or patient_info.get("gender") or "未知").strip() or "未知"
    diabetes_type = str(
        base_info.get("糖尿病类型")
        or patient_info.get("糖尿病类型")
        or raw.get("糖尿病类型")
        or "2型"
    ).strip() or "2型"
    diagnosis_date = str(
        patient_info.get("发现糖尿病时间")
        or patient_info.get("诊断时间")
        or raw.get("诊断时间")
        or ""
    ).strip()

    glucose_history = []
    for record in _as_list(raw.get("血糖记录"))[-60:]:
        if not isinstance(record, dict):
            continue
        glucose_history.append(
            {
                "timestamp": str(record.get("记录时间") or record.get("timestamp") or "").strip(),
                "type": _normalize_glucose_type(str(record.get("测量类型") or record.get("type") or "")),
                "value": _safe_float(record.get("血糖值") or record.get("value"), 0.0),
                "note": str(record.get("备注") or record.get("note") or "").strip(),
            }
        )

    medications = []
    for med in _as_list(raw.get("用药信息")):
        if isinstance(med, dict):
            name_part = str(med.get("药品名称") or med.get("name") or "").strip()
            dose_part = str(med.get("剂量") or med.get("dosage") or "").strip()
            freq_part = str(med.get("频次") or med.get("frequency") or "").strip()
            label = " ".join(part for part in (name_part, dose_part, freq_part) if part).strip()
            if label:
                medications.append(label)
        elif str(med).strip():
            medications.append(str(med).strip())

    complications_raw = base_info.get("并发症") or raw.get("并发症") or []
    if isinstance(complications_raw, str):
        complications = [part.strip() for part in complications_raw.replace("、", "，").split("，") if part.strip()]
    else:
        complications = [str(item).strip() for item in _as_list(complications_raw) if str(item).strip()]

    return {
        "id": patient_id,
        "name": name,
        "age": age,
        "gender": gender,
        "diabetesType": diabetes_type,
        "diagnosisDate": diagnosis_date,
        "glucoseHistory": glucose_history,
        "medications": medications,
        "complications": complications,
        "rawProfile": raw,
    }


def load_patients() -> List[Dict[str, Any]]:
    patients: List[Dict[str, Any]] = []
    for item in _load_raw_patients():
        normalized = _normalize_patient(item)
        if normalized.get("id"):
            patients.append(normalized)
    return patients


def get_patient_by_id(patient_id: str) -> Dict[str, Any]:
    for patient in load_patients():
        if patient["id"] == patient_id:
            return patient
    raise HTTPException(status_code=404, detail=f"patient not found: {patient_id}")


def serialize_patient(patient: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in patient.items() if key != "rawProfile"}


def get_workflow() -> GlucoseManagementWorkflow:
    llm_client = get_llm_client()
    return GlucoseManagementWorkflow(use_mock=not llm_client.available, llm_client=llm_client)


def _safe_update_patient_profile(memory_agent: Any, patient_id: str, patient: Dict[str, Any]) -> Optional[str]:
    glucose_history = list(patient.get("glucoseHistory") or [])
    snapshot = {
        "id": patient.get("id"),
        "name": patient.get("name"),
        "age": patient.get("age"),
        "gender": patient.get("gender"),
        "diabetesType": patient.get("diabetesType"),
        "diagnosisDate": patient.get("diagnosisDate"),
        "medications": list(patient.get("medications") or [])[:10],
        "complications": list(patient.get("complications") or [])[:10],
        "glucoseRecent": glucose_history[-5:],
    }
    try:
        ok = memory_agent.update_patient_profile(patient_id, {"patient_snapshot": snapshot})
        if ok:
            return None
        return "memory profile update returned false"
    except Exception as exc:
        return str(exc)


def _safe_list_patient_memories(memory_agent: Any, patient_id: str, limit: int = 20) -> tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        memories = memory_agent.list_patient_memories(patient_id, limit=limit)
        return list(memories or []), None
    except Exception as exc:
        return [], str(exc)


def serialize_llm_config() -> Dict[str, Any]:
    settings = read_runtime_llm_settings()
    client = get_llm_client()
    return {
        "configured": bool(settings.get("api_key")),
        "apiKeyPreview": mask_api_key(settings.get("api_key", "")),
        "apiBase": settings.get("api_base", ""),
        "model": settings.get("model", ""),
        "mode": "llm" if client.available else "mock",
    }


def serialize_native_llm_config() -> Dict[str, Any]:
    raw = load_actor_llm_config()
    default = dict(raw.get("default") or {})
    actors = dict(raw.get("actors") or {})
    return {
        "default": {
            "configured": bool(default.get("api_key")),
            "apiKeyPreview": mask_api_key(default.get("api_key", "")),
            "apiBase": default.get("api_base", ""),
            "model": default.get("model", ""),
        },
        "actors": {
            actor_id: {
                "configured": bool((cfg or {}).get("api_key")),
                "apiKeyPreview": mask_api_key((cfg or {}).get("api_key", "")),
                "apiBase": (cfg or {}).get("api_base", ""),
                "model": (cfg or {}).get("model", ""),
            }
            for actor_id, cfg in actors.items()
        },
    }


def _memory_briefs(memory_context: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    for bucket in ("recent_memories", "session_history"):
        for entry in memory_context.get(bucket, [])[:3]:
            content = entry.get("content") if isinstance(entry, dict) else entry
            if isinstance(content, dict):
                text = str(content.get("content") or content.get("raw") or "").strip()
                category = str(content.get("category") or "memory").strip()
                items.append(f"[{category}] {text}")
            elif isinstance(entry, dict) and isinstance(entry.get("content"), str):
                items.append(str(entry["content"]).strip())
            elif str(entry).strip():
                items.append(str(entry).strip())
    deduped: List[str] = []
    for item in items:
        if item and item not in deduped:
            deduped.append(item)
    return deduped[:6]


def get_cached_ui_report(refresh: bool = False) -> Dict[str, Any]:
    global _cached_report, _cached_report_mode
    if not refresh and _cached_report is not None:
        return _cached_report
    if not refresh and _ui_report_path.exists():
        _cached_report = json.loads(_ui_report_path.read_text(encoding="utf-8"))
        return _cached_report
    with _report_lock:
        if not refresh and _cached_report is not None:
            return _cached_report
        run_result = run_demo_evaluation(iterations=2, case_limit=5, export=True)
        _cached_report = build_ui_report(run_result)
        _cached_report_mode = run_result.get("mode")
        _ui_report_path.parent.mkdir(parents=True, exist_ok=True)
        _ui_report_path.write_text(json.dumps(_cached_report, ensure_ascii=False, indent=2), encoding="utf-8")
        return _cached_report


@app.get("/api/patients")
async def api_get_patients() -> Dict[str, Any]:
    return {"patients": [serialize_patient(patient) for patient in load_patients()]}


@app.get("/api/patients/{patient_id}")
async def api_get_patient(patient_id: str) -> Dict[str, Any]:
    return serialize_patient(get_patient_by_id(patient_id))


@app.get("/api/patients/{patient_id}/memories")
async def api_get_patient_memories(patient_id: str) -> Dict[str, Any]:
    patient = get_patient_by_id(patient_id)
    memory_agent = get_memory_agent()
    memory_error = _safe_update_patient_profile(memory_agent, patient_id, patient)
    memories, list_error = _safe_list_patient_memories(memory_agent, patient_id, limit=20)
    normalized = []
    for item in memories:
        content = item.get("content") if isinstance(item, dict) else {}
        if isinstance(content, dict):
            normalized.append(
                {
                    "id": item.get("uri"),
                    "category": content.get("category", "memory"),
                    "content": content.get("content") or content.get("raw") or "",
                    "timestamp": content.get("timestamp") or item.get("timestamp") or "",
                }
            )
    errors = [msg for msg in (memory_error, list_error) if msg]
    response: Dict[str, Any] = {"memories": normalized}
    if errors:
        response["memoryStatus"] = "degraded"
        response["memoryError"] = "; ".join(errors)
    else:
        response["memoryStatus"] = "ok"
    return response


# ── Memory Palace API ───────────────────────────────────────────────


def _build_memory_tree_node(client: Any, path: str, depth: int = 0, max_depth: int = 3) -> Dict[str, Any]:
    """Recursively read a Memory Palace node and its children into a tree."""
    record = client.read(path)
    if not record:
        return {"path": path, "content": None, "children": []}

    content_raw = record.get("content")
    parsed: Dict[str, Any] = {}
    if isinstance(content_raw, str):
        try:
            parsed = json.loads(content_raw)
        except (json.JSONDecodeError, TypeError):
            parsed = {"raw": content_raw}
    elif isinstance(content_raw, dict):
        parsed = content_raw

    node: Dict[str, Any] = {
        "path": path,
        "uri": record.get("uri", ""),
        "content": parsed,
        "category": parsed.get("category", path.rsplit("/", 1)[-1] if "/" in path else path),
        "priority": (record.get("metadata") or {}).get("priority"),
        "disclosure": (record.get("metadata") or {}).get("disclosure", ""),
        "created_at": (record.get("metadata") or {}).get("created_at", ""),
        "children": [],
    }

    if depth < max_depth:
        for child in record.get("children") or []:
            child_path = child.get("path") if isinstance(child, dict) else str(child)
            if child_path:
                child_node = _build_memory_tree_node(client, child_path, depth + 1, max_depth)
                node["children"].append(child_node)

    return node


@app.get("/api/memory/tree/{patient_id}")
async def api_get_memory_tree(patient_id: str) -> Dict[str, Any]:
    """Get the full memory tree for a patient."""
    memory_agent = get_memory_agent()
    client = memory_agent.client
    root_path = f"patients/{patient_id}"
    tree = _build_memory_tree_node(client, root_path, depth=0, max_depth=3)
    return {"patient_id": patient_id, "tree": tree}


@app.get("/api/memory/search")
async def api_search_memories(
    q: str = Query(default="", description="Search query"),
    patient_id: Optional[str] = Query(default=None),
    max_results: int = Query(default=20, ge=1, le=100),
    mode: str = Query(default="hybrid"),
) -> Dict[str, Any]:
    """Search memories, optionally scoped to a patient."""
    memory_agent = get_memory_agent()
    if not q.strip():
        return {"results": [], "query": q, "count": 0}
    results = memory_agent.search_memories(
        query=q.strip(),
        patient_id=patient_id,
        max_results=max_results,
    )
    normalized = []
    for item in results:
        content = item.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"raw": content}
        normalized.append({
            "uri": item.get("uri", ""),
            "path": item.get("path", ""),
            "content": content,
            "category": content.get("category", "memory") if isinstance(content, dict) else "memory",
            "score": item.get("score", 0),
            "snippet": item.get("snippet", ""),
        })
    return {"results": normalized, "query": q, "count": len(normalized)}


@app.post("/api/memory/create")
async def api_create_memory(request: MemoryCreateRequest) -> Dict[str, Any]:
    """Create a new memory node for a patient."""
    memory_agent = get_memory_agent()
    client = memory_agent.client
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = f"patients/{request.patient_id}/{request.category}/{ts}"
    memory_content = {
        "patient_id": request.patient_id,
        "category": request.category,
        "content": request.content,
        "timestamp": datetime.now().isoformat(),
    }
    result = client.create(
        path=path,
        content=json.dumps(memory_content, ensure_ascii=False),
        priority=request.priority,
        disclosure=request.disclosure,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=str(result["error"]))
    return {
        "status": "created",
        "path": path,
        "uri": result.get("uri", ""),
        "node": memory_content,
    }


@app.put("/api/memory/{path:path}")
async def api_update_memory(path: str, request: MemoryUpdateRequest) -> Dict[str, Any]:
    """Update an existing memory node's content and/or metadata."""
    memory_agent = get_memory_agent()
    client = memory_agent.client
    result = client.update(
        path=path,
        content=request.content,
        priority=request.priority,
        disclosure=request.disclosure,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=str(result["error"]))
    return {
        "status": "updated",
        "path": path,
        "uri": result.get("uri", ""),
    }


@app.delete("/api/memory/{path:path}")
async def api_delete_memory(path: str) -> Dict[str, Any]:
    """Delete a memory node."""
    memory_agent = get_memory_agent()
    client = memory_agent.client
    ok = client.delete(path=path)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete memory node")
    return {"status": "deleted", "path": path}


@app.get("/api/memory/stats")
async def api_get_memory_stats(
    patient_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Get memory statistics for a patient or globally."""
    memory_agent = get_memory_agent()
    client = memory_agent.client

    categories = ["profile", "consultations", "medications", "glucose", "diet", "alerts"]
    stats: Dict[str, Any] = {"total": 0, "categories": {}}

    if patient_id:
        root_path = f"patients/{patient_id}"
        root = client.read(root_path)
        if root:
            children = root.get("children") or []
            for child in children:
                child_path = child.get("path") if isinstance(child, dict) else str(child)
                if not child_path:
                    continue
                cat_name = child_path.rsplit("/", 1)[-1] if "/" in child_path else child_path
                child_record = client.read(child_path)
                count = len(child_record.get("children") or []) if child_record else 0
                stats["categories"][cat_name] = count
                stats["total"] += count
    else:
        # Global stats: count all patient roots
        patients_root = client.read("patients")
        if patients_root:
            patient_children = patients_root.get("children") or []
            stats["patient_count"] = len(patient_children)
            for pc in patient_children[:50]:
                pc_path = pc.get("path") if isinstance(pc, dict) else str(pc)
                if pc_path:
                    pc_record = client.read(pc_path)
                    if pc_record:
                        for cat_child in pc_record.get("children") or []:
                            cat_path = cat_child.get("path") if isinstance(cat_child, dict) else str(cat_child)
                            if cat_path:
                                cat_name = cat_path.rsplit("/", 1)[-1]
                                cat_record = client.read(cat_path)
                                count = len(cat_record.get("children") or []) if cat_record else 0
                                stats["categories"][cat_name] = stats["categories"].get(cat_name, 0) + count
                                stats["total"] += count

    return stats


@app.post("/api/consultation")
async def api_create_consultation(request: ConsultationRequest) -> Dict[str, Any]:
    """DEPRECATED: Use CCCC work group API instead.

    The multi-agent consultation now runs through the CCCC work group
    (glucose-management-main / g_72244ae16d48) via:
      POST /api/v1/groups/g_72244ae16d48/send
      GET  /api/v1/groups/g_72244ae16d48/ledger/stream  (SSE)

    This endpoint is kept as a compatibility stub.
    """
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "error": "此接口已废弃。会诊功能已迁移至 CCCC 工作组。",
            "migration": "POST /api/v1/groups/g_72244ae16d48/send",
            "docs": "前端已自动使用新的 CCCC 协作 API。",
        },
    )


# ── Evaluation API (Human Doctor Evaluation) ──────────────────────


@app.post("/api/evaluations/pending")
async def api_create_pending_evaluation(request: CreatePendingEvaluationRequest) -> Dict[str, Any]:
    """Create a pending evaluation record after a consultation.

    Called by the system after each patient interaction.
    """
    service = get_evaluation_service()
    try:
        evaluation = service.create_pending_evaluation(
            patient_id=request.patient_id,
            query=request.query,
            response=request.response,
            expert_opinions=request.expert_opinions or {},
        )
        return {
            "status": "created",
            "evaluation_id": evaluation.evaluation_id,
            "evaluation": evaluation.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/evaluations/pending")
async def api_get_pending_evaluations(
    patient_id: str = Query(default="", description="Filter by patient ID"),
    limit: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    """Get pending evaluations for doctors to review."""
    service = get_evaluation_service()
    try:
        evaluations = service.get_pending_evaluations(limit=limit)
        # Filter by patient_id if provided
        if patient_id:
            evaluations = [e for e in evaluations if e.patient_id == patient_id]
        return {
            "evaluations": [e.to_dict() for e in evaluations],
            "count": len(evaluations),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/evaluations/{evaluation_id}/submit")
async def api_submit_evaluation(
    evaluation_id: str,
    request: SubmitEvaluationRequest,
) -> Dict[str, Any]:
    """Doctor submits an evaluation for a pending record."""
    service = get_evaluation_service()
    try:
        evaluation = service.submit_evaluation(
            evaluation_id=evaluation_id,
            label=request.label,
            safety=request.safety,
            personalized=request.personalized,
            advice_direction=request.advice_direction,
            reviewer_notes=request.reviewer_notes,
            reviewer_id=request.reviewer_id,
            failure_tags=request.failure_tags or None,
        )
        return {
            "status": "submitted",
            "evaluation_id": evaluation.evaluation_id,
            "label": evaluation.label,
            "evaluation": evaluation.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/evaluations/stats")
async def api_get_evaluation_stats(
    patient_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Get aggregated evaluation statistics."""
    service = get_evaluation_service()
    try:
        stats = service.get_evaluation_stats(patient_id=patient_id)
        return stats.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/evaluations/bad")
async def api_get_bad_evaluations(
    limit: int = Query(default=10, ge=1, le=100),
) -> Dict[str, Any]:
    """Get recent BAD and ERROR evaluations for self-evolution analysis."""
    service = get_evaluation_service()
    try:
        evaluations = service.get_bad_evaluations(limit=limit)
        return {
            "evaluations": [e.to_dict() for e in evaluations],
            "count": len(evaluations),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/evaluations/failure-tags")
async def api_get_failure_tags() -> Dict[str, Any]:
    """Return all valid failure classification tags."""
    return {"failure_tags": sorted(VALID_FAILURE_TAGS)}


@app.get("/api/traces/{trace_id}")
async def api_get_trace(trace_id: str) -> Dict[str, Any]:
    """Return a single consultation trace by trace_id."""
    import json as _json

    memory_agent = get_memory_agent()
    client = memory_agent.client
    path = f"traces/{trace_id}"
    record = client.read(path)
    if not record or "error" in record:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    content = record.get("content")
    if isinstance(content, str):
        try:
            content = _json.loads(content)
        except (_json.JSONDecodeError, TypeError):
            content = {"raw": content}
    elif not isinstance(content, dict):
        content = {}

    return {"trace_id": trace_id, "trace": content}


@app.get("/api/evaluations/{evaluation_id}")
async def api_get_evaluation(evaluation_id: str) -> Dict[str, Any]:
    """Get a single evaluation by ID."""
    service = get_evaluation_service()
    evaluation = service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id} not found")
    return evaluation.to_dict()


@app.get("/api/evolution/report")
async def api_get_evolution_report(refresh: bool = Query(default=False)) -> Dict[str, Any]:
    return get_cached_ui_report(refresh=refresh)


@app.get("/api/evolution/timeline")
async def api_get_evolution_timeline(refresh: bool = Query(default=False)) -> Dict[str, Any]:
    report = get_cached_ui_report(refresh=refresh)
    timeline = [
        {
            "iteration": item["iteration"],
            "timestamp": item["timestamp"],
            "overall_score": item["avgScore"],
            "medical_accuracy": item["medicalAccuracy"],
            "safety": item["safety"],
            "completeness": item["completeness"],
            "personalization": item["personalization"],
            "consistency": item["consistency"],
            "changes": [
                *(
                    [{"type": "prompt", "description": f"Optimized {item['promptChanges']} prompt(s)"}]
                    if item["promptChanges"]
                    else []
                ),
                *(
                    [{"type": "memory", "description": f"Changed {item['memoryChanges']} memory item(s)"}]
                    if item["memoryChanges"]
                    else []
                ),
            ],
        }
        for item in report.get("iterations", [])
    ]
    return {"iterations": timeline}


@app.post("/api/evolution/human-driven")
async def api_run_human_eval_evolution(
    limit: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    """Run one cycle of human-evaluation-driven optimization.

    Reads recent BAD/ERROR evaluations, analyzes root causes,
    and outputs prompt optimizations + memory reinforcements.
    """
    memory_agent = get_memory_agent()
    llm_client = get_llm_client()
    loop = HumanEvalEvolutionLoop(
        memory_agent=memory_agent,
        llm_client=llm_client if llm_client.available else None,
    )
    summary = loop.run(limit=limit)
    try:
        loop.export_results()
    except Exception:
        pass  # non-critical
    return summary.to_dict()


@app.get("/api/config/llm")
async def api_get_llm_config() -> Dict[str, Any]:
    return serialize_llm_config()


@app.put("/api/config/llm")
async def api_update_llm_config(request: LLMConfigRequest) -> Dict[str, Any]:
    write_runtime_llm_settings(
        api_key=request.api_key if request.api_key else None,
        api_base=request.api_base if request.api_base else None,
        model=request.model if request.model else None,
        clear_api_key=bool(request.clear_api_key),
    )
    # Recreate client on next access.
    _ = get_llm_client()
    return serialize_llm_config()


@app.get("/api/cccc-native/status")
async def api_get_cccc_native_status() -> Dict[str, Any]:
    return list_native_groups()


@app.get("/api/cccc-native/actors")
async def api_get_cccc_native_actors() -> Dict[str, Any]:
    status = list_native_groups()
    main_group_id = str((status.get("main_group") or {}).get("group_id") or "").strip()
    eval_group_id = str((status.get("evaluation_group") or {}).get("group_id") or "").strip()
    return {
        "main_group_id": main_group_id,
        "evaluation_group_id": eval_group_id,
        "main_group_actors": list_group_actors(main_group_id),
        "evaluation_group_actors": list_group_actors(eval_group_id),
    }


@app.get("/api/cccc-native/llm")
async def api_get_cccc_native_llm_config() -> Dict[str, Any]:
    return serialize_native_llm_config()


@app.put("/api/cccc-native/llm")
async def api_update_cccc_native_llm_config(request: NativeActorLlmConfigRequest) -> Dict[str, Any]:
    payload = save_actor_llm_config({"default": request.default, "actors": request.actors})
    status = list_native_groups()
    main_group = status.get("main_group") or {}
    eval_group = status.get("evaluation_group") or {}
    if main_group.get("group_id"):
        apply_llm_config_to_group(str(main_group["group_id"]), list(main_group.get("actor_ids") or []), payload)
    if eval_group.get("group_id"):
        apply_llm_config_to_group(str(eval_group["group_id"]), list(eval_group.get("actor_ids") or []), payload)
    return serialize_native_llm_config()


@app.post("/api/cccc-native/groups/start")
async def api_start_cccc_native_group(request: NativeGroupActionRequest) -> Dict[str, Any]:
    status = list_native_groups()
    group = status.get("main_group" if request.target == "main" else "evaluation_group") or {}
    group_id = str(group.get("group_id") or "").strip()
    if not group_id:
        raise HTTPException(status_code=404, detail=f"group not found for target={request.target}")
    return start_group(group_id)


@app.post("/api/cccc-native/groups/stop")
async def api_stop_cccc_native_group(request: NativeGroupActionRequest) -> Dict[str, Any]:
    status = list_native_groups()
    group = status.get("main_group" if request.target == "main" else "evaluation_group") or {}
    group_id = str(group.get("group_id") or "").strip()
    if not group_id:
        raise HTTPException(status_code=404, detail=f"group not found for target={request.target}")
    return stop_group(group_id)


@app.post("/api/cccc-native/groups/state")
async def api_set_cccc_native_group_state(request: NativeGroupActionRequest) -> Dict[str, Any]:
    status = list_native_groups()
    group = status.get("main_group" if request.target == "main" else "evaluation_group") or {}
    group_id = str(group.get("group_id") or "").strip()
    if not group_id:
        raise HTTPException(status_code=404, detail=f"group not found for target={request.target}")
    if request.state not in {"active", "idle", "paused"}:
        raise HTTPException(status_code=400, detail="invalid state")
    return set_group_state(group_id, request.state)


@app.get("/api/health")
async def api_health() -> Dict[str, Any]:
    llm_client = get_llm_client()
    memory_palace_status = "unreachable"
    try:
        import httpx

        with httpx.Client(timeout=1.0) as client:
            resp = client.get("http://127.0.0.1:8000/health")
            if resp.status_code == 200:
                memory_palace_status = "ok"
            else:
                memory_palace_status = f"http_{resp.status_code}"
    except Exception:
        memory_palace_status = "unreachable"
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "llm_mode": "llm" if llm_client.available else "mock",
        "memory_palace_url": "http://127.0.0.1:8000",
        "memory_palace_status": memory_palace_status,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
