from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestAtomicWriteWindowsRetry(unittest.TestCase):
    def test_atomic_write_text_retries_permission_error_on_windows(self) -> None:
        from cccc.util.fs import atomic_write_text

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.txt"
            real_replace = os.replace
            attempts = {"count": 0}

            def flaky_replace(src: str, dst: str) -> None:
                attempts["count"] += 1
                if attempts["count"] < 3:
                    raise PermissionError(13, "Access is denied", dst)
                real_replace(src, dst)

            with (
                patch("cccc.util.fs.os.name", "nt"),
                patch("cccc.util.fs.os.replace", side_effect=flaky_replace),
                patch("cccc.util.fs.time.sleep", return_value=None),
            ):
                atomic_write_text(path, "hello")

            self.assertEqual(path.read_text(encoding="utf-8"), "hello")
            self.assertEqual(attempts["count"], 3)

    def test_atomic_write_json_retries_permission_error_on_windows(self) -> None:
        from cccc.util.fs import atomic_write_json

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.json"
            real_replace = os.replace
            attempts = {"count": 0}

            def flaky_replace(src: str, dst: str) -> None:
                attempts["count"] += 1
                if attempts["count"] < 4:
                    raise PermissionError(13, "Access is denied", dst)
                real_replace(src, dst)

            with (
                patch("cccc.util.fs.os.name", "nt"),
                patch("cccc.util.fs.os.replace", side_effect=flaky_replace),
                patch("cccc.util.fs.time.sleep", return_value=None),
            ):
                atomic_write_json(path, {"ok": True})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})
            self.assertEqual(attempts["count"], 4)
