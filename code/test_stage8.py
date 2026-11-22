import unittest, pathlib
from stage8_audit import load, run
P=pathlib.Path(__file__).resolve().parent.parent / 'data' / 'rq3_labels.csv'
class Stage8PublicAudit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.z=run(load(P), P)
 def test_exact_decomposition(self):
  d=self.z['decomposition']; self.assertAlmostEqual(d['composition_pp']+d['within_stratum_pp'],d['overall_pp'],places=10)
 def test_known_rate_controls(self):
  c=self.z['counts']; self.assertEqual((c['rspack']['agentic']['yes'],c['rspack']['agentic']['n']), (76,88));self.assertEqual((c['rspack']['human_candidate']['yes'],c['rspack']['human_candidate']['n']),(7,9))
  self.assertEqual((c['other']['agentic']['yes'],c['other']['agentic']['n']),(39,770));self.assertEqual((c['other']['human_candidate']['yes'],c['other']['human_candidate']['n']),(31,832))
 def test_all_ten_dimensions(self):
  a=self.z['dimensions'];self.assertEqual({x['dimension'] for x in a},{'D'+str(x) for x in range(10)})
  d6=next(x for x in a if x['dimension']=='D6');self.assertEqual(d6['rspack_rank_by_abs_influence'],1)
  self.assertAlmostEqual(d6['rspack_influence_pp'],self.z['decomposition']['overall_pp']-100*(c['other']['agentic']['rate']-c['other']['human_candidate']['rate']) if (c:=self.z['counts']) else 0,places=10)
 def test_checksum(self): self.assertEqual(self.z['source_git_blob_sha1'],'136a2cf5bf1a9a71f06f2a7c6c9932194865c854')
if __name__=='__main__':unittest.main()
