"""Offline integrity tests for the 1,699-PR Rspack D6 boundary-sensitivity replay."""
from __future__ import annotations
import csv
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from fractions import Fraction

import sensitivity_rspack65 as model

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/rq3_labels.csv'
PAIRS=ROOT/'results/rspack_65_comment_pairs.csv'
BOUNDARY=ROOT/'results/rspack_97_comment_boundary_audit.csv'
OUTPUT=ROOT/'results/rspack_65_fullcohort_sensitivity.json'

class RspackSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original,cls.selected=model.load_inputs(SOURCE,PAIRS,BOUNDARY)
        cls.scenario=model.set_selected_off(cls.original,cls.selected)
        cls.result=json.loads(OUTPUT.read_text(encoding='utf8'))

    def test_input_hashes_and_complete_cohort(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),model.SOURCE_SHA256)
        self.assertEqual(model.core.git_blob_sha1(PAIRS.read_bytes()),model.PAIR_BLOB_SHA)
        self.assertEqual(len(self.original),1699)
        self.assertEqual(len(model.core.repo_index(self.original)),440)
        self.assertEqual(len(self.selected),65)

    def test_exact_witness_join_and_arm_counts(self):
        self.assertEqual(sum(x=='agentic' for x in self.selected.values()),60)
        self.assertEqual(sum(x=='human_candidate' for x in self.selected.values()),5)
        self.assertEqual({x.repo for x in self.original if (x.repo,x.pr) in self.selected},{model.RSPACK})
        for x in self.original:
            if (x.repo,x.pr) in self.selected:
                self.assertEqual((x.M6,x.M6_no_diff),(1,1))

    def test_original_and_scenario_counts_independent_arithmetic(self):
        for arm,n,published,lowered in [('agentic',858,115,55),('human_candidate',841,38,33)]:
            o=[x for x in self.original if x.arm==arm]
            s=[x for x in self.scenario if x.arm==arm]
            self.assertEqual((len(o),sum(x.M6 for x in o),sum(x.M6 for x in s)),(n,published,lowered))
        base=100*(Fraction(115,858)-Fraction(38,841))
        alt=100*(Fraction(55,858)-Fraction(33,841))
        self.assertAlmostEqual(self.result['scenarios']['published']['gap_pp'],float(base))
        self.assertAlmostEqual(self.result['scenarios']['disable_65_D6_flags']['gap_pp'],float(alt))
        self.assertAlmostEqual(self.result['effects']['absolute_shift_pp'],float(alt-base))
        self.assertAlmostEqual(self.result['effects']['gap_attenuation_fraction'],float((base-alt)/base))

    def test_all_unaffected_records_bitwise_preserved(self):
        changes=[]
        for a,b in zip(self.original,self.scenario):
            if a!=b:changes.append((a.repo,a.pr))
            else:self.assertEqual(a,b)
        self.assertEqual(set(changes),set(self.selected))
        self.assertEqual(len(changes),65)

    def test_exclusion_options_and_repo_counts(self):
        r=self.result['scenarios']
        self.assertAlmostEqual(r['exclude_65_PR_rows']['gap_pp'],100*(55/798-33/836))
        self.assertAlmostEqual(r['exclude_Rspack_repository']['gap_pp'],100*(39/770-31/832))
        self.assertEqual(r['exclude_65_PR_rows']['by_arm']['agentic']['n'],798)
        self.assertEqual(r['exclude_65_PR_rows']['by_arm']['human_candidate']['n'],836)
        self.assertEqual(r['Rspack_disable_65']['by_arm']['agentic']['D6_yes'],16)
        self.assertEqual(r['Rspack_disable_65']['by_arm']['human_candidate']['D6_yes'],2)

    def test_decomposition_closes_exactly(self):
        for name,sc in [('published','published'),('disable_65','disable_65_D6_flags')]:
            decomp=self.result['two_stratum_kitagawa'][name]
            pooled=self.result['scenarios'][sc]['gap_pp']
            self.assertAlmostEqual(decomp['composition_component_pp']+decomp['within_rate_component_pp'],pooled,places=10)
        self.assertEqual(self.result['within_shared_repository']['published']['shared_repos'],84)
        self.assertEqual(self.result['within_shared_repository']['disable_65']['shared_repos'],84)

    def test_other_evidence_retention_grid_bounds(self):
        bounds=self.result['other_evidence_channel_retention']
        self.assertEqual(bounds['all_count_combinations'],366)
        self.assertTrue(bounds['always_positive_under_local_scope'])
        self.assertAlmostEqual(bounds['conditional_gap_min_pp'],100*(55/858-38/841))
        self.assertAlmostEqual(bounds['conditional_gap_max_pp'],100*(115/858-33/841))

    def test_paired_bootstrap_determinism(self):
        a=model.paired_cluster_bootstrap(self.original,self.scenario,B=200,seed=42)
        b=model.paired_cluster_bootstrap(self.original,self.scenario,B=200,seed=42)
        self.assertEqual(a,b)
        self.assertEqual(a['repository_count'],440)
        self.assertEqual(a['retained_draws'],200)
        self.assertLessEqual(a['metrics']['scenario_minus_published']['percentile_95_pp'][1],0)

    def test_published_scenario_table(self):
        p=ROOT/'results/rspack_65_fullcohort_scenarios.csv'
        with p.open(newline='',encoding='utf8') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),6)
        self.assertEqual({x['scenario'] for x in rows},set(self.result['scenarios']))
        for x in rows:
            data=self.result['scenarios'][x['scenario']]
            self.assertAlmostEqual(float(x['contrast_pp']),data['gap_pp'],places=8)
            for arm,prefix in [('agentic','agentic'),('human_candidate','human_candidate')]:
                self.assertEqual(int(x[prefix+'_n']),data['by_arm'][arm]['n'])
                self.assertEqual(int(x[prefix+'_D6_yes']),data['by_arm'][arm]['D6_yes'])

    def test_input_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=Path(tmp)/'altered.csv'
            q.write_bytes(PAIRS.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'differs from frozen witness'):
                model.load_inputs(SOURCE,q,BOUNDARY)

    def test_written_result_follows_current_inputs(self):
        regenerated=model.run(SOURCE,PAIRS,BOUNDARY,B=160,seed=21)
        self.assertEqual(regenerated['input_provenance']['unique_PRs'],65)
        self.assertEqual(regenerated['effects'],self.result['effects'])
        self.assertEqual(regenerated['other_evidence_channel_retention'],self.result['other_evidence_channel_retention'])

if __name__=='__main__':unittest.main()
