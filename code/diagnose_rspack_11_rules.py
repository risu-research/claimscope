#!/usr/bin/env python3
"""Evaluate original D6 rule behavior under controlled public-comment edits."""
import datetime as dt
import json
import os
from pathlib import Path
import re

from audit_rspack_11_exact import get_paginated, load_original_extractor

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rspack_11_rule_diagnostics.json'
NEGATIVE=[11179,11320,12058,13714,13842,13854,13935,13968,13973,13975,14101]
POSITIVE_CONTROLS=[12560,13010]


def probe(text, extract):
    mp=extract.__globals__['mp']
    old=mp.WINDOW_TOKENS
    observed={}
    try:
        for window in (12,16,20,24,32,48,80):
            mp.WINDOW_TOKENS=window
            observed[str(window)]=('D6' in extract(text))
    finally:
        mp.WINDOW_TOKENS=old
    return observed


def find_cues_quant(text,extract):
    mp=extract.__globals__['mp']
    norm=mp.normalize(text)
    token_starts=extract.__globals__['_token_starts'](norm)
    tt=extract.__globals__['_tok']
    cues=[{'cue':m.group(0),'token':tt(token_starts,m.start()),'char':m.start()} for m in mp.CUE_PATTERNS['D6'].finditer(norm)]
    quants=[{'kind':kind,'match':m.group(0),'token':tt(token_starts,m.start()),'char':m.start()} for kind,pat in mp.QUANT_PATTERNS if kind in mp.QUANT_KINDS['D6'] for m in pat.finditer(norm)]
    exc=[{'match':m.group(0),'token':tt(token_starts,m.start())} for m in mp.EXCLUSION_RE.finditer(norm)]
    distances=sorted([{'cue':c['cue'],'quant':q['match'],'kind':q['kind'],'gap_tokens':abs(c['token']-q['token']),'direction':'after' if q['token']>=c['token'] else 'before'} for c in cues for q in quants],key=lambda x:x['gap_tokens'])
    return {'normalized_excerpt':norm[:950], 'cue_positions':cues[:7],'quant_positions':quants[:15], 'nearest_quant_pairs':distances[:6],'exclusion_positions':exc[:12]}


def main():
    extract=load_original_extractor()
    token=os.environ.get('GITHUB_TOKEN')
    rows=[]
    for n in NEGATIVE+POSITIVE_CONTROLS:
        comments=get_paginated(f'issues/{n}/comments', token)
        binary=[c for c in comments if 'binary size-limit' in (c.get('body') or '').lower() and (c.get('user') or {}).get('type')=='Bot']
        if len(binary)!=1:
            raise ValueError(f'Expected one binary size comment on {n}; got {len(binary)}')
        c=binary[0]
        body=c['body']
        removed_compare=re.sub(r'(?m)^>\s*Comparing[^\n]*\n?', '', body)
        measurement_lines=[ln for ln in body.splitlines() if re.search(r'\bSize\s+(?:decreased|increased|remains|changed)\b',ln,re.I)]
        short='## Binary Size-limit\n'+'\n'.join(measurement_lines)
        changes={
            'original':probe(body,extract),
            'comparison_line_removed':probe(removed_compare,extract),
            'minimal_header_and_measurement':probe(short,extract),
        }
        row={
            'pr_number':n,
            'published_D6': n in POSITIVE_CONTROLS,
            'comment_url':c.get('html_url'),
            'comment_id':c.get('id'),
            'comment_created_at':c.get('created_at'),
            'comment_updated_at':c.get('updated_at'),
            'comparison_line_removed_chars':len(body)-len(removed_compare),
            'size_measurement_lines':measurement_lines,
            'measurements':'\n'.join(measurement_lines),
            'matches_by_window_and_edit':changes,
            'original_match_detail': find_cues_quant(body,extract),
        }
        rows.append(row)
        print('DIAG_JSON '+json.dumps({'pr':n,'label':row['published_D6'],
              'original_window12':changes['original']['12'],
              'first_window_true':next((w for w,b in changes['original'].items() if b),None),
              'remove_compare':changes['comparison_line_removed']['12'],
              'minimal':changes['minimal_header_and_measurement']['12'],
              'nearest_gap':row['original_match_detail']['nearest_quant_pairs'][:2],
              'exclusions':row['original_match_detail']['exclusion_positions'][:3],
              'measurement':measurement_lines[:1]},ensure_ascii=False),flush=True)
    neg=[x for x in rows if not x['published_D6']]
    summary={
        'pinned_upstream_commit':'64432e0b6ed7791bbfa929c6c183fc76c75b5d58',
        'retrieval_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'n_negative':len(neg),
        'negative_original_positive_at_12':sum(x['matches_by_window_and_edit']['original']['12'] for x in neg),
        'negative_comparison_removed_positive_at_12':sum(x['matches_by_window_and_edit']['comparison_line_removed']['12'] for x in neg),
        'negative_minimal_positive_at_12':sum(x['matches_by_window_and_edit']['minimal_header_and_measurement']['12'] for x in neg),
        'negative_original_positive_at_48':sum(x['matches_by_window_and_edit']['original']['48'] for x in neg),
        'negative_original_positive_at_80':sum(x['matches_by_window_and_edit']['original']['80'] for x in neg),
        'n_positive_controls':len(POSITIVE_CONTROLS),
        'positive_controls_original_positive_at_12':sum(x['matches_by_window_and_edit']['original']['12'] for x in rows if x['published_D6']),
        'limitations':['Current public bot-comment text, not an archived original evidence snapshot',
                       'Edits are controlled input transformations and are diagnostic, not observed PR events',
                       'Increasing WINDOW_TOKENS also changes other window-based rule behavior'],
        'rows':rows,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('DIAG_SUMMARY '+json.dumps({k:v for k,v in summary.items() if k not in ['rows','limitations']},ensure_ascii=False),flush=True)

if __name__=='__main__': main()
