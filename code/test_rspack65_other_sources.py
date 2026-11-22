"""Offline contracts for the exact-source Rspack 65-PR replay."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_rspack65_other_sources as audit


class SourceAuditTests(unittest.TestCase):
    def test_locked_cohort_and_arms(self):
        refs=audit.load_ids(audit.PAIRS)
        self.assertEqual(len(refs),65)
        self.assertEqual(sum(v=='agentic' for v in refs.values()),60)
        self.assertEqual(sum(v=='human_candidate' for v in refs.values()),5)

    def test_rejects_tampered_witness(self):
        with audit.PAIRS.open(newline='',encoding='utf8') as f:
            values=list(csv.DictReader(f))
            keys=list(values[0])
        values[0]['cue_comment_id']=values[0]['quant_comment_id']
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.csv'
            with p.open('w',newline='',encoding='utf8') as f:
                w=csv.DictWriter(f,fieldnames=keys)
                w.writeheader();w.writerows(values)
            with self.assertRaises(ValueError):audit.load_ids(p)

    def test_item_level_and_joined_source_are_separate(self):
        def fake(t, include_positions=False):
            if 'binary size' in t and '49.5MB' in t:
                return {'D6':[{'rule_id':'SIM','cue':'binary size','quant':'49.5MB','snippet':t}]}
            return {}
        x=[audit.item('49.5MB',1,'https://example.org/1'),
           audit.item('binary size',2,'https://example.org/2')]
        result=audit.inspect_items(fake,x,'issue_comments',True)
        self.assertFalse(result['any_atomic'])
        self.assertTrue(result['joined_detected'])
        self.assertEqual(result['atomic_positive_records'],0)
        self.assertEqual(result['joined_match_count'],1)

    def test_single_record_source_witness(self):
        def fake(t, include_positions=False):
            return {'D6':[{'rule_id':'SIM','cue':'bundle','quant':'2 MB'}]} if '2 MB bundle' in t else {}
        result=audit.inspect_items(fake,[audit.item('2 MB bundle',99,'https://example.org/99','analyst')], 'description',True)
        self.assertTrue(result['any_atomic'])
        self.assertEqual(result['atomic_evidence'][0]['record_id'],'99')
        self.assertEqual(result['atomic_evidence'][0]['first_hit']['account'],'analyst')

    def test_deduplicates_workflow_names_in_metadata_only(self):
        runs=[{'id':1,'name':'CI','html_url':'https://example.org/1'},
              {'id':2,'name':'CI','html_url':'https://example.org/2'}]
        with patch.object(audit,'checked_fetch',return_value=json.dumps({'total_count':2,'workflow_runs':runs}).encode()):
            vals,meta=audit.workflow_run_names('a'*40,13010,None)
        self.assertEqual(len(vals),2)
        self.assertEqual(meta['unique_workflow_names'],1)
        self.assertEqual(meta['historical_snapshot_equivalence'],'unverified')


if __name__=='__main__':unittest.main()
