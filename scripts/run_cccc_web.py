"""Run the vendored CCCC web process."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cccc_native.vendored_cccc import ensure_vendored_cccc_on_path

ensure_vendored_cccc_on_path()

from cccc.ports.web.main import main as web_main


def main() -> int:
    return int(web_main(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
