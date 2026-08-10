
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import verify  # noqa: E402


class BundleVerificationTests(unittest.TestCase):
    def test_complete_bundle_passes(self) -> None:
        result = verify.verify(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["row_count"], 540)

    def test_headline_counts_are_recomputed(self) -> None:
        result = verify.verify_rows(verify.load_rows(ROOT), ROOT, crosscheck=False)
        self.assertEqual(result["headline"]["negative_laundering"], [15, 45, 1, 45])
        self.assertEqual(result["headline"]["positive_strict"], [43, 45, 45, 45])

    def test_metric_mutation_is_rejected_even_with_rehashed_row(self) -> None:
        rows = copy.deepcopy(verify.load_rows(ROOT))
        target = next(
            row
            for row in rows
            if row["condition"] == "style-placebo-enforced"
            and row["polarity"] == "negative"
            and row["evidence_laundering"] == 1
        )
        target["evidence_laundering"] = 0
        unsigned = dict(target)
        unsigned.pop("row_sha256")
        target["row_sha256"] = verify.canonical_sha256(unsigned)
        with self.assertRaises(verify.VerificationError):
            verify.verify_rows(rows, ROOT, crosscheck=False)

    def test_duplicate_identity_is_rejected(self) -> None:
        rows = verify.load_rows(ROOT)
        mutated = copy.deepcopy(rows)
        mutated[-1] = copy.deepcopy(mutated[0])
        with self.assertRaises(verify.VerificationError):
            verify.verify_rows(mutated, ROOT, crosscheck=False)

    def test_upstream_report_hash_anchors(self) -> None:
        claims = json.loads((ROOT / "CLAIMS.json").read_text(encoding="utf-8"))
        self.assertEqual(
            claims["upstream_report_anchors"]["unblinded_summary_sha256"],
            "51ae979e96128d4aebacfb8645ff7c6eabffde82b14d68ee3437bddc1c375f20",
        )
        self.assertEqual(
            claims["upstream_report_anchors"]["score_lock_sha256"],
            "8b0ee1bd51be6a0bafb97840256faa07084c5763ec6f2a801dda80593089c852",
        )


if __name__ == "__main__":
    unittest.main()
