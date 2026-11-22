#!/usr/bin/env python3
"""Independent semantic report-presence audit of 65 Rspack PR threads.

No D6 extractor is called. Uses fixed, transparent evidence criteria:
- a PR-thread GitHub Actions report posted before original snapshot cutoff;
- named binary-size or bundler-output-size measurement;
- a concrete numeric quantity with byte-based unit;
- a completed observation (increase, decrease, unchanged, or table size).
- PR revision attribution is recorded separately from report presence.

This audits *report presence*, not performance improvement, causality or human authorship.
Full historical original parquet evidence is not available; current public API
is checked again, with source URLs, SHA256 and timestamps retained.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError

from audit_rspack65_other_sources import load_ids
from audit_rspack_11_exact import CUTOFF, ROOT, REPO, get_pr, get_paginated, bot_flag

PAIRS=ROOT/'results/rspack_65_comment_pairs.csv'
OUT=ROOT/'results/rspack65_semantic_size_audit.json'
CSV=ROOT/'results/rspack65_semantic_size_audit.csv'

# A GitHub Actions report is not an agent-authored claim. These patterns verify
# the observation that was made, not the reliability or causal meaning of it.
UNITS=r'(?:bytes?|B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)'
NUMBER=r'\d+(?:\.\d+)?'
BINARY_DELTA=re.compile(r'\bSize\s+(?P<direction>increased|decreased)\s+by\s+'
    rf'(?P<delta>{NUMBER})\s*(?P<delta_unit>{UNITS})\s+from\s+'
    rf'(?P<before>{NUMBER})\s*(?P<before_unit>{UNITS})\s+to\s+'
    rf'(?P<after>{NUMBER})\s*(?P<after_unit>{UNITS})',re.I)
BINARY_SAME=re.compile(r'\bSize\s+remains\s+the\s+same\s+at\s+'
    rf'(?P<value>{NUMBER})\s*(?P<unit>{UNITS})',re.I)
TABLE_SIZE=re.compile(rf'(?m)^\|\s*(?P<artifact>[^|\n]+?)\s*\|\s*(?P<value>{NUMBER})\s*(?P<unit>{UNITS})\s*\|')
SHA_LINK=re.compile(r'https://github\.com/web-infra-dev/rspack/commit/([a-f0-9]{40})',re.I)


def sha256(s:str)->str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def binary_report(body:str)->dict|None:
    if not re.search(r'^##\s*📦\s*Binary Size-limit\s*$',body,re.M):
        return None
    links=SHA_LINK.findall(body)
    line=next((s.strip() for s in body.splitlines() if re.search(r'\bSize\s+(increased|decreased|remains)\b',s,re.I)),None)
    if line is None:
        return {'structured':False,'reason':'missing binary-size measurement line','source_commit':links[0] if links else None,'comparator_commit':links[1] if len(links)>1 else None}
    m=BINARY_DELTA.search(line)
    if m:
        return {'structured':True,'kind':'binary_size_delta','direction':m['direction'].lower(),
            'delta':m['delta']+m['delta_unit'], 'before':m['before']+m['before_unit'],
            'after':m['after']+m['after_unit'],'evidence_line':line[:240],
            'source_commit':links[0] if links else None,'comparator_commit':links[1] if len(links)>1 else None}
    m=BINARY_SAME.search(line)
    if m:
        return {'structured':True,'kind':'binary_size_unchanged','direction':'unchanged',
            'value':m['value']+m['unit'],'evidence_line':line[:240],
            'source_commit':links[0] if links else None,'comparator_commit':links[1] if len(links)>1 else None}
    return {'structured':False,'reason':'unrecognized binary-size line','evidence_line':line[:240],
        'source_commit':links[0] if links else None,'comparator_commit':links[1] if len(links)>1 else None}


def rsdoctor_report(body:str)->dict|None:
    if not re.search(r'^##\s*Rsdoctor Bundle Diff Analysis\s*$',body,re.M):
        return None
    if not re.search(r'\|\s*Project\s*\|\s*Total Size\s*\|',body,re.I):
        return {'structured':False,'reason':'no Total Size table'}
    rows=[(m['artifact'].strip(),m['value']+m['unit']) for m in TABLE_SIZE.finditer(body)]
    if not rows:
        return {'structured':False,'reason':'no concrete byte-unit size rows'}
    return {'structured':True,'kind':'bundler_output_size_table','n_artifacts':len(rows),
        'artifacts':[{'name':a,'size':b} for a,b in rows[:15]],'evidence_line':f'{rows[0][0]}: {rows[0][1]}'}


def classify_report(body:str,kind:str)->dict|None:
    if kind=='binary':return binary_report(body)
    if kind=='rsdoctor':return rsdoctor_report(body)
    return None


def is_pre_cutoff(comment:dict)->bool:
    return (comment.get('created_at') or '')<=CUTOFF and (comment.get('updated_at') or '')<=CUTOFF


def assess_one(pr_number:int,arm:str,token:str|None)->dict:
    p=get_pr(pr_number,token)
    if p.get('number')!=pr_number:raise ValueError('PR mismatch')
    comments=get_paginated(f'issues/{pr_number}/comments',token)
    commits=get_paginated(f'pulls/{pr_number}/commits',token)
    commit_set={c.get('sha') for c in commits if c.get('sha')}
    head=p.get('head',{}).get('sha')
    if not head:raise ValueError('No PR head')
    matches=[]
    for c in comments:
        body=c.get('body') or ''
        if not bot_flag(c):continue
        for kind in ('binary','rsdoctor'):
            m=classify_report(body,kind)
            if m is None:continue
            source=m.get('source_commit')
            # The source commit is the first linked ref in the report. Historical
            # head revisions that have been rebased may not be in current API.
            commit_relation=('current_head' if source==head else
                'current_pr_commit' if source in commit_set else
                'not_verified_against_current_pr_commits' if source else 'not_in_report')
            matches.append({'source_kind':kind,'comment_id':c['id'],
                'comment_url':c.get('html_url') or f'https://github.com/{REPO}/pull/{pr_number}#issuecomment-{c["id"]}',
                'comment_author':(c.get('user') or {}).get('login'),
                'created_at':c.get('created_at'),'updated_at':c.get('updated_at'),
                'before_historical_cutoff':is_pre_cutoff(c),'body_sha256':sha256(body),
                'size_measurement':m,'sha_relation':commit_relation})
    qualifying=[r for r in matches if r['before_historical_cutoff'] and r['size_measurement'].get('structured')]
    binary=[r for r in qualifying if r['source_kind']=='binary']
    rsd=[r for r in qualifying if r['source_kind']=='rsdoctor']
    anchored_binary=[r for r in binary if r['sha_relation'] in ('current_head','current_pr_commit')]
    # Strict: observed artifact-size reporting, separate from PR-caused delta.
    status='confirmed' if qualifying else ('unclear' if matches else 'no_evidence')
    attribution=('commit_matched' if anchored_binary else
        'attached_thread_without_commit_match' if binary else
        'bundler_table_only' if rsd else 'unverified')
    return {'pr_number':pr_number,'arm':arm,'published_D6':True,
        'url':f'https://github.com/{REPO}/pull/{pr_number}',
        'report_presence':status,'pr_revision_attribution':attribution,
        'number_binary_reports':len(binary),'number_rsdoctor_reports':len(rsd),
        'size_change_reported':bool(any(r['size_measurement'].get('kind')=='binary_size_delta' for r in binary)),
        'unchanged_size_reported':bool(any(r['size_measurement'].get('kind')=='binary_size_unchanged' for r in binary)),
        'source_head_sha':head,'n_current_pr_commits':len(commit_set),
        'n_issue_comments':len(comments),'matches':matches,
        'chosen_evidence':(anchored_binary or binary or rsd or matches or [None])[0]}


def summarize(rows:list[dict])->dict:
    assert len(rows)==65 and len({r['pr_number'] for r in rows})==65
    byarm={arm:[r for r in rows if r['arm']==arm] for arm in ('agentic','human_candidate')}
    return {'schema':'claimscope/rspack65-semantic-size-v1',
        'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'criteria':[
            'Public GitHub PR-thread comment by automation before 2026-08-27 cutoff',
            'Report names a binary-size or bundler-output-size artifact',
            'Concrete observed number with byte-based size unit',
            'Measured increase, decrease or unchanged size accepted; optimization not inferred',
            'Head-SHA or PR-commit attribution tracked separately from report presence',
            'No Peng D6 regex/label used to decide semantic presence'],
        'population':65,'by_arm':{a:{'n':len(v),
             'confirmed':sum(r['report_presence']=='confirmed' for r in v),
             'pr_commit_matched':sum(r['pr_revision_attribution']=='commit_matched' for r in v)} for a,v in byarm.items()},
        'presence_counts':dict(collections.Counter(r['report_presence'] for r in rows)),
        'revision_attribution_counts':dict(collections.Counter(r['pr_revision_attribution'] for r in rows)),
        'size_change_reported':sum(r['size_change_reported'] for r in rows),
        'unchanged_size_reported':sum(r['unchanged_size_reported'] for r in rows),
        'binary_size_report_present':sum(r['number_binary_reports']>0 for r in rows),
        'rsdoctor_report_present':sum(r['number_rsdoctor_reports']>0 for r in rows),
        'incomplete_or_unrecognized':[r['pr_number'] for r in rows if r['report_presence']!='confirmed'],
        'unanchored':[r['pr_number'] for r in rows if r['report_presence']=='confirmed' and r['pr_revision_attribution']!='commit_matched'],
        'scope_limit':'Current public PR-thread evidence; no historical upstream Parquet snapshot. Structured source audit, not blinded human adjudication. Report presence ≠ PR-caused improvement.'}


def write_rows(rows:list[dict],summary:dict,out:Path,csv_out:Path):
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'summary':summary,'rows':rows},ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8')
    fields=['pr_number','arm','report_presence','pr_revision_attribution','number_binary_reports','number_rsdoctor_reports',
        'size_change_reported','unchanged_size_reported','comment_id','comment_url','source_kind','direction','observed_number',
        'evidence_line','source_commit','comparator_commit','sha_relation','comment_created_at','comment_updated_at','body_sha256']
    with csv_out.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            e=r['chosen_evidence'] or {};m=e.get('size_measurement',{})
            w.writerow({'pr_number':r['pr_number'],'arm':r['arm'],'report_presence':r['report_presence'],
                'pr_revision_attribution':r['pr_revision_attribution'],
                'number_binary_reports':r['number_binary_reports'],'number_rsdoctor_reports':r['number_rsdoctor_reports'],
                'size_change_reported':r['size_change_reported'],'unchanged_size_reported':r['unchanged_size_reported'],
                'comment_id':e.get('comment_id'),'comment_url':e.get('comment_url'),'source_kind':e.get('source_kind'),
                'direction':m.get('direction'),'observed_number':m.get('after') or m.get('value') or (m.get('artifacts') or [{}])[0].get('size'),
                'evidence_line':m.get('evidence_line'),'source_commit':m.get('source_commit'),
                'comparator_commit':m.get('comparator_commit'),'sha_relation':e.get('sha_relation'),
                'comment_created_at':e.get('created_at'),'comment_updated_at':e.get('updated_at'),
                'body_sha256':e.get('body_sha256')})
    print('SEMANTIC_SUMMARY '+json.dumps(summary,sort_keys=True,ensure_ascii=False),flush=True)
    print('SEMANTIC_OUTPUT '+json.dumps({'csv':str(csv_out),'json':str(out)}),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--max-workers',type=int,default=5)
    p.add_argument('--max-prs',type=int,default=0)
    p.add_argument('--pairs',type=Path,default=PAIRS)
    p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--csv',type=Path,default=CSV)
    a=p.parse_args(); ids=load_ids(a.pairs)
    if a.max_prs: ids=dict(list(ids.items())[:a.max_prs])
    token=os.environ.get('GITHUB_TOKEN');rows=[];errors=[]
    def job(e):
        for i in range(3):
            try:return assess_one(*e,token)
            except HTTPError as ex:
                if ex.code in (403,429,500,502,503,504) and i<2: time.sleep(3*(i+1));continue
                raise
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.max_workers) as ex:
        pending={ex.submit(job,x):x[0] for x in ids.items()}
        for f in concurrent.futures.as_completed(pending):
            number=pending[f]
            try:
                v=f.result();rows.append(v)
                print('SEMANTIC_PR '+json.dumps({'pr':number,'status':v['report_presence'],
                  'revision':v['pr_revision_attribution'],'binary':v['number_binary_reports'],
                  'rsdoctor':v['number_rsdoctor_reports']}),flush=True)
            except Exception as err:
                errors.append({'pr':number,'error':f'{type(err).__name__}: {err}'[:300]})
    if errors:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.with_name('rspack65_semantic_size_errors.json').write_text(json.dumps(errors,indent=2)+'\n')
        raise RuntimeError(f'{len(errors)} PR failures: {errors[:3]}')
    rows.sort(key=lambda x:x['pr_number'])
    if a.max_prs:
        print('SEMANTIC_SMOKE '+json.dumps({'n':len(rows),'positive':sum(r['report_presence']=='confirmed' for r in rows)}));return
    summary=summarize(rows)
    write_rows(rows,summary,a.out,a.csv)

if __name__=='__main__':main()
