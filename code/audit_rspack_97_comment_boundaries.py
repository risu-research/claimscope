#!/usr/bin/env python3
"""Audit D6 cross-comment matches using Peng's exact pinned extraction function.

Input: 97 fixed Rspack PR identities and their published D6 labels.
Surfaces: current public GitHub issue-thread comments in API order.
"""
import csv
import datetime as dt
import json
import os
from pathlib import Path
import re
from audit_rspack_11_exact import get_paginated, load_original_extractor, bot_flag, PIN, DEFAULT_CSV

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rspack_97_comment_boundary_audit.json'
CSV_OUT=ROOT/'results/rspack_97_comment_boundary_audit.csv'
DELIMITER='\n'+' '.join(['zzcommentboundary']*32)+'\n'


def text_join(items,delimiter='\n'):
    return delimiter.join(str(x.get('body')) for x in items if x.get('body') is not None)


def d6(extract,text):
    return 'D6' in extract(text)


def matches(extract,text):
    return extract(text,include_positions=True).get('D6',[])


def stats_for(comments,extract):
    full=text_join(comments)
    padded=text_join(comments,DELIMITER)
    per=[(c,matches(extract,c.get('body') or '')) for c in comments]
    combined_matches=matches(extract,full)
    return {
        'comments':len(comments),'concatenated_D6':bool(combined_matches),
        'padded_D6':d6(extract,padded),
        'any_individual_D6':any(bool(m) for _,m in per),
        'n_individual_D6_comments':sum(bool(m) for _,m in per),
        'n_concatenated_matches':len(combined_matches),
        'match_examples':[{'rule_id':m.get('rule_id'),'cue':m.get('cue'),'quant':m.get('quant'),'snippet':m.get('snippet','')[:200]} for m in combined_matches[:3]],
        'individual_D6_sources':[{'comment_id':c.get('id'),'url':c.get('html_url'),'login':(c.get('user') or {}).get('login'), 'n_matches':len(m)} for c,m in per if m][:10],
    }


