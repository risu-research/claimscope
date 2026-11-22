"""Offline reproduction and tamper tests for the 476 public Rspack comment timestamps."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from audit_rspack97_temporal import (ROOT, LEDGER, SUMMARY, EXPECTED,
                                     EXPECTED_MAX_UPDATE, replay, parse_utc)


class PublicTemporalLedgerTests(unittest.TestCase):
    def test_frozen_source_population(self):
        self.assertTrue(LEDGER.exists())
        with LEDGER.open(newline="", encoding="utf8") as fh:
            rows=list(csv.DictReader(fh))
        self.assertEqual(len(rows),476)
        self.assertEqual(len({r["comment_id"] for r in rows}),476)
        self.assertEqual(len({r["pr_number"] for r in rows}),97)
        self.assertEqual(max(r["updated_at"] for r in rows),EXPECTED_MAX_UPDATE)
        self.assertEqual(sum(r["is_bot"]=="True" for r in rows),437)
        self.assertEqual(sum(r["is_bot"]=="False" for r in rows),39)
        self.assertTrue(all(set(r)=={"pr_number","comment_id","created_at","updated_at","is_bot"}
                            for r in rows))

    def test_self_contained_replay(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"temporal.json"
            result=replay(LEDGER,path)
            self.assertEqual(result["counts"],EXPECTED)
            self.assertEqual(path.read_bytes(),SUMMARY.read_bytes())

    def test_missing_or_modified_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"tampered.csv"
            with LEDGER.open(newline="",encoding="utf8") as fh:
                lines=fh.readlines()
            path.write_text("".join(lines[:-1]),encoding="utf8")
            with self.assertRaises(ValueError):
                replay(path,Path(d)/"bad.json")

    def test_timestamps_have_explicit_utc(self):
        self.assertEqual(parse_utc("2026-06-02T07:58:45Z").isoformat(),
                         "2026-06-02T07:58:45+00:00")
        with self.assertRaises(ValueError):
            parse_utc("2026-06-02T07:58:45")

    def test_public_ledger_excludes_body_or_account(self):
        txt=LEDGER.read_text(encoding="utf8")
        self.assertNotIn("github.com",txt)
        self.assertNotIn("body",txt)
        self.assertNotIn("user_login",txt)
        self.assertNotIn("@",txt)
        self.assertEqual(len(txt.splitlines()),477)

if __name__=="__main__":
    unittest.main()
