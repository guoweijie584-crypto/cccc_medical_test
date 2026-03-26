"""Repo-side runtime diagnostics helpers for delivery stalls."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .runtime_gate import EventRef, load_ledger_events


@dataclass
class MemoryDeliveryDiagnostics:
    probe_event_id: str
    probe_line: int
    status: str
    active_probe_status: str
    reasons: List[str] = field(default_factory=list)
    memory_consults: List[EventRef] = field(default_factory=list)
    memory_reads: List[EventRef] = field(default_factory=list)
    memory_acks: List[EventRef] = field(default_factory=list)
    memory_replies: List[EventRef] = field(default_factory=list)
    memory_notifications: List[EventRef] = field(default_factory=list)
    cursor_event_id: str = ""
    cursor_line: int = 0
    cursor_stale: bool = False
    automation_nudge_keys: List[str] = field(default_factory=list)
    runner_pid: Optional[int] = None
    runner_alive: Optional[bool] = None
    superseding_event: Optional[EventRef] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def diagnose_memory_delivery(
    group_dir: str | Path,
    probe_event_id: str,
    *,
    pid_alive_fn: Optional[Callable[[int], bool]] = None,
) -> MemoryDeliveryDiagnostics:
    group_path = Path(group_dir)
    events = load_ledger_events(group_path / "ledger.jsonl")
    probe_id = str(probe_event_id or "").strip()
    if not probe_id:
        raise ValueError("probe_event_id is required")

    probe_index = -1
    for index, item in enumerate(events):
        if str(item.payload.get("id") or "").strip() == probe_id:
            probe_index = index
            break
    if probe_index < 0:
        raise ValueError(f"probe event not found: {probe_id}")

    probe_item = events[probe_index]
    event_line_by_id = {
        str(item.payload.get("id") or "").strip(): item.line
        for item in events
        if str(item.payload.get("id") or "").strip()
    }
    diagnostics = MemoryDeliveryDiagnostics(
        probe_event_id=probe_id,
        probe_line=probe_item.line,
        status="pending",
        active_probe_status="active",
    )

    consult_ids: set[str] = set()
    first_consult_line: Optional[int] = None

    for item in events[probe_index + 1 :]:
        payload = item.payload
        kind = str(payload.get("kind") or "").strip()
        by = str(payload.get("by") or "").strip()
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

        if kind == "chat.message" and by == "user":
            diagnostics.superseding_event = _event_ref(item)
            break
        if kind == "actor.restart":
            diagnostics.superseding_event = _event_ref(item)
            break

        if kind == "system.notify" and str(data.get("target_actor_id") or "").strip() == "memory":
            if first_consult_line is not None:
                diagnostics.memory_notifications.append(_event_ref(item))
            continue

        if kind == "chat.read":
            if str(data.get("actor_id") or "").strip() == "memory":
                event_id = str(data.get("event_id") or "").strip()
                if event_id in consult_ids:
                    diagnostics.memory_reads.append(_event_ref(item))
            continue

        if kind == "chat.ack":
            if by == "memory":
                event_id = str(data.get("event_id") or "").strip()
                if event_id in consult_ids:
                    diagnostics.memory_acks.append(_event_ref(item))
            continue

        if kind != "chat.message":
            continue

        event_ref = _event_ref(item)
        if by == "primary" and "memory" in _normalize_to_tokens(data):
            consult_ids.add(event_ref.event_id)
            diagnostics.memory_consults.append(event_ref)
            if first_consult_line is None:
                first_consult_line = item.line
            continue

        if by == "memory" and event_ref.reply_to in consult_ids:
            diagnostics.memory_replies.append(event_ref)

    diagnostics.active_probe_status = "stale" if diagnostics.superseding_event is not None else "active"
    diagnostics.cursor_event_id, diagnostics.cursor_line = _load_memory_cursor(group_path, event_line_by_id)
    diagnostics.cursor_stale = bool(
        first_consult_line and diagnostics.cursor_line and diagnostics.cursor_line < first_consult_line
    )
    diagnostics.automation_nudge_keys = _load_memory_automation_keys(group_path)
    diagnostics.runner_pid, diagnostics.runner_alive = _load_memory_runner(group_path, pid_alive_fn=pid_alive_fn)
    diagnostics.reasons = _build_reasons(diagnostics)
    diagnostics.status = _classify_status(diagnostics)
    return diagnostics


def _event_ref(item: Any) -> EventRef:
    payload = item.payload
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return EventRef(
        line=item.line,
        event_id=str(payload.get("id") or "").strip(),
        ts=str(payload.get("ts") or "").strip(),
        kind=str(payload.get("kind") or "").strip(),
        by=str(payload.get("by") or "").strip(),
        to=sorted(_normalize_to_tokens(data)),
        reply_to=str(data.get("reply_to") or "").strip(),
    )


def _normalize_to_tokens(data: Dict[str, Any]) -> set[str]:
    raw = data.get("to")
    if isinstance(raw, list):
        tokens = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        tokens = [raw.strip()] if raw.strip() else []
    else:
        tokens = []
    return {"user" if token == "@user" else token for token in tokens}


def _load_memory_cursor(group_path: Path, event_line_by_id: Dict[str, int]) -> tuple[str, int]:
    path = group_path / "state" / "read_cursors.json"
    if not path.exists():
        return "", 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "", 0
    memory_doc = payload.get("memory") if isinstance(payload, dict) else {}
    if not isinstance(memory_doc, dict):
        return "", 0
    event_id = str(memory_doc.get("event_id") or "").strip()
    return event_id, int(event_line_by_id.get(event_id) or 0)


def _load_memory_automation_keys(group_path: Path) -> List[str]:
    path = group_path / "state" / "automation.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    actors = payload.get("actors") if isinstance(payload, dict) else {}
    memory_doc = actors.get("memory") if isinstance(actors, dict) else {}
    if not isinstance(memory_doc, dict):
        return []
    nudge_items = memory_doc.get("nudge_items") if isinstance(memory_doc.get("nudge_items"), dict) else {}
    return sorted(str(key).strip() for key in nudge_items if str(key).strip())


def _load_memory_runner(
    group_path: Path,
    *,
    pid_alive_fn: Optional[Callable[[int], bool]],
) -> tuple[Optional[int], Optional[bool]]:
    path = group_path / "state" / "runners" / "pty" / "memory.json"
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    pid_raw = payload.get("pid") if isinstance(payload, dict) else None
    try:
        pid = int(pid_raw)
    except Exception:
        return None, None
    if pid_alive_fn is None:
        return pid, None
    return pid, bool(pid_alive_fn(pid))


def _build_reasons(diagnostics: MemoryDeliveryDiagnostics) -> List[str]:
    reasons: List[str] = []
    if diagnostics.memory_consults:
        reasons.append("memory_consults_pending")
    if diagnostics.memory_notifications:
        reasons.append("memory_nudged")
    if diagnostics.automation_nudge_keys:
        reasons.append("memory_automation_backlog")
    if not (diagnostics.memory_reads or diagnostics.memory_acks or diagnostics.memory_replies):
        if diagnostics.memory_consults:
            reasons.append("no_memory_activity")
    if diagnostics.cursor_stale:
        reasons.append("memory_cursor_stale")
    if diagnostics.runner_alive is True:
        reasons.append("memory_runner_alive")
    elif diagnostics.runner_alive is False:
        reasons.append("memory_runner_down")
    return reasons


def _classify_status(diagnostics: MemoryDeliveryDiagnostics) -> str:
    if not diagnostics.memory_consults:
        return "no_memory_consults"
    if diagnostics.memory_replies:
        return "replied"
    if diagnostics.memory_reads or diagnostics.memory_acks:
        return "consumed"
    if diagnostics.runner_alive is False:
        return "runner_down"
    if diagnostics.memory_notifications and diagnostics.cursor_stale:
        return "stalled"
    return "pending"
