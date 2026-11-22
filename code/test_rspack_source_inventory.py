import csv
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rspack_source_inventory import audit_one, get_pages, rows_from_csv, user_is_bot


def c(i, user, typ, body, date='2026-04-15T08:50:45Z'):
    return {'id': i, 'user': {'login': user, 'type': typ}, 'body': body,
            'created_at': date, 'updated_at': date,
            'html_url': f'https://github.com/web-infra-dev/rspack/pull/13714#issuecomment-{i}'}


class InventoryTests(unittest.TestCase):
    def test_public_baseline(self):
        p = Path(__file__).resolve().parents[1] / 'data/rq3_labels.csv'
        rows = rows_from_csv(p)
        self.assertEqual(len(rows), 97)
        self.assertEqual(sum(x['D6'] == 'True' for x in rows), 83)

    def test_frozen_public_inventory_if_present(self):
        path = Path(__file__).resolve().parents[1] / 'evidence/rspack_97_source_inventory_20261122.csv'
        if not path.exists():
            self.skipTest('Frozen public inventory file enters repository with this revision')
        with path.open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 97)
        self.assertEqual(len(set(x['pr_number'] for x in rows)), 97)
        self.assertEqual(sum(x['published_D6'] == 'True' for x in rows), 83)
        self.assertEqual(sum(x['bot_binary_size_present'] == 'True' for x in rows), 94)
        self.assertEqual(sum(x['published_D6'] == 'False' and x['bot_binary_size_present'] == 'True' for x in rows), 11)
        self.assertEqual(sum(x['comment_created_after_snapshot'] != '0' for x in rows), 0)
        for r in rows:
            self.assertEqual(r['source_url'], f"https://github.com/web-infra-dev/rspack/pull/{r['pr_number']}")
            if r['bot_binary_size_present'] == 'True':
                self.assertIn('#issuecomment-', r['bot_binary_size_comment_url'])

    def test_binary_bot_vs_source_label(self):
        source = {'number': '13714', 'sample_arm': 'agentic', 'D6': 'False',
                  'html_url': 'https://github.com/web-infra-dev/rspack/pull/13714'}
        pr = {'number': 13714, 'user': {'login': 'LingyuCoder'}, 'created_at': '2026-04-15T08:38:21Z'}
        bot = c(1, 'github-actions[bot]', 'Bot', '## 📦 Binary Size-limit\n\nSize decreased by 766.47KB')
        person = c(2, 'reviewer', 'User', 'Binary Size-limit: 12MB')
        late = c(3, 'github-actions[bot]', 'Bot', 'No size report', date='2026-10-01T00:00:00Z')
        row = audit_one(source, pr, [bot, person, late], [])
        self.assertEqual(row['published_D6'], 'False')
        self.assertTrue(row['bot_binary_size_present'])
        self.assertEqual(row['bot_binary_size_count'], 1)
        self.assertEqual(row['comment_created_after_snapshot'], 1)

    def test_bot_type_and_pagination(self):
        self.assertTrue(user_is_bot(c(1, 'github-actions[bot]', 'User', 'binary')))
        self.assertTrue(user_is_bot(c(1, 'automation', 'Bot', 'binary')))
        self.assertFalse(user_is_bot(c(1, 'developer', 'User', 'binary')))
        def getter(url, token):
            if url == 'page1':
                return [{'id': 1}], '<page2>; rel="next"'
            if url == 'page2':
                return [{'id': 2}], ''
            raise ValueError('unexpected page')
        self.assertEqual(len(get_pages('page1', None, getter)), 2)


if __name__ == '__main__':
    unittest.main()
