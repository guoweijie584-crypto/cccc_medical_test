"""CLI for classifying a runtime bound round from the repo-local ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cccc_native.runtime_gate import (
    classify_probe_round_from_ledger,
    find_latest_bound_user_round_id,
)
from src.cccc_native.runtime_manager import load_bootstrap_state, native_cccc_home


def _default_group_id() -> str:
    state = load_bootstrap_state()
    group_id = str(state.get("main_group_id") or "").strip()
    return group_id or "g_619a5acb6163"


def _default_ledger_path(group_id: str) -> Path:
    return native_cccc_home() / "groups" / group_id / "ledger.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify a runtime bound round from the live ledger.")
    parser.add_argument("--group-id", default="", help="CCCC group id; defaults to the bootstrapped main group")
    parser.add_argument("--ledger", default="", help="Override ledger path")
    parser.add_argument("--probe-id", default="", help="User probe event id to classify")
    parser.add_argument(
        "--latest-bound-round",
        action="store_true",
        help="Use the latest bound user chat.message in the target ledger",
    )
    args = parser.parse_args()

    group_id = str(args.group_id or "").strip() or _default_group_id()
    ledger_path = Path(str(args.ledger or "").strip()) if str(args.ledger or "").strip() else _default_ledger_path(group_id)
    if not ledger_path.exists():
        raise SystemExit(f"ledger not found: {ledger_path}")

    probe_id = str(args.probe_id or "").strip()
    if args.latest_bound_round:
        probe_id = find_latest_bound_user_round_id(ledger_path)
    if not probe_id:
        raise SystemExit("probe id is required; pass --probe-id or --latest-bound-round")

    verdict = classify_probe_round_from_ledger(ledger_path, probe_id)
    print(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
