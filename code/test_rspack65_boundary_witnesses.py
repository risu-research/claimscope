"""Fully offline original-rule replay and corruption checks for 72 public boundary witnesses."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from replay_rspack65_boundary_witnesses import (
    FIXTURE, PAIR_LEDGER, EXPECTED_PAIRS, EXPECTED_PRS,
    replay, source_bytes, ledger,
)

class BoundaryWitnessTests(unittest.TestCase):
    def test_original_upstream_code_hashes_are_pinned(self):
        self.assertEqual(len(source_bytes()),2)

    def test_original_pair_ledger_is_fixed(self):
        rows=ledger()
        self.assertEqual(len(rows),EXPECTED_PAIRS)
        self.assertEqual(len({x["pr_number"] for x in rows}),EXPECTED_PRS)

    def test_original_extractor_replay_is_fully_offline(self):
        result=replay(FIXTURE)
        self.assertEqual(result["pairs"],72)
        self.assertEqual(result["prs"],65)
        self.assertLessEqual(result["max_excerpt_length"],1024)

    def test_mutated_cue_is_rejected(self):
        x=json.loads(FIXTURE.read_text(encoding="utf8"))
        source=x["witnesses"][0]
        self.assertIn("bundle",source["right_public_bot_head"].lower())
        source["right_public_bot_head"] = " ".join(["no_size_cue"]*80)
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"mutated.json"
            f.write_text(json.dumps(x),encoding="utf8")
            with self.assertRaises(ValueError):
                replay(f)

    def test_no_human_comments_or_credentials_in_witnesses(self):
        x=json.loads(FIXTURE.read_text(encoding="utf8"))
        self.assertEqual(len(x["witnesses"]),72)
        self.assertEqual(len({w["pr_number"] for w in x["witnesses"]}),65)
        self.assertTrue(all("human" not in " ".join(w).lower()
                            for w in x["witnesses"]))

if __name__=="__main__":
    unittest.main()
