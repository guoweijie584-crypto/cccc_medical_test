from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


_WINDOWS_REPLACE_RETRY_DELAYS = (0.01, 0.02, 0.05, 0.1, 0.2)


def _replace_with_retry(src: str, dst: Path) -> None:
    target = str(dst)
    if os.name != "nt":
        os.replace(src, target)
        return

    last_error: PermissionError | None = None
    for delay in (0.0, *_WINDOWS_REPLACE_RETRY_DELAYS):
        if delay > 0.0:
            time.sleep(delay)
        try:
            os.replace(src, target)
            return
        except PermissionError as exc:
            last_error = exc

    assert last_error is not None
    raise last_error


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
        _replace_with_retry(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def atomic_write_json(path: Path, obj: Dict[str, Any], *, indent: int = 2) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=indent) + "\n")

def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        _replace_with_retry(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
