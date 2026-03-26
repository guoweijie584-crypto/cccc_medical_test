#!/usr/bin/env python
"""Run the end-to-end evolution demo against the evaluation dataset."""

from __future__ import annotations

import json
from pathlib import Path

from src.evolution import build_ui_report, run_demo_evaluation


def main() -> int:
    print("=" * 70)
    print("Glucose Management Self-Evolution Demo")
    print("=" * 70)

    run_result = run_demo_evaluation(export=True)
    ui_report = build_ui_report(run_result)

    print(f"Mode: {run_result['mode']}")
    print(f"Iterations: {len(ui_report.get('iterations', []))}")
    print(f"Initial score: {ui_report['summary'].get('initialScore', 0):.2f}")
    print(f"Final score: {ui_report['summary'].get('finalScore', 0):.2f}")
    print(f"Improvement: {ui_report['summary'].get('improvement', 0):+.2f}")
    print(f"Export dir: {run_result.get('export_dir')}")

    export_dir = Path(str(run_result.get("export_dir") or "")).resolve()
    if export_dir:
        report_path = export_dir / "ui_report.json"
        report_path.write_text(json.dumps(ui_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"UI report: {report_path}")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
