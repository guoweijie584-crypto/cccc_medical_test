"""Runtime helpers for the CCCC-native glucose-management architecture."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .vendored_cccc import ensure_vendored_cccc_on_path

ensure_vendored_cccc_on_path()

from cccc.daemon.server import DaemonPaths, call_daemon
import yaml

from config.settings import PROJECT_ROOT

BOOTSTRAP_STATE_FILE = PROJECT_ROOT / "config" / "cccc_native" / "bootstrap_state.json"
NATIVE_LLM_CONFIG_FILE = PROJECT_ROOT / "config" / "cccc_native" / "actor_llm_config.json"
DEFAULT_NATIVE_CCCC_HOME = (PROJECT_ROOT / ".cccc_home").resolve()


def _env_native_home() -> Optional[Path]:
    for env_name in ("CCCC_NATIVE_HOME", "CCCC_HOME"):
        raw = str(os.environ.get(env_name) or "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return None


def native_cccc_home() -> Path:
    env_home = _env_native_home()
    if env_home is not None:
        return env_home
    state = {}
    if BOOTSTRAP_STATE_FILE.exists():
        try:
            state = json.loads(BOOTSTRAP_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    stored = str(state.get("cccc_home") or "").strip()
    if stored:
        return Path(stored).expanduser().resolve()
    return DEFAULT_NATIVE_CCCC_HOME


def native_daemon_paths() -> DaemonPaths:
    return DaemonPaths(native_cccc_home())


def _call_native_daemon(op: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = call_daemon({"op": op, "args": args or {}}, paths=native_daemon_paths())
    if not resp.get("ok"):
        error = resp.get("error") if isinstance(resp.get("error"), dict) else {}
        raise RuntimeError(f"{op} failed: {error.get('code')}: {error.get('message')}")
    return dict(resp.get("result") or {})


def ensure_native_daemon_running() -> None:
    env = os.environ.copy()
    env["CCCC_HOME"] = str(native_cccc_home())
    env.setdefault("CCCC_DAEMON_PORT", "9766")
    proc = subprocess.run(
        [sys.executable, "-m", "cccc.daemon_main", "start"],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to start daemon")


def load_bootstrap_state() -> Dict[str, Any]:
    if not BOOTSTRAP_STATE_FILE.exists():
        return {}
    try:
        payload = json.loads(BOOTSTRAP_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    current_home = str(native_cccc_home())
    stored_home = str(payload.get("cccc_home") or "").strip()
    if stored_home and stored_home != current_home:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_actor_llm_config() -> Dict[str, Any]:
    default = {
        "default": {"api_key": "", "api_base": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
        "actors": {},
    }
    if not NATIVE_LLM_CONFIG_FILE.exists():
        return default
    try:
        payload = json.loads(NATIVE_LLM_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return default
        merged = dict(default)
        merged["default"] = dict(default["default"], **dict(payload.get("default") or {}))
        merged["actors"] = dict(payload.get("actors") or {})
        return merged
    except Exception:
        return default


def save_actor_llm_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = load_actor_llm_config()
    next_default = dict(current["default"])
    default_patch = dict(payload.get("default") or {})
    if default_patch.get("clear_api_key"):
        next_default["api_key"] = ""
    if "api_key" in default_patch and default_patch.get("api_key") not in (None, ""):
        next_default["api_key"] = str(default_patch.get("api_key") or "").strip()
    if "api_base" in default_patch and default_patch.get("api_base") not in (None, ""):
        next_default["api_base"] = str(default_patch.get("api_base") or "").strip()
    if "model" in default_patch and default_patch.get("model") not in (None, ""):
        next_default["model"] = str(default_patch.get("model") or "").strip()

    next_actors = dict(current["actors"])
    for actor_id, raw_patch in dict(payload.get("actors") or {}).items():
        aid = str(actor_id or "").strip()
        if not aid:
            continue
        patch = dict(raw_patch or {})
        actor_entry = dict(next_actors.get(aid) or {})
        if patch.get("clear_api_key"):
            actor_entry["api_key"] = ""
        if "api_key" in patch and patch.get("api_key") not in (None, ""):
            actor_entry["api_key"] = str(patch.get("api_key") or "").strip()
        if "api_base" in patch and patch.get("api_base") not in (None, ""):
            actor_entry["api_base"] = str(patch.get("api_base") or "").strip()
        if "model" in patch and patch.get("model") not in (None, ""):
            actor_entry["model"] = str(patch.get("model") or "").strip()
        next_actors[aid] = actor_entry

    merged = {
        "default": next_default,
        "actors": next_actors,
    }
    NATIVE_LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    NATIVE_LLM_CONFIG_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def apply_llm_config_to_group(group_id: str, actor_ids: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
    ensure_native_daemon_running()
    default_cfg = dict(config.get("default") or {})
    actor_cfg_map = dict(config.get("actors") or {})
    results: Dict[str, Any] = {}
    for actor_id in actor_ids:
        override = dict(actor_cfg_map.get(actor_id) or {})
        effective = {
            "LLM_API_KEY": str(override.get("api_key") or default_cfg.get("api_key") or "").strip(),
            "LLM_API_BASE": str(override.get("api_base") or default_cfg.get("api_base") or "").strip(),
            "LLM_MODEL": str(override.get("model") or default_cfg.get("model") or "").strip(),
        }
        set_payload = {key: value for key, value in effective.items() if value}
        clear = not bool(set_payload)
        result = _call_native_daemon(
            "actor_env_private_update",
            {
                "group_id": group_id,
                "actor_id": actor_id,
                "by": "user",
                "set": set_payload,
                "unset": [],
                "clear": clear,
            },
        )
        results[actor_id] = result
    return results


def group_snapshot(group_id: str) -> Dict[str, Any]:
    if not group_id:
        return {}
    home = native_cccc_home()
    registry_path = home / "registry.json"
    if not registry_path.exists():
        return {}
    try:
        registry_doc = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    meta = ((registry_doc.get("groups") or {}) if isinstance(registry_doc, dict) else {}).get(group_id) or {}
    path = str(meta.get("path") or "").strip()
    if not path:
        return {}
    group_yaml = Path(path) / "group.yaml"
    if not group_yaml.exists():
        return {}
    try:
        group_doc = yaml.safe_load(group_yaml.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    actors = group_doc.get("actors") if isinstance(group_doc.get("actors"), list) else []
    return {
        "group_id": group_id,
        "title": str(group_doc.get("title") or ""),
        "topic": str(group_doc.get("topic") or ""),
        "running": bool(group_doc.get("running", False)),
        "state": str(group_doc.get("state") or "active"),
        "active_scope_key": str(group_doc.get("active_scope_key") or ""),
        "scope_count": len(group_doc.get("scopes") or []),
        "actor_ids": [str(actor.get("id") or "").strip() for actor in actors if isinstance(actor, dict)],
        "path": path,
    }


def list_native_groups() -> Dict[str, Any]:
    state = load_bootstrap_state()
    main_group_id = str(state.get("main_group_id") or "").strip()
    evaluation_group_id = str(state.get("evaluation_group_id") or "").strip()
    return {
        "cccc_home": str(native_cccc_home()),
        "main_group": group_snapshot(main_group_id) if main_group_id else {},
        "evaluation_group": group_snapshot(evaluation_group_id) if evaluation_group_id else {},
    }


def list_group_actors(group_id: str) -> List[Dict[str, Any]]:
    if not group_id:
        return []
    try:
        ensure_native_daemon_running()
        result = _call_native_daemon("actor_list", {"group_id": group_id})
        return list(result.get("actors") or [])
    except Exception:
        snapshot = group_snapshot(group_id)
        path = str(snapshot.get("path") or "").strip()
        if not path:
            return []
        group_yaml = Path(path) / "group.yaml"
        try:
            group_doc = yaml.safe_load(group_yaml.read_text(encoding="utf-8")) or {}
        except Exception:
            return []
        actors = group_doc.get("actors") if isinstance(group_doc.get("actors"), list) else []
        return [dict(actor) for actor in actors if isinstance(actor, dict)]


def start_group(group_id: str) -> Dict[str, Any]:
    ensure_native_daemon_running()
    return _call_native_daemon("group_start", {"group_id": group_id, "by": "user"})


def stop_group(group_id: str) -> Dict[str, Any]:
    ensure_native_daemon_running()
    return _call_native_daemon("group_stop", {"group_id": group_id, "by": "user"})


def set_group_state(group_id: str, state: str) -> Dict[str, Any]:
    ensure_native_daemon_running()
    return _call_native_daemon("group_set_state", {"group_id": group_id, "state": state, "by": "user"})


def send_group_message(
    group_id: str,
    *,
    by: str,
    text: str,
    to: Optional[List[str]] = None,
    priority: str = "normal",
    reply_required: bool = False,
    client_id: str = "",
    src_group_id: str = "",
    src_event_id: str = "",
) -> Dict[str, Any]:
    """Send a chat.message into a CCCC group via the native daemon.

    This is the thinnest deterministic bridge from local Python code into the
    ledger-backed runtime. Both the MCP `cccc_message_send` surface and the web
    `/api/v1/groups/{id}/send` route eventually converge on the same daemon op.
    """
    ensure_native_daemon_running()
    return _call_native_daemon(
        "send",
        {
            "group_id": group_id,
            "text": str(text or ""),
            "by": str(by or "").strip(),
            "to": [str(item).strip() for item in (to or []) if str(item).strip()],
            "path": "",
            "priority": str(priority or "normal").strip() or "normal",
            "reply_required": bool(reply_required),
            "client_id": str(client_id or "").strip(),
            "src_group_id": str(src_group_id or "").strip(),
            "src_event_id": str(src_event_id or "").strip(),
        },
    )
