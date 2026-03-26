"""Helpers to prefer the repo-vendored ``cccc`` package at runtime.

This project vendors a patched CCCC runtime under ``cccc_medical-main/src``.
Server entrypoints should import that copy first so daemon/bootstrap/web/API all
run against the same code surface instead of falling back to site-packages.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDORED_CCCC_SRC = (PROJECT_ROOT / "cccc_medical-main" / "src").resolve()


def _prepend_sys_path(path: Path) -> None:
    raw = str(path)
    try:
        while raw in sys.path:
            sys.path.remove(raw)
    except ValueError:
        pass
    sys.path.insert(0, raw)


def _prepend_pythonpath_env(path: Path) -> None:
    raw = str(path)
    current = str(os.environ.get("PYTHONPATH") or "").strip()
    parts = [item for item in current.split(os.pathsep) if item]
    parts = [item for item in parts if item != raw]
    parts.insert(0, raw)
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)


def ensure_vendored_cccc_on_path() -> Path:
    """Force the repo-vendored ``cccc`` package ahead of site-packages."""
    _prepend_sys_path(VENDORED_CCCC_SRC)
    _prepend_pythonpath_env(VENDORED_CCCC_SRC)
    return VENDORED_CCCC_SRC
