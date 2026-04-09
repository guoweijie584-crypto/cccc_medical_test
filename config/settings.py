"""Project configuration for the glucose-management self-evolution demo."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"
PATIENT_DATA_FILE = DATA_DIR / "patient_structured" / "patient_structured_50_desensitize.json"
EVALUATION_DATASET_FILE = PROJECT_ROOT / "tests" / "evaluation_dataset_v2.json"
EVALUATION_OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
LOG_DIR = PROJECT_ROOT / "logs"
RUNTIME_LLM_CONFIG_FILE = PROJECT_ROOT / "config" / "runtime_llm.json"


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat").strip()

LLM_CONFIG = {
    "default": {
        "api_key": LLM_API_KEY,
        "api_base": LLM_API_BASE,
        "model": LLM_MODEL,
        "temperature": 0.6,
        "max_tokens": 1800,
    },
    "evaluation": {
        "api_key": LLM_API_KEY,
        "api_base": LLM_API_BASE,
        "model": LLM_MODEL,
        "temperature": 0.2,
        "max_tokens": 1400,
    },
    "optimization": {
        "api_key": LLM_API_KEY,
        "api_base": LLM_API_BASE,
        "model": LLM_MODEL,
        "temperature": 0.4,
        "max_tokens": 2200,
    },
}

MEMORY_PALACE_HOST = os.getenv("MEMORY_PALACE_HOST", "127.0.0.1").strip()
MEMORY_PALACE_PORT = _env_int("MEMORY_PALACE_PORT", 8000)
MEMORY_PALACE_URL = f"http://{MEMORY_PALACE_HOST}:{MEMORY_PALACE_PORT}"
MCP_API_KEY = os.getenv("MCP_API_KEY", "memory-palace-default-key").strip()

MEMORY_DOMAINS = {
    "patient_profile": "medical://patient/{patient_id}/profile",
    "glucose_records": "medical://patient/{patient_id}/glucose",
    "medication": "medical://patient/{patient_id}/medication",
    "diet": "medical://patient/{patient_id}/diet",
    "exercise": "medical://patient/{patient_id}/exercise",
    "consultation": "medical://patient/{patient_id}/consultation",
    "safety": "medical://patient/{patient_id}/safety",
}

AGENT_CONFIG = {
    "primary": {
        "name": "Primary Doctor",
        "name_zh": "主治医生",
        "role": "Owns final synthesis across specialists.",
        "system_prompt_file": "prompts/primary_doctor.txt",
    },
    "pharmacist": {
        "name": "Pharmacist",
        "name_zh": "药剂师",
        "role": "Covers medication choice, dose, interactions, and safety.",
        "system_prompt_file": "prompts/pharmacist.txt",
    },
    "nutritionist": {
        "name": "Nutritionist",
        "name_zh": "营养师",
        "role": "Provides diet and meal-structure guidance.",
        "system_prompt_file": "prompts/nutritionist.txt",
    },
    "doctor": {
        "name": "Metabolism Doctor",
        "name_zh": "代谢病医生",
        "role": "Handles complication and disease-management reasoning.",
        "system_prompt_file": "prompts/metabolism_doctor.txt",
    },
    "safety_reviewer": {
        "name": "Safety Reviewer",
        "name_zh": "安全审查员",
        "role": "Reviews final responses for safety risks and escalation needs.",
        "system_prompt_file": "prompts/safety_reviewer.txt",
    },
    "memory": {
        "name": "Memory Agent",
        "name_zh": "记忆管理",
        "role": "Extracts and maintains short-, mid-, and long-term patient memory.",
        "system_prompt_file": "prompts/memory_agent.txt",
    },
    "evaluator": {
        "name": "Evaluator",
        "name_zh": "质检员",
        "role": "Scores answer quality and memory quality.",
        "system_prompt_file": "prompts/evaluator.txt",
    },
    "analyzer": {
        "name": "Analyzer",
        "name_zh": "分析师",
        "role": "Separates prompt issues from memory issues and locates root cause.",
        "system_prompt_file": "prompts/analyzer.txt",
    },
    "prompt_optimizer": {
        "name": "Prompt Optimizer",
        "name_zh": "提示词优化师",
        "role": "Improves prompts for medical agents and the memory agent.",
        "system_prompt_file": "prompts/prompt_optimizer.txt",
    },
    "memory_optimizer": {
        "name": "Memory Optimizer",
        "name_zh": "记忆优化师",
        "role": "Adds, updates, deletes, and restructures memory entries.",
        "system_prompt_file": "prompts/memory_optimizer.txt",
    },
}

PROMPT_AGENT_IDS = tuple(AGENT_CONFIG.keys())

EVOLUTION_CONFIG = {
    "max_iterations": _env_int("EVOLUTION_MAX_ITERATIONS", 3),
    "improvement_threshold": _env_float("EVOLUTION_IMPROVEMENT_THRESHOLD", 0.03),
    "regression_tolerance": _env_float("EVOLUTION_REGRESSION_TOLERANCE", 0.05),
    "default_eval_cases": _env_int("EVOLUTION_EVAL_CASES", 25),
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def prompt_path_for(agent_id: str) -> Path:
    prompt_file = str(AGENT_CONFIG.get(agent_id, {}).get("system_prompt_file", "")).strip()
    return PROJECT_ROOT / prompt_file if prompt_file else PROMPTS_DIR / f"{agent_id}.txt"


def read_runtime_llm_settings() -> dict[str, str]:
    settings = {
        "api_key": LLM_API_KEY,
        "api_base": LLM_API_BASE,
        "model": LLM_MODEL,
    }
    if not RUNTIME_LLM_CONFIG_FILE.exists():
        return settings
    try:
        import json

        payload = json.loads(RUNTIME_LLM_CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            settings["api_key"] = str(payload.get("api_key", settings["api_key"]) or "").strip()
            settings["api_base"] = str(payload.get("api_base", settings["api_base"]) or "").strip()
            settings["model"] = str(payload.get("model", settings["model"]) or "").strip()
    except Exception:
        pass
    return settings


def write_runtime_llm_settings(
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    model: str | None = None,
    clear_api_key: bool = False,
) -> dict[str, str]:
    current = read_runtime_llm_settings()
    if clear_api_key:
        current["api_key"] = ""
    elif api_key is not None:
        current["api_key"] = str(api_key).strip()
    if api_base is not None:
        current["api_base"] = str(api_base).strip() or current["api_base"]
    if model is not None:
        current["model"] = str(model).strip() or current["model"]

    RUNTIME_LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    import json

    RUNTIME_LLM_CONFIG_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def mask_api_key(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"
