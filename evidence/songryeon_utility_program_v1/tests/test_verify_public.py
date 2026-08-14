from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_verifier(root: Path) -> tuple[int, dict]:
    process = subprocess.run(
        [sys.executable, "-B", str(root / "verify_public.py")],
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    return process.returncode, json.loads(process.stdout)


class PublicDerivativeVerificationTests(unittest.TestCase):
    def test_baseline_passes(self) -> None:
        code, result = run_verifier(ROOT)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "PASS")

    def test_declared_data_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "bundle"
            shutil.copytree(ROOT, copy)
            target = copy / "data" / "receipt_reconstruction_rows.jsonl"
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            code, result = run_verifier(copy)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("mismatch" in item for item in result["errors"]))

    def test_undeclared_nested_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "bundle"
            shutil.copytree(ROOT, copy)
            extra = copy / "data" / "undeclared" / "extra.txt"
            extra.parent.mkdir(parents=True)
            extra.write_text("negative control\n", encoding="utf-8")
            code, result = run_verifier(copy)
            self.assertNotEqual(code, 0)
            self.assertTrue(
                any("recursive_file_set_mismatch" in item for item in result["errors"])
            )


if __name__ == "__main__":
    unittest.main()
