#!/usr/bin/env python3
"""Collect a dated, source-linked inventory of public Rspack PR discussions.

This script audits the presence and authorship of binary-size comments. The
original D6 extraction runs over a larger source corpus and is handled in a
separate reproduction stage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE_SHA256 = 'c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9'
RSPACK_ID = '476642602'
SNAPSHOT_CUTOFF = '2026-08-27T23:59:59Z'
FIELDS = (
    'pr_number', 'sample_arm', 'published_D6', 'pr_creator_account',
    'pr_created_at', 'comment_count_issue', 'comment_count_inline_review',
    'bot_binary_size_present', 'bot_binary_size_count', 'bot_binary_size_comment_url',
    'bot_binary_size_comment_created_at', 'bot_bundle_diff_present',
    'comment_created_after_snapshot', 'comment_updated_after_snapshot',
    'source_url',
)
API = 'https://api.github.com/repos/web-infra-dev/rspack'


def rows_from_csv(path: Path):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise ValueError(f'Unexpected input CSV SHA-256: {actual}')
    allrows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    rows = [r for r in allrows if r['repo_id'] == RSPACK_ID and r['in_metric_layer'] == 'True']
    if len(rows) != 97 or len({r['number'] for r in rows}) != 97:
        raise ValueError('Rspack population mismatch')
    assert Counter((r['sample_arm'], r['D6']) for r in rows) == Counter({
        ('agentic', 'True'): 76, ('agentic', 'False'): 12,
        ('human_candidate', 'True'): 7, ('human_candidate', 'False'): 2})
    return rows


def get_json(url: str, token: str | None, attempts: int = 3):
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'claimscope-source-inventory',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    for trial in range(attempts):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res), res.headers.get('Link', '')
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            status = getattr(exc, 'code', None)
            if status in (401, 403, 404, 422):
                raise RuntimeError(f'GitHub API HTTP {status} at {url}') from exc
            if trial == attempts - 1:
                raise
            time.sleep(2 ** trial)
    raise RuntimeError('unreachable')


def get_pages(url: str, token: str | None, getter=get_json):
    result = []
    next_url = url
    seen = set()
    while next_url:
        if next_url in seen:
            raise RuntimeError('Repeated pagination URL')
        seen.add(next_url)
        data, link = getter(next_url, token)
        if not isinstance(data, list):
            raise ValueError(f'Expected an array from {next_url}')
        result.extend(data)
        following = None
        for segment in link.split(','):
            if 'rel="next"' in segment:
                following = segment.split('<', 1)[1].split('>', 1)[0]
        next_url = following
    return result


def user_is_bot(comment):
    user = comment.get('user') or {}
    return user.get('type') == 'Bot' or (user.get('login') or '').endswith('[bot]')


def audit_one(source, pr, issues, reviews, cutoff=SNAPSHOT_CUTOFF):
    number = int(source['number'])
    if int(pr['number']) != number:
        raise ValueError(f'PR identity mismatch: {number}')
    def size_bot(c):
        return user_is_bot(c) and 'binary size-limit' in (c.get('body') or '').lower()
    def bundle_bot(c):
        return user_is_bot(c) and 'rsdoctor bundle diff analysis' in (c.get('body') or '').lower()
    size = sorted((c for c in issues if size_bot(c)), key=lambda c: (c.get('created_at') or '', c['id']))
    comments = issues + reviews
    return {
        'pr_number': number,
        'sample_arm': source['sample_arm'],
        'published_D6': source['D6'],
        'pr_creator_account': (pr.get('user') or {}).get('login', ''),
        'pr_created_at': pr.get('created_at') or '',
        'comment_count_issue': len(issues),
        'comment_count_inline_review': len(reviews),
        'bot_binary_size_present': bool(size),
        'bot_binary_size_count': len(size),
        'bot_binary_size_comment_url': size[0].get('html_url', '') if size else '',
        'bot_binary_size_comment_created_at': size[0].get('created_at', '') if size else '',
        'bot_bundle_diff_present': any(bundle_bot(c) for c in issues),
        'comment_created_after_snapshot': sum((c.get('created_at') or '') > cutoff for c in comments),
        'comment_updated_after_snapshot': sum((c.get('updated_at') or '') > cutoff for c in comments),
        'source_url': source['html_url'],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv', type=Path, default=Path(__file__).resolve().parents[1] / 'data/rq3_labels.csv')
    ap.add_argument('--output', type=Path, default=Path('build/rspack_source_inventory.csv'))
    ap.add_argument('--max-prs', type=int, default=97)
    args = ap.parse_args()
    if not 1 <= args.max_prs <= 97:
        ap.error('--max-prs must be between 1 and 97')
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    sources = rows_from_csv(args.csv)[:args.max_prs]
    output = []
    for source in sources:
        number = int(source['number'])
        pr, _ = get_json(f'{API}/pulls/{number}', token)
        issues = get_pages(f'{API}/issues/{number}/comments?per_page=100', token)
        reviews = get_pages(f'{API}/pulls/{number}/comments?per_page=100', token)
        output.append(audit_one(source, pr, issues, reviews))
        print(f'Checked {number}: {len(issues)} issue comments, {len(reviews)} inline reviews', file=sys.stderr)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    summary = Counter((r['published_D6'], r['bot_binary_size_present']) for r in output)
    print(json.dumps({'checked_prs': len(output),
                      'D6_x_bot_binary': {f'{d}_{str(b).lower()}': n for (d, b), n in summary.items()},
                      'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
