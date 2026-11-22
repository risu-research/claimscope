#!/usr/bin/env python3
"""Trace D6 cue/quantity pairs across public Rspack issue-comment boundaries.

Uses the pinned Peng et al. extractor verbatim. Output retains the source comment
identities and the matched cue/quantity spans, with source URLs for inspection.
"""
import argparse
from bisect import bisect_right
import csv
import datetime as dt
import json
import os
from pathlib import Path

from audit_rspack_11_exact import (
    PIN, BLOB_SHAS, DEFAULT_CSV, CUTOFF,
    bot_flag, get_paginated, load_original_extractor,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'
SEPARATOR = '\n' + ' '.join(['zzcommentboundary'] * 32) + '\n'


def join_bodies(comments, separator='\n'):
    return separator.join(str(c['body']) for c in comments if c.get('body') is not None)


def bodies_present(comments):
    return [c for c in comments if c.get('body') is not None]


def classify_comment(c):
    body = (c.get('body') or '').lower()
    if 'binary size-limit' in body:
        return 'binary_size_limit'
    if 'rsdoctor bundle diff analysis' in body:
        return 'rsdoctor_bundle_diff'
    if 'codspeed performance report' in body or '__codspeed_performance_report_comment__' in body:
        return 'codspeed'
    if 'benchmark' in body:
        return 'other_benchmark'
    return 'other'


def offsets_of_independently_normalized_comments(comments, normalize):
    """Return the normalized-concatenation offset of each source comment.

    Guard: accepting these offsets requires that normalization commutes with
    joining the particular raw texts. The caller verifies exact equality.
    """
    starts, ends = [], []
    length = 0
    for i, c in enumerate(comments):
        if i:
            length += 1  # one original newline separator
        starts.append(length)
        length += len(normalize(str(c['body'])))
        ends.append(length)
    return starts, ends


def owner_of_span(pos, stop, starts, ends):
    """Find the comment containing an entire half-open normalized-text span."""
    i = bisect_right(starts, pos) - 1
    if i < 0 or not (starts[i] <= pos < ends[i] and stop <= ends[i]):
        return None
    return i


def source(c, ordinal):
    actor = c.get('user') or {}
    return {
        'comment_id': c.get('id'),
        'comment_ordinal': ordinal,
        'url': c.get('html_url'),
        'account_login': actor.get('login'),
        'account_type': actor.get('type'),
        'is_bot': bool(bot_flag(c)),
        'kind': classify_comment(c),
        'created_at': c.get('created_at'),
        'updated_at': c.get('updated_at'),
    }


def trace_one(ref, comments, extract):
    """Locate original D6 cue/quantity match spans in exact comment identities."""
    mp = extract.__globals__['mp']
    present = bodies_present(comments)
    raw_join = join_bodies(present)
    normalized = mp.normalize(raw_join)
    normalized_individual_join = '\n'.join(mp.normalize(str(c['body'])) for c in present)
    mapping_exact = normalized == normalized_individual_join

    hits = extract(raw_join, include_positions=True).get('D6', [])
    separate = any('D6' in extract(str(c['body'])) for c in present)
    guarded = 'D6' in extract(join_bodies(present, SEPARATOR))
    is_positive = ref['published_D6'] == 'True'
    case_cross_only = bool(hits) and not separate and not guarded
    starts, ends = offsets_of_independently_normalized_comments(present, mp.normalize)
    pairs = []
    unlocated = []
    if mapping_exact:
        token_starts = extract.__globals__['_token_starts'](normalized)
        token_of = extract.__globals__['_tok']
        for k, m in enumerate(hits):
            a = owner_of_span(m['cue_start'], m['cue_end'], starts, ends)
            b = owner_of_span(m['quant_start'], m['quant_end'], starts, ends)
            if a is None or b is None:
                unlocated.append({'match_ordinal':k+1, 'rule_id':m.get('rule_id'), 'reason':'span_on_separator_or_unmapped'})
                continue
            if a == b:
                continue
            ca, cb = present[a], present[b]
            cue=source(ca,a+1); quant=source(cb,b+1)
            original_pair = str(ca['body'])+'\n'+str(cb['body']) if a<b else str(cb['body'])+'\n'+str(ca['body'])
            source_pair_activates = 'D6' in extract(original_pair)
            guarded_pair = str(ca['body'])+SEPARATOR+str(cb['body']) if a<b else str(cb['body'])+SEPARATOR+str(ca['body'])
            guarded_pair_activates = 'D6' in extract(guarded_pair)
            pairs.append({
                'pr_number':int(ref['pr_number']),
                'match_ordinal':k+1,
                'rule_id':m['rule_id'],
                'cue':m['cue'], 'quant':m['quant'], 'quant_kind':m['quant_kind'],
                'cue_start_norm':m['cue_start'], 'quant_start_norm':m['quant_start'],
                'cue_quant_token_delta': token_of(token_starts,m['quant_start'])-token_of(token_starts,m['cue_start']),
                'source_comment_gap':abs(a-b),
                'cue_source':cue, 'quant_source':quant,
                'pair_only_D6':source_pair_activates,
                'pair_with_separator_D6':guarded_pair_activates,
                'cue_source_D6_alone':'D6' in extract(str(ca['body'])),
                'quant_source_D6_alone':'D6' in extract(str(cb['body'])),
                'cue_text_norm':normalized[m['cue_start']:m['cue_end']],
                'quant_text_norm':normalized[m['quant_start']:m['quant_end']],
            })
    else:
        unlocated.append({'reason':'full_normalization_differs_from_independent_comments'})
    return {
      'pr_number':int(ref['pr_number']), 'sample_arm':ref['sample_arm'],
      'published_D6':is_positive, 'all_concat_D6':bool(hits),
      'any_individual_D6':separate, 'guarded_D6':guarded,
      'cross_comment_only':case_cross_only,
      'comment_count':len(present),
      'normalization_mapping_exact':mapping_exact,
      'original_D6_match_count':len(hits),
      'cross_comment_match_count':len(pairs),
      'pairs':pairs,
      'unlocated_hits':unlocated,
      'source_comment_updated_after_cutoff':sum((c.get('updated_at') or '')>CUTOFF for c in present),
    }


def flatten_pairs(records):
    rows=[]
    for r in records:
        for m in r['pairs']:
            c,q=m['cue_source'],m['quant_source']
            rows.append({
              'pr_number':m['pr_number'], 'sample_arm':r['sample_arm'],
              'published_D6':r['published_D6'], 'match_ordinal':m['match_ordinal'],
              'rule_id':m['rule_id'], 'cue':m['cue'], 'quant':m['quant'],
              'quant_kind':m['quant_kind'], 'cue_quant_token_delta':m['cue_quant_token_delta'],
              'source_comment_gap':m['source_comment_gap'],
              'cue_comment_id':c['comment_id'], 'cue_comment_url':c['url'],
              'cue_comment_account':c['account_login'], 'cue_comment_type':c['kind'],
              'cue_comment_created_at':c['created_at'], 'cue_comment_updated_at':c['updated_at'],
              'cue_is_bot':c['is_bot'],
              'quant_comment_id':q['comment_id'], 'quant_comment_url':q['url'],
              'quant_comment_account':q['account_login'], 'quant_comment_type':q['kind'],
              'quant_comment_created_at':q['created_at'], 'quant_comment_updated_at':q['updated_at'],
              'quant_is_bot':q['is_bot'],
              'pair_only_D6':m['pair_only_D6'],
              'pair_with_separator_D6':m['pair_with_separator_D6'],
              'cue_D6_alone':m['cue_source_D6_alone'],
              'quant_D6_alone':m['quant_source_D6_alone'],
            })
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args()
    with DEFAULT_CSV.open(newline='',encoding='utf-8') as f:
        refs=list(csv.DictReader(f))
    if len(refs)!=97 or len({r['pr_number'] for r in refs})!=97:
        raise ValueError('Expected exactly 97 unique pinned Rspack PR identities')
    if sum(r['published_D6']=='True' for r in refs)!=83:
        raise ValueError('Unexpected published D6 distribution')
    extract=load_original_extractor()
    records=[]
    for i,ref in enumerate(refs,1):
        comments=get_paginated(f'issues/{ref["pr_number"]}/comments',os.environ.get('GITHUB_TOKEN'))
        row=trace_one(ref,comments,extract)
        records.append(row)
        print('TRACE_PR '+json.dumps({k:row[k] for k in ('pr_number','published_D6','cross_comment_only','normalization_mapping_exact','cross_comment_match_count','original_D6_match_count')},sort_keys=True),flush=True)
    boundary_only=[r for r in records if r['cross_comment_only']]
    mapping_fail=[r['pr_number'] for r in boundary_only if not r['normalization_mapping_exact']]
    empty_pairs=[r['pr_number'] for r in boundary_only if not r['pairs']]
    matched=sum(r['all_concat_D6']==r['published_D6'] for r in records)
    original_check={'full_cohort':len(records),'published_D6_matches':matched,'cross_comment_only':len(boundary_only),
       'all_exact_normalization':sum(r['normalization_mapping_exact'] for r in boundary_only),
       'boundary_cases_without_cross_pairs':empty_pairs,
       'boundary_cases_without_exact_mapping':mapping_fail,
    }
    if matched!=97 or len(boundary_only)!=65:
        raise ValueError(f'Previous audit baseline changed: {original_check}')
    flat=flatten_pairs(boundary_only)
    source_types={}
    account_pairs={}
    cue_quant_order={'quant_before_cue':0,'cue_before_quant':0}
    for p in flat:
        typ=p['quant_comment_type']+' -> '+p['cue_comment_type']
        source_types[typ]=source_types.get(typ,0)+1
        pair=p['quant_comment_account']+' -> '+p['cue_comment_account']
        account_pairs[pair]=account_pairs.get(pair,0)+1
        if p['quant_comment_created_at']<=p['cue_comment_created_at']:
            cue_quant_order['quant_before_cue']+=1
        else:cue_quant_order['cue_before_quant']+=1
    summary={
      'source': 'Original Peng et al. extract_dimensions and metric_patterns at pinned commit',
      'pinned_upstream_commit':PIN,'pinned_original_blob_shas':BLOB_SHAS,
      'retrieved_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'cohort_size':97,'published_D6_yes':83,'published_D6_no':14,
      'exact_full_cohort_replay':matched,'cross_comment_only_PRs':len(boundary_only),
      'cross_comment_pair_matches':len(flat),'unique_cue_quant_comment_id_pairs':len(set((p['pr_number'],p['cue_comment_id'],p['quant_comment_id']) for p in flat)),
      'normalization_exact_mapping_PRs':original_check['all_exact_normalization'],
      'mapping_anomalies':mapping_fail,'boundary_cases_without_cross_pair':empty_pairs,
      'pair_only_D6_count':sum(p['pair_only_D6'] for p in flat),
      'pair_with_separator_D6_count':sum(p['pair_with_separator_D6'] for p in flat),
      'both_comments_bot_count':sum(p['cue_is_bot'] and p['quant_is_bot'] for p in flat),
      'source_type_pairs':dict(sorted(source_types.items())),
      'actor_account_pairs':dict(sorted(account_pairs.items())),
      'cue_quant_order':cue_quant_order,
      'cohort_cross_only_by_arm':{
        arm:sum(r['cross_comment_only'] and r['sample_arm']==arm for r in records)
        for arm in ('agentic','human_candidate')},
      'limits':[
       'Current public GitHub comments; original historical evidence snapshot unavailable.',
       'This trace tests the original issue-comment concatenation surface only.',
       'A cross-comment match is a property of input processing, separate from the truth of the recorded measurement.',
      ],
    }
    args.out.mkdir(parents=True,exist_ok=True)
    paths={
      'summary':args.out/'rspack_65_comment_pair_summary.json',
      'pairs':args.out/'rspack_65_comment_pairs.csv',
      'full':args.out/'rspack_65_comment_pair_audit.json',
    }
    paths['summary'].write_text(json.dumps(summary,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    paths['full'].write_text(json.dumps({'summary':summary,'rows':boundary_only},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    fields=['pr_number','sample_arm','published_D6','match_ordinal','rule_id','cue','quant','quant_kind','cue_quant_token_delta','source_comment_gap','cue_comment_id','cue_comment_url','cue_comment_account','cue_comment_type','cue_comment_created_at','cue_comment_updated_at','cue_is_bot','quant_comment_id','quant_comment_url','quant_comment_account','quant_comment_type','quant_comment_created_at','quant_comment_updated_at','quant_is_bot','pair_only_D6','pair_with_separator_D6','cue_D6_alone','quant_D6_alone']
    with paths['pairs'].open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat)
    print('PAIR_SUMMARY '+json.dumps(summary,ensure_ascii=False,sort_keys=True),flush=True)
    print('PAIR_OUTPUT '+json.dumps({k:str(p) for k,p in paths.items()}),flush=True)
    if mapping_fail or empty_pairs:
        raise RuntimeError('Some boundary cases lack exact located original-match evidence; inspect audit output')


if __name__=='__main__':
    main()
