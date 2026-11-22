import unittest
from claimscope_stage6 import (Observation,group_stats,pattern_standardized,within_shared,
    influence,certificate,parse_rows,git_blob_sha1,cluster_bootstrap)

def o(repo,num,arm,d,nd=None,pat='memory'):
    return Observation(repo,str(num),arm,pat,d,d if nd is None else nd,f'https://github.com/x/{repo}/pull/{num}')

def fixture():
    return [o('r1',1,'agentic',1),o('r1',2,'agentic',1),o('r1',3,'human_candidate',0),
            o('r2',4,'agentic',0),o('r2',5,'human_candidate',1),o('r3',6,'human_candidate',0)]

class Tests(unittest.TestCase):
    def test_original_blob(self):self.assertEqual(git_blob_sha1(b''),'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
    def test_counts(self):
        s=group_stats(fixture());self.assertEqual((s['groups']['agentic']['positive'],s['groups']['human_candidate']['positive']),(2,1))
    def test_equal_repos(self):
        s=within_shared(fixture());self.assertEqual(s['shared_repos'],2);self.assertEqual(s['positive'],1);self.assertEqual(s['negative'],1)
    def test_influence(self):self.assertGreater(abs(influence(fixture())[0]['shift_pp']),0)
    def test_pattern(self):self.assertAlmostEqual(pattern_standardized(fixture())['standardized_contrast_pp'],100*(2/3-1/3))
    def test_cert(self):self.assertEqual(certificate(fixture())['schema'],'claimscope/metric-influence-certificate/v1')
    def test_seed(self):self.assertEqual(cluster_bootstrap(fixture(),B=100,seed=42),cluster_bootstrap(fixture()[::-1],B=100,seed=42))
    def test_no_group(self):
        with self.assertRaises(ValueError):group_stats([o('x',1,'agentic',1)])
    def test_bad_gate(self):
        x={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','validation_present':'False','in_metric_layer':'True','D6':'True','D6_nodiff':'False','html_url':'z'}
        with self.assertRaises(ValueError):parse_rows([x])
    def test_bad_evidence(self):
        x={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','validation_present':'True','in_metric_layer':'True','D6':'False','D6_nodiff':'True','html_url':'z'}
        with self.assertRaises(ValueError):parse_rows([x])
    def test_duplicate(self):
        x={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','validation_present':'True','in_metric_layer':'True','D6':'True','D6_nodiff':'True','html_url':'z'}
        with self.assertRaises(ValueError):parse_rows([x,x])
    def test_bad_boolean(self):
        x={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','validation_present':'True','in_metric_layer':'True','D6':'1','D6_nodiff':'True','html_url':'z'}
        with self.assertRaises(ValueError):parse_rows([x])
    def test_small_bootstrap(self):
        with self.assertRaises(ValueError):cluster_bootstrap(fixture(),B=5)
    def test_rate_ratio(self):self.assertAlmostEqual(group_stats(fixture())['ratio'],2)
    def test_negative_inference(self):self.assertEqual(certificate(fixture())['interpretation']['causation_or_model_superiority'],'OUTSIDE_MEASUREMENT')


import tempfile
from pathlib import Path
from replay_public import replay

class CrossCohortIntegrityTests(unittest.TestCase):
    def row(self,num,arm='agentic',gate='True'):
        return {'repo_id':'repo','number':str(num),'sample_arm':arm,'pattern':'p',
                'validation_present':gate,'in_metric_layer':gate,'D6':'True',
                'D6_nodiff':'True','html_url':'https://github.com/example/repo/pull/'+str(num)}

    def test_same_pr_across_cohorts_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate PR'):
            parse_rows([self.row(1),self.row(1,'human_candidate')])

    def test_duplicate_excluded_row_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate PR'):
            parse_rows([self.row(1,'agentic','False'),self.row(1,'human_candidate','True')])

    def test_same_number_different_repo_allowed(self):
        x=self.row(1); y=self.row(1,'human_candidate');y['repo_id']='other'
        self.assertEqual(len(parse_rows([x,y])),2)

    def test_local_replay_unverified_fixture(self):
        # Demonstrates runnable CLI without passing fabricated data as original.
        import csv
        rows=[self.row(1),self.row(2,'human_candidate'),self.row(3),self.row(4,'human_candidate')]
        rows[2]['repo_id']='other';rows[3]['repo_id']='other'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.csv';out=Path(d)/'audit.json'
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            result=replay(p,out,verify=False)
            self.assertTrue(out.exists())
            self.assertEqual(result['observed']['groups']['agentic']['n'],2)
            self.assertFalse(result['replay_source']['validated_against_published_aggregate'])

if __name__=='__main__':unittest.main()
