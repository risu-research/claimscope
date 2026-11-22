"""Independent checks of current public source retention and 1,699-PR D6 rates."""
import collections
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from fractions import Fraction

import sensitivity_rspack65_observed_channels as model
import sensitivity_rspack65 as sens

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'results/rspack65_other_source_replay.json'
TABLE=ROOT/'results/rspack65_other_source_replay.csv'
REPORT=ROOT/'results/rspack65_observed_channel_sensitivity.json'

class ObservedSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads(SOURCE.read_text(encoding='utf8'))
        cls.summary=cls.audit['summary']
        cls.rows=cls.audit['rows']
        cls.report=model.run(SOURCE)

    def test_full_65_identity_lock(self):
        rows=self.rows
        self.assertEqual(len(rows),65)
        self.assertEqual(len(set(x['pr_number'] for x in rows)),65)
        self.assertEqual(collections.Counter(x['sample_arm'] for x in rows),{'agentic':60,'human_candidate':5})
        self.assertTrue(all(x['published_D6'] is True for x in rows))
        original,selected=sens.load_inputs(ROOT/'data/rq3_labels.csv',ROOT/'results/rspack_65_comment_pairs.csv',ROOT/'results/rspack_97_comment_boundary_audit.csv')
        self.assertEqual(set(selected),{(sens.RSPACK,str(x['pr_number'])) for x in rows})

    def test_no_independent_positive_on_current_public_sources(self):
        expected=['description','review_comments','commit_messages','ci_metadata','code_diff',
                  'issue_comments_atomic','issue_comments_nonbot_atomic','review_body_supplement']
        for row in self.rows:
            self.assertFalse(row['retained_when_issue_boundaries_preserved'])
            self.assertFalse(row['retained_when_all_source_records_atomic'])
            for s in expected:
                v=row['surfaces'][s]
                self.assertFalse(v['any_atomic'])
                if v['joined_detected'] is not None:self.assertFalse(v['joined_detected'])
        self.assertEqual(self.summary['retention_count_joined_nonissue'],0)
        self.assertEqual(self.summary['retention_count_all_atomic'],0)
        self.assertEqual(self.report['observed_other_source_retention']['retained'],0)

    def test_evidence_scope_and_complete_patch_transmission(self):
        counts=self.summary['total_evidence_objects']
        self.assertEqual(counts['issue_comments'],318)
        self.assertEqual(counts['inline_review_comments'],99)
        self.assertEqual(counts['commits'],236)
        self.assertEqual(counts['ci_workflow_runs'],439)
        self.assertEqual(counts['changed_files'],389)
        self.assertEqual(counts['patches_available'],389)
        self.assertEqual(counts['patches_unavailable'],0)
        self.assertEqual(counts['created_issue_comments_after_cutoff'],0)
        self.assertEqual(counts['updated_issue_comments_after_cutoff'],0)
        self.assertFalse(self.summary['historical_snapshot_available'])
        self.assertEqual(self.summary['pinned_upstream_commit'],sens.PIN if hasattr(sens,'PIN') else '64432e0b6ed7791bbfa929c6c183fc76c75b5d58')

    def test_csv_matches_audit_per_pr(self):
        with TABLE.open(encoding='utf8',newline='') as f: table=list(csv.DictReader(f))
        self.assertEqual(len(table),65)
        by={int(x['pr_number']):x for x in table}
        for x in self.rows:
            y=by[x['pr_number']]
            self.assertEqual(y['sample_arm'],x['sample_arm'])
            self.assertEqual(y['retained_issue_comments_atomic_plus_joined_nonissue'],'False')
            self.assertEqual(y['retained_all_records_atomic'],'False')
            self.assertEqual(int(y['patches_unavailable']),x['counts']['patches_unavailable'])
            self.assertEqual(int(y['ci_workflow_runs']),x['counts']['ci_workflow_runs'])
            for src in ('description','review_comments','commit_messages','ci_metadata','code_diff'):
                self.assertEqual(y[src],str(x['surfaces'][src]['joined_detected']))

    def test_exact_1699_recalculation(self):
        a=self.report['contrasts']['published_labels']
        b=self.report['contrasts']['retain_current_public_source_matches']
        self.assertEqual((a['by_arm']['agentic']['D6_yes'],a['by_arm']['agentic']['n']),(115,858))
        self.assertEqual((a['by_arm']['human_candidate']['D6_yes'],a['by_arm']['human_candidate']['n']),(38,841))
        self.assertEqual((b['by_arm']['agentic']['D6_yes'],b['by_arm']['agentic']['n']),(55,858))
        self.assertEqual((b['by_arm']['human_candidate']['D6_yes'],b['by_arm']['human_candidate']['n']),(33,841))
        self.assertAlmostEqual(a['gap_pp'],100*(Fraction(115,858)-Fraction(38,841)))
        self.assertAlmostEqual(b['gap_pp'],100*(Fraction(55,858)-Fraction(33,841)))
        self.assertAlmostEqual(b['gap_pp'],self.report['contrasts']['65_flags_off_local_scenario']['gap_pp'])

    def test_raw_audit_sha_and_published_report(self):
        self.assertEqual(self.report['origin']['audit_file_sha256'],hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(self.report, json.loads(REPORT.read_text()))

    def test_missing_or_tampered_cohort_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'altered.json'
            obj=json.loads(SOURCE.read_text())
            obj['rows'].pop()
            p.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):model.run(p)

if __name__=='__main__':unittest.main()
