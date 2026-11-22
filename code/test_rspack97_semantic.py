"""Deterministic, network-free tests for the Rspack 97 semantic source ledger."""
import copy
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from rspack97_semantic_audit import (
    ROOT, SNAPSHOT, REQUIRED_COUNTS, assess_saved, before_cutoff,
    digest, relation, run_replay, select_reports, source_inputs,
)


class Rspack97Tests(unittest.TestCase):
    def test_frozen_populations(self):
        inventory, baseline, new, witnesses = source_inputs()
        self.assertEqual(len(inventory), 97)
        self.assertEqual(len(baseline), 65)
        self.assertEqual(len(new), 32)
        self.assertEqual(len(witnesses), 65)
        self.assertEqual(sum(x["published_D6"] == "True" for x in inventory), 83)
        self.assertEqual(sum(x["published_D6"] == "False" for x in inventory), 14)
        self.assertEqual({n for n, r in new.items() if not r["evidence_comment_id"]},
                         {10648, 10677, 13932})
        self.assertEqual({n for n, r in new.items()
                          if r["source_sha_relation"] == "listed_pr_commit"},
                         {11320, 13975})
        self.assertEqual({n for n, r in new.items()
                          if r["source_sha_relation"] == "not_verified_current_commits"},
                         {14172})
        self.assertEqual({n for n, r in new.items()
                          if r["published_D6"] == "0" and r["evidence_comment_id"]},
                         {11179,11320,12058,13714,13842,13854,13935,13968,13973,13975,14101})

    def test_commit_attribution(self):
        a, b, c = ("a" * 40, "b" * 40, "c" * 40)
        self.assertEqual(relation(a, a, {a, b}), "head")
        self.assertEqual(relation(b, a, {a, b}), "listed_pr_commit")
        self.assertEqual(relation(c, a, {a, b}), "not_verified_current_commits")
        self.assertEqual(relation(None, a, {a, b}), "not_in_report")

    def test_cutoff_requires_both_timestamps(self):
        self.assertTrue(before_cutoff({"created_at":"2026-05-01T00:00:00Z",
                                       "updated_at":"2026-08-27T21:59:59Z"}))
        self.assertFalse(before_cutoff({"created_at":"2026-05-01T00:00:00Z",
                                        "updated_at":"2026-08-27T22:00:01Z"}))
        self.assertFalse(before_cutoff({"created_at":"2026-05-01T00:00:00Z"}))

    def test_selection_independent_of_D6(self):
        sha = "a" * 40
        bot = {"id": 101, "user":{"login":"github-actions[bot]","type":"Bot"},
               "created_at":"2026-05-01T00:00:00Z",
               "updated_at":"2026-05-02T00:00:00Z",
               "body":f"## 📦 Binary Size-limit\n> Comparing [here](https://github.com/web-infra-dev/rspack/commit/{sha})\n"
                      "Size increased by 1KB from 3MB to 3MB"}
        reports, other, n = select_reports([bot], sha, {sha})
        self.assertEqual((len(reports), len(other), n), (1,0,1))
        self.assertEqual(reports[0]["commit_relation"],"head")
        self.assertEqual(reports[0]["measurement"]["after"],"3MB")

    def test_offline_replay_and_tamper_detection(self):
        if not SNAPSHOT.exists():
            self.skipTest("Live collection snapshot not yet produced")
        data = json.loads(SNAPSHOT.read_text())
        self.assertEqual(len(data["prs"]), 97)
        self.assertEqual(len({x["pr_number"] for x in data["prs"]}), 97)
        absent = [x for x in data["prs"] if not x["eligible_reports"]]
        self.assertEqual({x["pr_number"] for x in absent}, {10648, 10677, 13932})
        for x in data["prs"]:
            self.assertFalse(any("body" in entry for entry in x["other_bot_comment_metadata"]))
            self.assertEqual(len(x["negative_bot_bodies"]) > 0, not bool(x["eligible_reports"]))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_replay(SNAPSHOT, root/"results.json", root/"results.csv", root/"manifest.json")
            self.assertEqual(result["counts"], REQUIRED_COUNTS)
            self.assertEqual(result["by_arm"]["agentic"]["size_report_confirmed"],86)
            self.assertEqual(result["by_arm"]["human_candidate"]["size_report_confirmed"],8)
            self.assertEqual(digest((root/"results.json").read_bytes()),
                             digest((ROOT/"results/rspack97_semantic_size_audit.json").read_bytes()))
        changed = copy.deepcopy(next(x for x in data["prs"] if x["eligible_reports"]))
        changed["eligible_reports"][0]["body"] += "\ntampered"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            assess_saved(changed)

if __name__ == "__main__":
    unittest.main()
