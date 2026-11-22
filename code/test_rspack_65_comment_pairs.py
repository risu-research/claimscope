"""Offline integrity tests for the 65-PR original-extractor comment-pair trace."""
import csv
import json
from pathlib import Path
import unittest
from collections import Counter
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results'


def read_rows(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


class CommentPairLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=read_rows(RESULTS/'rspack_97_comment_boundary_audit.csv')
        cls.ledger=read_rows(RESULTS/'rspack_65_comment_pairs.csv')
        cls.details=json.loads((RESULTS/'rspack_65_comment_pair_audit.json').read_text(encoding='utf-8'))
        cls.summary=json.loads((RESULTS/'rspack_65_comment_pair_summary.json').read_text(encoding='utf-8'))
        cls.labels=[r for r in read_rows(ROOT/'data/rq3_labels.csv')
                    if r['repo_id']=='476642602' and r['in_metric_layer']=='True']

    def test_cohort_coverage_and_source_label_consistency(self):
        self.assertEqual(len(self.baseline),97)
        self.assertEqual(len(self.labels),97)
        ids={int(x['number']) for x in self.labels}
        self.assertEqual(len(ids),97)
        original={int(x['number']):x['D6'] for x in self.labels}
        self.assertEqual({int(x['pr_number']) for x in self.baseline},ids)
        for r in self.baseline:
            self.assertEqual(r['published_D6'],original[int(r['pr_number'])])
        cross={int(x['pr_number']) for x in self.baseline
               if x['all_concat_D6']=='True' and x['all_individual_D6']=='False' and x['all_padded_D6']=='False'}
        self.assertEqual(len(cross),65)
        self.assertEqual({int(x['pr_number']) for x in self.ledger},cross)
        self.assertEqual({x['pr_number'] for x in self.details['rows']},cross)
        self.assertEqual(self.summary['cross_comment_only_PRs'],65)
        self.assertEqual(self.summary['exact_full_cohort_replay'],97)

    def test_every_match_references_two_public_comments(self):
        self.assertEqual(len(self.ledger),72)
        seen=set()
        for r in self.ledger:
            n=int(r['pr_number'])
            cue=int(r['cue_comment_id'])
            quant=int(r['quant_comment_id'])
            self.assertNotEqual(cue,quant)
            self.assertTrue(r['cue_comment_url'].endswith(f'#issuecomment-{cue}'))
            self.assertTrue(r['quant_comment_url'].endswith(f'#issuecomment-{quant}'))
            self.assertTrue(r['cue_comment_url'].startswith('https://github.com/web-infra-dev/rspack/pull/'))
            self.assertTrue(r['quant_comment_url'].startswith('https://github.com/web-infra-dev/rspack/pull/'))
            self.assertEqual(r['source_comment_gap'],'1')
            self.assertEqual(r['pair_only_D6'],'True')
            self.assertEqual(r['pair_with_separator_D6'],'False')
            self.assertEqual(r['cue_D6_alone'],'False')
            self.assertEqual(r['quant_D6_alone'],'False')
            self.assertEqual(r['cue_comment_account'],'github-actions[bot]')
            self.assertEqual(r['quant_comment_account'],'github-actions[bot]')
            self.assertLess(r['quant_comment_created_at'],r['cue_comment_created_at'])
            key=(n, cue,quant)
            self.assertNotIn(key,seen)
            seen.add(key)
        self.assertEqual(self.summary['unique_cue_quant_comment_id_pairs'],len(seen))
        self.assertEqual(self.summary['pair_only_D6_count'],72)
        self.assertEqual(self.summary['pair_with_separator_D6_count'],0)

    def test_original_span_counts_and_mapping(self):
        count=0
        for p in self.details['rows']:
            self.assertTrue(p['normalization_mapping_exact'])
            self.assertTrue(p['cross_comment_only'])
            self.assertEqual(p['original_D6_match_count'],p['cross_comment_match_count'])
            self.assertEqual(p['cross_comment_match_count'],len(p['pairs']))
            self.assertEqual(p['unlocated_hits'],[])
            count+=p['cross_comment_match_count']
        self.assertEqual(count,72)
        self.assertEqual(self.summary['mapping_anomalies'],[])

    def test_type_and_arm_counts(self):
        types=Counter(f"{p['quant_comment_type']} -> {p['cue_comment_type']}" for p in self.ledger)
        self.assertEqual(dict(types),self.summary['source_type_pairs'])
        groups=Counter(x['sample_arm'] for x in self.details['rows'])
        self.assertEqual(dict(groups),self.summary['cohort_cross_only_by_arm'])
        self.assertEqual(groups,{'agentic':60,'human_candidate':5})
        self.assertEqual(types,{'rsdoctor_bundle_diff -> binary_size_limit':33,
             'binary_size_limit -> rsdoctor_bundle_diff':29,
             'other_benchmark -> rsdoctor_bundle_diff':8,
             'other_benchmark -> binary_size_limit':2})


if __name__=='__main__':
    unittest.main()
