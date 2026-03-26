"""Run the vendored CCCC daemon foreground process."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cccc_native.vendored_cccc import ensure_vendored_cccc_on_path

ensure_vendored_cccc_on_path()

from cccc import daemon_main


def main() -> int:
    return int(daemon_main.main(["run", *sys.argv[1:]]))


if __name__ == "__main__":
    raise SystemExit(main())
