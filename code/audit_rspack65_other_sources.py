#!/usr/bin/env python3
"""Source-specific D6 retention among 65 Rspack boundary-dependent PRs.

Uses Peng et al.'s exact hash-pinned metric extractor. Fetches current public
PR evidence from GitHub, preserving individual issue-comment boundaries.
Historical snapshot evidence and full original extractor reruns are separate.
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
import time
from urllib.error import HTTPError

from audit_rspack_11_exact import (
    CUTOFF, PIN, BLOB_SHAS, REPO, ROOT, checked_fetch,
    get_paginated, get_pr, load_original_extractor, bot_flag
)

PAIRS = ROOT / 'results/rspack_65_comment_pairs.csv'
OUTPUT = ROOT / 'results/rspack65_other_source_replay.json'
CSV_OUTPUT = ROOT / 'results/rspack65_other_source_replay.csv'
AUDIT_VERSION = 'claimscope/rspack65-other-sources/v1'
PRIMARY = ('description','review_comments','commit_messages','ci_metadata','code_diff')
ISSUES = ('issue_comments_atomic','issue_comments_nonbot_atomic')


def load_ids(path: Path) -> dict[int, str]:
    with path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 72:
        raise ValueError(f'Expected 72 source-linked witness pairs, found {len(rows)}')
    out: dict[int,str] = {}
    for r in rows:
        n = int(r['pr_number'])
        arm = r['sample_arm']
        if r['published_D6'] != 'True' or arm not in ('agentic', 'human_candidate'):
            raise ValueError(f'Unexpected status for PR {n}')
        if n in out and out[n] != arm:
            raise ValueError('Inconsistent arm within witness pairs')
        if r['cue_comment_id'] == r['quant_comment_id']:
            raise ValueError('Non-cross-comment witness')
        if r['pair_only_D6'] != 'True' or r['pair_with_separator_D6'] != 'False':
            raise ValueError('Witness fails pair-control invariant')
        out[n]=arm
    if len(out)!=65 or collections.Counter(out.values())!=collections.Counter({'agentic':60,'human_candidate':5}):
        raise ValueError('Unexpected 65-case cohort')
    return dict(sorted(out.items()))


def short_witness(hit: dict, kind: str, url: str, identity: str|int, account: str|None, timestamp: str|None) -> dict:
    return {
        'source':kind,'record_id':str(identity),'url':url,'account':account,'created_at':timestamp,
        'rule_id':hit.get('rule_id'),'cue':hit.get('cue'),'quant':hit.get('quant'),
        'quant_kind':hit.get('quant_kind'),'snippet':hit.get('snippet','')[:260],
    }


def inspect_items(extract, items: list[dict], group: str, aggregate: bool) -> dict:
    # Each item: {text, id, url, account, created_at}. Position inside one
    # independently inspected source record is attributable to that record.
    present = []
    for item in items:
        hits = extract(item['text'], include_positions=True).get('D6', [])
        if hits:
            present.append({'record_id':str(item['id']), 'url':item['url'],
                'account':item.get('account'),'created_at':item.get('created_at'),
                'n_hits':len(hits),'first_hit':short_witness(hits[0],group,item['url'],item['id'],item.get('account'),item.get('created_at'))})
    # Original code concatenated all records inside each surface. This
    # companion value can contain a cross-record match in that surface.
    combined = '\n'.join(item['text'] for item in items)
    aggregate_matches = extract(combined,include_positions=True).get('D6',[]) if aggregate else []
    return {
        'record_count':len(items),'any_atomic':bool(present),'atomic_positive_records':len(present),
        'atomic_evidence':present[:12],
        'joined_detected':bool(aggregate_matches) if aggregate else None,
        'joined_match_count':len(aggregate_matches) if aggregate else None,
        'joined_first_match':({'rule_id':aggregate_matches[0].get('rule_id'),
            'cue':aggregate_matches[0].get('cue'), 'quant':aggregate_matches[0].get('quant'),
            'snippet':aggregate_matches[0].get('snippet','')[:260]} if aggregate_matches else None),
        'empty_count':sum(not v['text'].strip() for v in items),
    }


def item(text: str|None, rid, url: str, login: str|None=None, created: str|None=None):
    return {'text':str(text) if text is not None else '', 'id':rid,
            'url':url,'account':login,'created_at':created}


def workflow_run_names(head_sha: str, num: int, token: str|None) -> tuple[list[dict],dict]:
    """PR-head-SHA workflow names, as current GitHub CI metadata proxy.

    The pinned original snapshot's workflows are unavailable. Workflow names
    retrieved from current API are explicitly marked as contemporary proxies.
    """
    base=f'https://api.github.com/repos/{REPO}/actions/runs?head_sha={head_sha}&per_page=100'
    obj=json.loads(checked_fetch(base,token))
    if not isinstance(obj,dict) or not isinstance(obj.get('workflow_runs'),list):
        raise ValueError('Unexpected actions/runs response')
    total=int(obj.get('total_count',-1))
    if total<0 or total>1000:
        raise ValueError(f'Unexpected CI run count for PR {num}: {total}')
    runs=obj['workflow_runs'][:]
    for page in range(2,(total+99)//100+1):
        extra=json.loads(checked_fetch(base+f'&page={page}',token))
        runs+=extra['workflow_runs']
    if len(runs)!=total:
        raise ValueError(f'Incomplete workflow run collection for PR {num}: {len(runs)}/{total}')
    vals=[item(x.get('name'),x['id'],x.get('html_url') or f'https://github.com/{REPO}/actions/runs/{x["id"]}',
           (x.get('actor') or {}).get('login'),x.get('created_at')) for x in runs if x.get('name') is not None]
    return vals,{'head_sha':head_sha,'runs_api_count':len(runs),
        'unique_workflow_names':len({x['text'] for x in vals}),
        'historical_snapshot_equivalence':'unverified'}


def fetch_one(num:int,arm:str,extract,token:str|None):
    pr=get_pr(num,token)
    if pr.get('number')!=num:
        raise ValueError('PR identity mismatch')
    url=f'https://github.com/{REPO}/pull/{num}'
    issues=get_paginated(f'issues/{num}/comments',token)
    inline=get_paginated(f'pulls/{num}/comments',token)
    commits=get_paginated(f'pulls/{num}/commits',token)
    files=get_paginated(f'pulls/{num}/files',token)
    reviews=get_paginated(f'pulls/{num}/reviews',token)
    head_sha=pr.get('head',{}).get('sha')
    if not head_sha:
        raise ValueError('Missing current PR head SHA')
    workflows,ci_meta=workflow_run_names(head_sha,num,token)
    issue_items=[item(c.get('body'),c['id'],c.get('html_url') or url,
       (c.get('user') or {}).get('login'),c.get('created_at')) for c in issues]
    nonbot_items=[item(c.get('body'),c['id'],c.get('html_url') or url,
       (c.get('user') or {}).get('login'),c.get('created_at')) for c in issues if not bot_flag(c)]
    desc=[item('\n'.join(str(x) for x in (pr.get('title'),pr.get('body')) if x is not None),num,url,
         (pr.get('user') or {}).get('login'),pr.get('created_at'))]
    inline_items=[item(c.get('body'),c['id'],c.get('html_url') or url,
          (c.get('user') or {}).get('login'),c.get('created_at')) for c in inline]
    # Supplementary review summaries are separate from the source study's
    # review_comments surface.
    review_summaries=[item(c.get('body'),c['id'],c.get('html_url') or url,
           (c.get('user') or {}).get('login'),c.get('submitted_at')) for c in reviews if (c.get('body') or '').strip()]
    commit_items=[item(c.get('commit',{}).get('message'),c.get('sha') or '',
          c.get('html_url') or url,(c.get('author') or {}).get('login'),
          c.get('commit',{}).get('author',{}).get('date')) for c in commits]
    file_items=[item(c.get('patch'),c.get('filename') or '',c.get('blob_url') or url,
          None,None) for c in files if c.get('patch') is not None]
    missing_patch=[(c.get('filename') or '') for c in files if c.get('patch') is None]
    surfaces={
        'description':inspect_items(extract,desc,'description',True),
        'issue_comments_atomic':inspect_items(extract,issue_items,'issue_comments',False),
        'issue_comments_nonbot_atomic':inspect_items(extract,nonbot_items,'issue_comments',False),
        'review_comments':inspect_items(extract,inline_items,'review_comments',True),
        'commit_messages':inspect_items(extract,commit_items,'commit_messages',True),
        'ci_metadata':inspect_items(extract,workflows,'ci_metadata',True),
        'code_diff':inspect_items(extract,file_items,'code_diff',True),
        'review_body_supplement':inspect_items(extract,review_summaries,'review_body_supplement',True),
    }
    # Historical extractor concatenates bodies within each source channel,
    # except our counterfactual keeps issue comments atomic; other channels
    # retain their original source-level joining rule.
    independent_source_joined=any(surfaces[k]['joined_detected'] for k in PRIMARY)
    independent_source_atomic=any(surfaces[k]['any_atomic'] for k in PRIMARY)
    retained_joined=independent_source_joined or surfaces['issue_comments_atomic']['any_atomic']
    retained_atomic=independent_source_atomic or surfaces['issue_comments_atomic']['any_atomic']
    return {
       'pr_number':num,'sample_arm':arm,'published_D6':True,'pr_url':url,
       'pr_created_at':pr.get('created_at'),'pr_updated_at':pr.get('updated_at'),
       'head_sha_at_retrieval':head_sha,'head_sha_vs_historical':'unverified',
       'surfaces':surfaces,
       'retained_when_issue_boundaries_preserved':retained_joined,
       'retained_when_all_source_records_atomic':retained_atomic,
       'non_issue_source_joined':independent_source_joined,
       'non_issue_source_atomic':independent_source_atomic,
       'supplemental_review_body_detected':surfaces['review_body_supplement']['joined_detected'],
       'ci_provenance':ci_meta,
       'counts':{
          'issue_comments':len(issues), 'issue_comment_bot':sum(bot_flag(c) for c in issues),
          'inline_review_comments':len(inline), 'review_summaries':len(review_summaries),
          'commits':len(commits),'changed_files':len(files), 'patches_available':len(file_items),
          'patches_unavailable':len(missing_patch),'ci_workflow_runs':len(workflows),
          'created_issue_comments_after_cutoff':sum((c.get('created_at') or '')>CUTOFF for c in issues),
          'updated_issue_comments_after_cutoff':sum((c.get('updated_at') or '')>CUTOFF for c in issues),
       },
       'patch_unavailable_filenames':missing_patch[:30],
       'snapshot_limit':'current GitHub API evidence; historical original parquet snapshot absent',
    }


def make_summary(rows:list[dict]):
    assert len(rows)==65 and len({x['pr_number'] for x in rows})==65
    groups={'agentic':[x for x in rows if x['sample_arm']=='agentic'],
            'human_candidate':[x for x in rows if x['sample_arm']=='human_candidate']}
    def count(xs,key):return sum(bool(x[key]) for x in xs)
    summary={
      'schema':AUDIT_VERSION,'pinned_upstream_commit':PIN,'pinned_source_blob_sha1':BLOB_SHAS,
      'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'n_selected':65,'selected_arm_counts':{k:len(v) for k,v in groups.items()},
      'retention_count_joined_nonissue':count(rows,'retained_when_issue_boundaries_preserved'),
      'retention_count_all_atomic':count(rows,'retained_when_all_source_records_atomic'),
      'other_sources_joined_count':count(rows,'non_issue_source_joined'),
      'other_sources_atomic_count':count(rows,'non_issue_source_atomic'),
      'supplemental_review_body_count':count(rows,'supplemental_review_body_detected'),
      'channel_detection':{k:{
          'any_joined':sum(bool(x['surfaces'][k]['joined_detected']) for x in rows if x['surfaces'][k]['joined_detected'] is not None),
          'any_atomic':sum(x['surfaces'][k]['any_atomic'] for x in rows),
          'n_without_records':sum(x['surfaces'][k]['record_count']==0 for x in rows)
          } for k in (*PRIMARY,'issue_comments_atomic','issue_comments_nonbot_atomic','review_body_supplement')},
      'joined_by_arm':{k:count(v,'retained_when_issue_boundaries_preserved') for k,v in groups.items()},
      'atomic_by_arm':{k:count(v,'retained_when_all_source_records_atomic') for k,v in groups.items()},
      'retained_prs':sorted(x['pr_number'] for x in rows if x['retained_when_issue_boundaries_preserved']),
      'removed_prs':sorted(x['pr_number'] for x in rows if not x['retained_when_issue_boundaries_preserved']),
      'total_evidence_objects':{k:sum(x['counts'][k] for x in rows) for k in rows[0]['counts']},
      'patch_incomplete_prs':[x['pr_number'] for x in rows if x['counts']['patches_unavailable']],
      'historical_snapshot_available':False,
      'interpretation':{
        'primary':'Boundary-preserved issue-comment evidence with other currently retrievable source channels joined per upstream policy.',
        'secondary':'Each record examined separately across all retrieved channels.',
        'CI':'Workflow names linked to current PR head SHA; original historical snapshot run names remain unverified.',
        'diff':'GitHub public files API can omit patches for binaries or oversized changes.',
        'population':'Only 65 source-linked Rspack PRs; other 1,634 labels frozen in sensitivity follow-up.',
      },
    }
    return summary


def write_outputs(rows:list[dict],summary:dict,out:Path,csvout:Path):
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'summary':summary,'rows':rows},indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf8')
    fields=['pr_number','sample_arm','published_D6','retained_issue_comments_atomic_plus_joined_nonissue',
       'retained_all_records_atomic','description','review_comments','commit_messages','ci_metadata','code_diff',
       'review_body_supplement','issue_comments_atomic','issue_comments_nonbot_atomic','patches_unavailable','ci_workflow_runs',
       'pr_url']
    with csvout.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        for x in rows:
            s=x['surfaces']
            w.writerow({'pr_number':x['pr_number'],'sample_arm':x['sample_arm'],'published_D6':'True',
              'retained_issue_comments_atomic_plus_joined_nonissue':str(x['retained_when_issue_boundaries_preserved']),
              'retained_all_records_atomic':str(x['retained_when_all_source_records_atomic']),
              **{k:str(s[k]['joined_detected']) for k in PRIMARY},
              'review_body_supplement':str(s['review_body_supplement']['joined_detected']),
              'issue_comments_atomic':str(s['issue_comments_atomic']['any_atomic']),
              'issue_comments_nonbot_atomic':str(s['issue_comments_nonbot_atomic']['any_atomic']),
              'patches_unavailable':x['counts']['patches_unavailable'],
              'ci_workflow_runs':x['counts']['ci_workflow_runs'],'pr_url':x['pr_url']})
    print('OTHER_SOURCE_SUMMARY '+json.dumps(summary,sort_keys=True,ensure_ascii=False),flush=True)
    print('OTHER_SOURCE_OUTPUT '+json.dumps({'json':str(out),'csv':str(csvout)}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pairs',type=Path,default=PAIRS)
    p.add_argument('--out',type=Path,default=OUTPUT)
    p.add_argument('--csv-out',type=Path,default=CSV_OUTPUT)
    p.add_argument('--max-workers',type=int,default=5)
    p.add_argument('--max-prs',type=int,default=0,help='Smoke-test subset; zero for complete locked cohort')
    a=p.parse_args()
    ids=load_ids(a.pairs)
    if a.max_prs:ids=dict(list(ids.items())[:a.max_prs])
    extract=load_original_extractor()
    token=os.getenv('GITHUB_TOKEN')
    rows=[];errors=[]
    def task(x):
        n,arm=x
        for attempt in range(3):
            try:return fetch_one(n,arm,extract,token)
            except HTTPError as ex:
                if ex.code in (403,429,500,502,503,504) and attempt<2:
                    time.sleep(4*(attempt+1));continue
                raise
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.max_workers) as pool:
        futures={pool.submit(task,item):item[0] for item in ids.items()}
        for f in concurrent.futures.as_completed(futures):
            pr=futures[f]
            try:
                x=f.result();rows.append(x)
                print('OTHER_SOURCE_PR '+json.dumps({'pr':pr,'arm':x['sample_arm'],
                    'retained_joined':x['retained_when_issue_boundaries_preserved'],
                    'retained_atomic':x['retained_when_all_source_records_atomic'],
                    'source_joined':{k:x['surfaces'][k]['joined_detected'] for k in PRIMARY},
                    'unavailable_patches':x['counts']['patches_unavailable']},sort_keys=True),flush=True)
            except Exception as e:
                errors.append((pr,type(e).__name__,str(e)[:300]))
                print('OTHER_SOURCE_ERROR '+json.dumps({'pr':pr,'exception':type(e).__name__,
                    'message':str(e)[:200]}),flush=True)
    rows.sort(key=lambda x:x['pr_number'])
    if errors:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        (a.out.parent/'rspack65_other_source_errors.json').write_text(json.dumps(errors,indent=2)+'\n')
        raise RuntimeError(f'{len(errors)} PR evidence fetch failures; no complete-cohort claim: {errors[:3]}')
    if a.max_prs:
        print('SMOKE_TEST_ONLY '+json.dumps({'n':len(rows)}));return
    summary=make_summary(rows)
    write_outputs(rows,summary,a.out,a.csv_out)

if __name__=='__main__': main()
