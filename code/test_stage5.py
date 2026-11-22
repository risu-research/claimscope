import unittest
from dataclasses import replace
from claimscope_stage5 import (PR,parse_records,repo_stats,pattern_standardized,
    nested_bound,sign_verdict,identification,bootstrap_repo,audit)


def pr(repo,num,arm,full,no_diff=None,description=None,pattern='Memory',url=None):
    if no_diff is None:no_diff=full
    if description is None:description=no_diff
    return PR(repo,str(num),arm,pattern,bool(full),bool(no_diff),bool(description),url or f'https://example.org/{repo}/{num}')


def fixture():
    return [
        pr('one',1,'agentic',1),pr('one',2,'agentic',1),pr('one',3,'agentic',0),
        pr('two',4,'agentic',0,pattern='Algorithm'),pr('three',5,'agentic',1,pattern='Algorithm'),
        pr('one',6,'human_candidate',0),pr('two',7,'human_candidate',1,pattern='Algorithm'),
        pr('two',8,'human_candidate',1,pattern='Algorithm'),pr('three',9,'human_candidate',0,pattern='Algorithm'),
    ]

class ClaimScope5Tests(unittest.TestCase):
    def test_sample_expected_pooled(self):
        x=repo_stats(fixture());self.assertAlmostEqual(x['pooled_contrast'],3/5-2/4)
        self.assertEqual(x['repo_total'],3)
        self.assertEqual(x['shared_repo_count'],3)
    def test_shared_repo_not_pooled(self):
        r=repo_stats(fixture());self.assertNotEqual(r['repo_equal_contrast'],r['pooled_contrast'])
    def test_leave_repo_out_results(self):
        r=repo_stats(fixture());self.assertEqual(len(r['top_leave_one_repo_out']),3)
        self.assertAlmostEqual(r['top_leave_one_repo_out'][0]['shift'],
            r['top_leave_one_repo_out'][0]['contrast']-r['pooled_contrast'])
    def test_resampling_deterministic(self):
        a=bootstrap_repo(fixture(),seed=9,B=100)
        b=bootstrap_repo(list(reversed(fixture())),seed=9,B=100)
        self.assertEqual(a,b)
    def test_pattern_standardization(self):
        r=pattern_standardized(fixture());self.assertEqual(len(r['categories']),2)
        self.assertAlmostEqual(r['pooled'],.1)
    def test_bad_pattern_overlap(self):
        x=fixture()+[pr('one',99,'agentic',1,pattern='OnlyOneArm')]
        with self.assertRaises(ValueError):pattern_standardized(x)
    def test_population_bounds(self):
        a=nested_bound(1129,929,858,437)
        b=nested_bound(1129,910,841,441)
        d=sign_verdict(a['all_pr_bounds'],b['all_pr_bounds'])
        self.assertEqual(d['direction'],'NOT_IDENTIFIED')
        self.assertAlmostEqual(d['contrast_bounds'][0],437/1129-510/1129)
        self.assertAlmostEqual(d['contrast_bounds'][1],508/1129-441/1129)
    def test_invalid_population(self):
        for args in ((10,11,8,7),(10,7,8,3),(10,7,5,6),(0,0,0,0)):
            with self.assertRaises(ValueError):nested_bound(*args)
    def test_tipping(self):
        # Synthetic fixture with custom population counts matching the fixture gates.
        x=identification(fixture(),{'agentic':{'total':6,'validation':6},'human_candidate':{'total':5,'validation':5}})
        self.assertEqual(x['group_bounds']['agentic']['observed_gated'],5)
        self.assertEqual(x['group_bounds']['human_candidate']['observed_gated'],4)
    def test_record_gate_mismatch(self):
        r={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','html_url':'https://example.org',
           'validation_present':'False','in_metric_layer':'True',
           'n_dims':'1','n_dims_nodiff':'1','n_dims_description_only':'0'}
        with self.assertRaises(ValueError):parse_records([r])
    def test_record_surface_violation(self):
        r={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','html_url':'https://example.org',
           'validation_present':'True','in_metric_layer':'True',
           'n_dims':'0','n_dims_nodiff':'1','n_dims_description_only':'0'}
        with self.assertRaises(ValueError):parse_records([r])
    def test_record_duplicate(self):
        r={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','html_url':'https://example.org',
           'validation_present':'True','in_metric_layer':'True',
           'n_dims':'1','n_dims_nodiff':'1','n_dims_description_only':'0'}
        with self.assertRaises(ValueError):parse_records([r,r])
    def test_record_no_positive(self):
        r={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','html_url':'https://example.org',
           'validation_present':'True','in_metric_layer':'False',
           'n_dims':'0','n_dims_nodiff':'0','n_dims_description_only':'0'}
        with self.assertRaises(ValueError):parse_records([r])
    def test_claim_out_of_scope(self):
        p={'agentic':{'total':6,'validation':6},'human_candidate':{'total':5,'validation':5}}
        x=audit(fixture(),bootstrap_B=100,published=p)
        self.assertEqual(x['certificates']['performance_improvement'],'OUTSIDE_MEASUREMENT')
    def test_source_nested(self):
        x=audit(fixture(),bootstrap_B=100,published={'agentic':{'total':6,'validation':6},'human_candidate':{'total':5,'validation':5}})
        self.assertGreaterEqual(x['evidence_surfaces']['agentic']['full'],x['evidence_surfaces']['agentic']['description'])


    def test_cross_arm_same_pr_rejected(self):
        r={'repo_id':'r','number':'1','sample_arm':'agentic','pattern':'p','html_url':'https://example.org',
           'validation_present':'True','in_metric_layer':'True','n_dims':'1',
           'n_dims_nodiff':'1','n_dims_description_only':'1'}
        with self.assertRaisesRegex(ValueError,'duplicate PR'):
            parse_records([r,dict(r,sample_arm='human_candidate')])

if __name__=='__main__':unittest.main()
