"""Bootstrap cccc_test into the CCCC-native glucose-management architecture."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.cccc_native.vendored_cccc import ensure_vendored_cccc_on_path

ensure_vendored_cccc_on_path()

from cccc.daemon.server import DaemonPaths, call_daemon
from cccc.kernel.active import set_active_group_id
from cccc.kernel.group import create_group, load_group
from cccc.kernel.registry import load_registry
from cccc.kernel.scope import detect_scope

from config.cccc_native.blueprints import build_evaluation_group_template, build_main_group_template

PROJECT_ROOT = Path(__file__).resolve().parent
STATE_FILE = PROJECT_ROOT / "config" / "cccc_native" / "bootstrap_state.json"


def _runtime_home() -> Path:
    for env_name in ("CCCC_NATIVE_HOME", "CCCC_HOME"):
        raw = str(os.environ.get(env_name, "")).strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return (PROJECT_ROOT / ".cccc_home").resolve()


def _load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        current_home = str(_runtime_home())
        stored_home = str(payload.get("cccc_home") or "").strip()
        if current_home and stored_home and current_home != stored_home:
            return {}
        return payload
    except Exception:
        return {}


def _save_state(payload: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_daemon() -> None:
    env = os.environ.copy()
    home = str(_runtime_home())
    env.setdefault("CCCC_HOME", home)
    env.setdefault("CCCC_NATIVE_HOME", home)
    result = subprocess.run(
        [sys.executable, "-m", "cccc.daemon_main", "start"],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to start/verify CCCC daemon.")


def _call(op: str, args: Dict[str, Any]) -> Dict[str, Any]:
    home = _runtime_home()
    resp = call_daemon({"op": op, "args": args}, paths=DaemonPaths(home))
    if not resp.get("ok"):
        error = resp.get("error") if isinstance(resp.get("error"), dict) else {}
        raise RuntimeError(f"{op} failed: {error.get('code')}: {error.get('message')}")
    return dict(resp.get("result") or {})


def _find_group_id_by_title(reg: Any, *, title: str, scope_key: str) -> str:
    fallback = ""
    wanted_title = str(title or "").strip()
    wanted_scope_key = str(scope_key or "").strip()
    for group_id, meta in dict(getattr(reg, "groups", {}) or {}).items():
        if not isinstance(meta, dict):
            continue
        if str(meta.get("title") or "").strip() != wanted_title:
            continue
        group = load_group(str(group_id))
        if group is None:
            continue
        if not fallback:
            fallback = str(group_id)
        scopes = group.doc.get("scopes")
        if not isinstance(scopes, list):
            continue
        if any(isinstance(item, dict) and str(item.get("scope_key") or "").strip() == wanted_scope_key for item in scopes):
            return str(group_id)
    return fallback


def _ensure_scope_attached(group_id: str, path: Path) -> None:
    _call("attach", {"path": str(path), "group_id": group_id, "by": "user"})


def _best_effort_stop_group(group_id: str) -> None:
    try:
        _call("group_stop", {"group_id": group_id, "by": "user"})
    except Exception:
        pass


def _replace_group_template(group_id: str, template: str) -> None:
    last_error: Optional[Exception] = None
    for attempt in range(3):
        _best_effort_stop_group(group_id)
        time.sleep(0.4 + 0.4 * attempt)
        try:
            _call(
                "group_template_import_replace",
                {
                    "group_id": group_id,
                    "by": "user",
                    "confirm": group_id,
                    "template": template,
                },
            )
            return
        except Exception as exc:
            last_error = exc
            message = str(exc)
            if "template_apply_failed" not in message and "WinError 5" not in message and "拒绝访问" not in message:
                raise
    if last_error is not None:
        raise last_error


def _ensure_main_group(runtime: str) -> str:
    state = _load_state()
    scope_key = detect_scope(PROJECT_ROOT).scope_key
    reg = load_registry()
    existing_id = str(state.get("main_group_id") or "").strip()
    if not existing_id or load_group(existing_id) is None:
        existing_id = _find_group_id_by_title(reg, title="glucose-management-main", scope_key=scope_key)
    if not existing_id:
        group = create_group(reg, title="glucose-management-main", topic="User-facing glucose-management medical team")
        existing_id = str(group.group_id or "").strip()
    _ensure_scope_attached(existing_id, PROJECT_ROOT)
    _replace_group_template(existing_id, build_main_group_template(runtime=runtime))
    _ensure_scope_attached(existing_id, PROJECT_ROOT)
    return existing_id


def _ensure_evaluation_group(runtime: str) -> str:
    state = _load_state()
    existing_id = str(state.get("evaluation_group_id") or "").strip()
    eval_scope_root = PROJECT_ROOT / ".cccc_eval_scope"
    eval_scope_root.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    scope_key = detect_scope(eval_scope_root).scope_key
    if not existing_id or load_group(existing_id) is None:
        existing_id = _find_group_id_by_title(reg, title="glucose-management-eval", scope_key=scope_key)
    if not existing_id:
        group = create_group(reg, title="glucose-management-eval", topic="Backstage evaluation and optimization team")
        existing_id = str(group.group_id or "").strip()
    _ensure_scope_attached(existing_id, eval_scope_root)
    _replace_group_template(existing_id, build_evaluation_group_template(runtime=runtime))
    _ensure_scope_attached(existing_id, eval_scope_root)
    return existing_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the CCCC-native glucose-management groups.")
    parser.add_argument("--runtime", default="codex", help="Runtime to use for all bootstrapped actors (default: codex)")
    args = parser.parse_args()

    runtime = str(args.runtime or "codex").strip() or "codex"
    runtime_home = str(_runtime_home())
    os.environ.setdefault("CCCC_HOME", runtime_home)
    os.environ.setdefault("CCCC_NATIVE_HOME", runtime_home)
    _ensure_daemon()

    main_group_id = _ensure_main_group(runtime)
    eval_group_id = _ensure_evaluation_group(runtime)

    if main_group_id:
        set_active_group_id(main_group_id)

    _save_state(
        {
            "cccc_home": runtime_home,
            "main_group_id": main_group_id,
            "evaluation_group_id": eval_group_id,
            "runtime": runtime,
            "project_root": str(PROJECT_ROOT),
        }
    )

    print(
        json.dumps(
            {
                "ok": True,
                "main_group_id": main_group_id,
                "evaluation_group_id": eval_group_id,
                "runtime": runtime,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
