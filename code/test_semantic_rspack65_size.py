"""Non-network tests for a distinct source-observation rubric."""
import unittest
from semantic_rspack65_size import binary_report,rsdoctor_report,summarize

class SemanticSizeRubricTests(unittest.TestCase):
    def test_delta_size_valid_with_head_and_base(self):
        a='a'*40;b='b'*40
        t=f'## 📦 Binary Size-limit\n> Comparing [`aaa`](https://github.com/web-infra-dev/rspack/commit/{a}) to [main](https://github.com/web-infra-dev/rspack/commit/{b})\n\n🎉 Size decreased by 48.00KB from 48.65MB to 48.61MB (⬇️0.10%)'
        v=binary_report(t)
        self.assertTrue(v['structured']);self.assertEqual(v['before'],'48.65MB');self.assertEqual(v['after'],'48.61MB')
        self.assertEqual(v['source_commit'],a);self.assertEqual(v['comparator_commit'],b)
    def test_literal_bytes_without_space(self):
        for delta in ('288bytes','416bytes'):
            v=binary_report(f'## 📦 Binary Size-limit\n❌ Size increased by {delta} from 49.09MB to 49.09MB')
            self.assertTrue(v['structured']);self.assertEqual(v['delta'],delta)

    def test_unchanged_is_report_not_gain(self):
        v=binary_report('## 📦 Binary Size-limit\n\n🙈 Size remains the same at 62.85MB')
        self.assertTrue(v['structured']);self.assertEqual(v['direction'],'unchanged')
    def test_rsdoctor_report(self):
        v=rsdoctor_report('## Rsdoctor Bundle Diff Analysis\n| Project | Total Size | Change |\n|---|---|---|\n| rome | 984.2 KB | 0 |')
        self.assertTrue(v['structured']);self.assertEqual(v['artifacts'][0]['size'],'984.2KB')
    def test_memory_not_size(self):
        self.assertIsNone(binary_report('Base RSS memory 600 MB; current RSS memory 800MB'))
        self.assertIsNone(rsdoctor_report('## Benchmark detail\n| Build RSS | 900 MB |'))
    def test_threshold_is_not_observation(self):
        v=binary_report('## 📦 Binary Size-limit\nBudget is 70MB; fail if over 70MB')
        self.assertFalse(v['structured'])
    def test_rsdoctor_no_data(self):
        self.assertFalse(rsdoctor_report('## Rsdoctor Bundle Diff Analysis\nNo baseline data; no table')['structured'])
    def test_both_directions(self):
        for direction in ('increased','decreased'):
            v=binary_report(f'## 📦 Binary Size-limit\n❌ Size {direction} by 4.00KB from 62.86MB to 62.87MB')
            self.assertTrue(v['structured']);self.assertEqual(v['direction'],direction)

if __name__=='__main__':unittest.main()