def main():
    with DEFAULT_CSV.open(newline='',encoding='utf-8') as f:
        cohort=list(csv.DictReader(f))
    if len(cohort)!=97 or sum(r['published_D6']=='True' for r in cohort)!=83:
        raise ValueError('Unexpected upstream-label cohort size or D6 distribution')
    if len({r['pr_number'] for r in cohort})!=97:
        raise ValueError('Repeated PR identity')
    extract=load_original_extractor()
    token=os.environ.get('GITHUB_TOKEN')
    records=[]
    for i,ref in enumerate(cohort,1):
        pr=int(ref['pr_number'])
        comments=get_paginated(f'issues/{pr}/comments',token)
        bots=[x for x in comments if bot_flag(x)]
        humans=[x for x in comments if not bot_flag(x)]
        full=stats_for(comments,extract)
        bot=stats_for(bots,extract)
        human=stats_for(humans,extract)
        row={
           'pr_number':pr,
           'sample_arm':ref['sample_arm'],
           'published_D6':ref['published_D6']=='True',
           'n_issue_comments':len(comments),
           'bot_comment_count':len(bots),
           'human_comment_count':len(humans),
           'n_binary_size_bot_comments':sum('binary size-limit' in (x.get('body') or '').lower() for x in bots),
           'n_rsdoctor_bot_comments':sum('rsdoctor bundle diff analysis' in (x.get('body') or '').lower() for x in bots),
           'all_comments':full,
           'bot_comments':bot,
           'human_comments':human,
           'comment_changed_after_reference':sum((x.get('updated_at') or '')>'2026-08-27T23:59:59Z' for x in comments),
        }
        records.append(row)
        print('BOUNDARY_JSON '+json.dumps({'pr':pr,'label':row['published_D6'],
                'all_concat':full['concatenated_D6'],'bot_concat':bot['concatenated_D6'],
                'any_individual':full['any_individual_D6'],'all_padded':full['padded_D6'],
                'bot_padded':bot['padded_D6'],'n_bot':len(bots),
                'n_bot_binary':row['n_binary_size_bot_comments'],
                'examples':full['match_examples'][:1]},ensure_ascii=False),flush=True)
    yes=[x for x in records if x['published_D6']]
    no=[x for x in records if not x['published_D6']]
    def count(a,path):
        keys=path.split('.')
        return sum(bool(__import__('functools').reduce(lambda cur,key:cur[key],keys,x)) for x in a)
    counts={
       'published_yes':len(yes), 'published_no':len(no),
       'all_concat_yes':count(yes,'all_comments.concatenated_D6'),
       'all_concat_no':count(no,'all_comments.concatenated_D6'),
       'bot_concat_yes':count(yes,'bot_comments.concatenated_D6'),
       'bot_concat_no':count(no,'bot_comments.concatenated_D6'),
       'all_individual_yes':count(yes,'all_comments.any_individual_D6'),
       'all_individual_no':count(no,'all_comments.any_individual_D6'),
       'bot_individual_yes':count(yes,'bot_comments.any_individual_D6'),
       'bot_individual_no':count(no,'bot_comments.any_individual_D6'),
       'all_padded_yes':count(yes,'all_comments.padded_D6'),
       'all_padded_no':count(no,'all_comments.padded_D6'),
       'bot_padded_yes':count(yes,'bot_comments.padded_D6'),
       'bot_padded_no':count(no,'bot_comments.padded_D6'),
       'cross_comment_only_yes':sum(x['all_comments']['concatenated_D6'] and not x['all_comments']['any_individual_D6'] and not x['all_comments']['padded_D6'] for x in yes),
       'cross_comment_only_no':sum(x['all_comments']['concatenated_D6'] and not x['all_comments']['any_individual_D6'] and not x['all_comments']['padded_D6'] for x in no),
       'all_comments':sum(x['n_issue_comments'] for x in records),
       'bot_comments':sum(x['bot_comment_count'] for x in records),
       'human_comments':sum(x['human_comment_count'] for x in records),
       'comments_edited_after_cutoff':sum(x['comment_changed_after_reference'] for x in records)
    }
    summary={
       'method':'Exact pinned original extractor on current public Rspack issue comments, with separate versus concatenated comment comparisons.',
       'pinned_upstream_commit':PIN,
       'retrieval_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
       'n':len(records),
       'counts':counts,
       'limits':['The original source extractor joined issue-comment bodies with newline characters.',
                 'GitHub comment content and order reflect current public API state.',
                 'This audit isolates issue comments. Other original sources remain outside this boundary test.',
                 'Separator insertion is a controlled diagnostic input transformation.'],
       'rows':records,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    flat_fields=['pr_number','sample_arm','published_D6','n_issue_comments','bot_comment_count','human_comment_count','n_binary_size_bot_comments','n_rsdoctor_bot_comments','all_concat_D6','all_individual_D6','all_padded_D6','bot_concat_D6','bot_individual_D6','bot_padded_D6']
    with CSV_OUT.open('w',encoding='utf-8',newline='') as f:
       w=csv.DictWriter(f,fieldnames=flat_fields);w.writeheader()
       for r in records:
          w.writerow({**{k:r[k] for k in flat_fields[:8]},
              'all_concat_D6':r['all_comments']['concatenated_D6'],
              'all_individual_D6':r['all_comments']['any_individual_D6'],
              'all_padded_D6':r['all_comments']['padded_D6'],
              'bot_concat_D6':r['bot_comments']['concatenated_D6'],
              'bot_individual_D6':r['bot_comments']['any_individual_D6'],
              'bot_padded_D6':r['bot_comments']['padded_D6']})
    print('BOUNDARY_SUMMARY '+json.dumps(counts,sort_keys=True),flush=True)
    print('WROTE '+str(OUT)+' '+str(CSV_OUT),flush=True)

if __name__=='__main__': main()
