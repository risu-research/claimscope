#!/usr/bin/env python3
"""Reproducible RQ4/M6 audit against a content-verified public label export.

Online: python replay_public.py --download
Offline: python replay_public.py --csv /path/to/rq3_labels.csv
Output includes a SHA-verified snapshot reference; original snippets are NOT in the export.
"""
from __future__ import annotations
import argparse, hashlib, json, urllib.request
from pathlib import Path
from claimscope_stage6 import GIT_BLOB_ID, git_blob_sha1, load_csv, certificate
URL = 'https://raw.githubusercontent.com/PurdueDualityLab/EMSE-perf-pr-study/64432e0b6ed7791bbfa929c6c183fc76c75b5d58/analysis/classification_labels/rq3_labels.csv'
EXPECTED = {'agentic':{'n':858,'positive':115}, 'human_candidate':{'n':841,'positive':38}}

def replay(path:Path,output:Path,verify=True):
    records=load_csv(path,validate_blob=verify)
    result=certificate(records)
    if verify:
        for arm,exp in EXPECTED.items():
            z=result['observed']['groups'][arm]
            if (z['n'],z['positive'])!=(exp['n'],exp['positive']):
                raise AssertionError(f'published count mismatch: {arm}: {z}')
        lead=result['most_concentrated_repository']
        if (lead['repo_id'],lead['agent_positive_count'])!=('476642602',76):
            raise AssertionError('leading repository mismatch')
    result['replay_source']={'file':str(path),'git_blob_sha1':git_blob_sha1(path.read_bytes()),
        'validated_against_published_aggregate':bool(verify)}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PASS:', len(records),'eligible PRs, D6 contrast (pp):',round(result['observed']['contrast_pp'],6),' -> ',output)
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    source=ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--csv',type=Path,help='local copy of public rq3_labels.csv')
    source.add_argument('--download',action='store_true',help='download public CSV and verify its Git blob SHA')
    ap.add_argument('--output',type=Path,default=Path('observed_replay.json'))
    ap.add_argument('--cache',type=Path,default=Path('source_labels/rq3_labels.csv'))
    ap.add_argument('--skip-sha-check',action='store_true',help='exploratory only; never use for published claims')
    args=ap.parse_args()
    if args.download:
        args.cache.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(URL,timeout=60) as r: raw=r.read()
        sha=git_blob_sha1(raw)
        if sha!=GIT_BLOB_ID and not args.skip_sha_check:
            raise ValueError(f'Upstream CSV differs from published snapshot; expected {GIT_BLOB_ID}, got {sha}')
        args.cache.write_bytes(raw)
        inp=args.cache
    else:inp=args.csv
    replay(inp,args.output,not args.skip_sha_check)

if __name__=='__main__':main()
