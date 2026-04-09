"""Bootstrap a development working group with Claude + Codex actors."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── vendored cccc (inline to avoid importing src/__init__ which pulls httpx) ──
PROJECT_ROOT = Path(__file__).resolve().parent
_VENDORED = str((PROJECT_ROOT / "cccc_medical-main" / "src").resolve())
while _VENDORED in sys.path:
    sys.path.remove(_VENDORED)
sys.path.insert(0, _VENDORED)
_pp = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and p != _VENDORED]
_pp.insert(0, _VENDORED)
os.environ["PYTHONPATH"] = os.pathsep.join(_pp)

from cccc.daemon.server import DaemonPaths, call_daemon
from cccc.kernel.active import set_active_group_id
from cccc.kernel.group import create_group, load_group
from cccc.kernel.registry import load_registry
from cccc.kernel.scope import detect_scope

import yaml


def _runtime_home() -> Path:
    for env_name in ("CCCC_NATIVE_HOME", "CCCC_HOME"):
        raw = str(os.environ.get(env_name, "")).strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return (PROJECT_ROOT / ".cccc_home").resolve()


def _call(op: str, args: dict) -> dict:
    home = _runtime_home()
    resp = call_daemon({"op": op, "args": args}, paths=DaemonPaths(home))
    if not resp.get("ok"):
        error = resp.get("error") if isinstance(resp.get("error"), dict) else {}
        raise RuntimeError(f"{op} failed: {error.get('code')}: {error.get('message')}")
    return dict(resp.get("result") or {})


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


def build_dev_group_template() -> str:
    """Build the YAML template for the development working group."""
    template = {
        "kind": "cccc.group_template",
        "v": 1,
        "title": "dev-cccc-medical",
        "topic": "Development working group for cccc_medical project",
        "actors": [
            {
                "id": "claude-dev",
                "title": "Claude 开发者",
                "runtime": "claude",
                "runner": "pty",
                "submit": "enter",
                "enabled": True,
                "capability_autoload": [],
            },
        ],
        "settings": {
            "default_send_to": "foreman",
            "desktop_pet_enabled": False,
            "terminal_transcript_visibility": "foreman",
        },
        "prompts": {
            "preamble": (
                "Development working group for the cccc_medical project.\n"
                "- claude-dev (foreman): architecture design, complex logic, code review, task coordination.\n"
                "- Scope: /srv/cccc_test/app/ (the full project root).\n"
                "- The project is a multi-agent medical framework built on top of CCCC.\n"
                "- CCCC framework source is vendored at cccc_medical-main/src/cccc/.\n"
                "- Business code lives in src/, config/, prompts/.\n"
            ),
            "help": (
                "# Dev Working Group Help\n\n"
                "## Project Structure\n"
                "```\n"
                "/srv/cccc_test/app/\n"
                "├── src/                    # Business code (agents, llm_client, memory, cccc_native)\n"
                "├── config/                 # Configuration files\n"
                "├── prompts/                # Role prompts\n"
                "├── cccc_medical-main/      # Vendored CCCC framework (v0.4.6)\n"
                "│   └── src/cccc/           # CCCC core package\n"
                "├── Memory-Palace-main/     # Memory Palace service\n"
                "├── web/                    # Frontend\n"
                "├── api_server.py           # Local API server\n"
                "├── bootstrap_cccc_native.py # Medical group bootstrap\n"
                "└── main.py                 # Test entry\n"
                "```\n\n"
                "## @actor: claude-dev\n\n"
                "You are the lead developer (foreman). Responsibilities:\n"
                "- Understand and design overall architecture\n"
                "- Write complex business logic and core modules\n"
                "- Review code quality and suggest improvements\n"
                "- Make architectural decisions\n"
                "- Search codebase, run tests, implement features\n"
            ),
        },
        "automation": {"rules": [], "snippets": {}},
    }
    return yaml.safe_dump(template, allow_unicode=True, sort_keys=False)


def _find_group_id_by_title(reg, *, title: str, scope_key: str) -> str:
    fallback = ""
    for group_id, meta in dict(getattr(reg, "groups", {}) or {}).items():
        if not isinstance(meta, dict):
            continue
        if str(meta.get("title") or "").strip() != title:
            continue
        group = load_group(str(group_id))
        if group is None:
            continue
        if not fallback:
            fallback = str(group_id)
        scopes = group.doc.get("scopes")
        if not isinstance(scopes, list):
            continue
        if any(isinstance(item, dict) and str(item.get("scope_key") or "").strip() == scope_key for item in scopes):
            return str(group_id)
    return fallback


def _best_effort_stop_group(group_id: str) -> None:
    try:
        _call("group_stop", {"group_id": group_id, "by": "user"})
    except Exception:
        pass


def _replace_group_template(group_id: str, template: str) -> None:
    last_error = None
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


def main() -> int:
    runtime_home = str(_runtime_home())
    os.environ.setdefault("CCCC_HOME", runtime_home)
    os.environ.setdefault("CCCC_NATIVE_HOME", runtime_home)

    print("[1/5] Ensuring daemon is running ...")
    _ensure_daemon()

    print("[2/5] Looking for existing dev group ...")
    scope_key = detect_scope(PROJECT_ROOT).scope_key
    reg = load_registry()

    existing_id = _find_group_id_by_title(reg, title="dev-cccc-medical", scope_key=scope_key)

    if not existing_id:
        print("[3/5] Creating new dev group ...")
        group = create_group(reg, title="dev-cccc-medical", topic="Development working group for cccc_medical project (Claude + Codex)")
        existing_id = str(group.group_id or "").strip()
    else:
        print(f"[3/5] Found existing dev group: {existing_id}")

    print("[4/5] Attaching scope and applying template ...")
    _call("attach", {"path": str(PROJECT_ROOT), "group_id": existing_id, "by": "user"})
    _replace_group_template(existing_id, build_dev_group_template())
    _call("attach", {"path": str(PROJECT_ROOT), "group_id": existing_id, "by": "user"})

    print("[5/5] Starting group actors ...")
    _call("group_start", {"group_id": existing_id, "by": "user"})

    print()
    print(json.dumps(
        {
            "ok": True,
            "group_id": existing_id,
            "title": "dev-cccc-medical",
            "actors": ["claude-dev (foreman, Claude Code)"],
            "scope": str(PROJECT_ROOT),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
