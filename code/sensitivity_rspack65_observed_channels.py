#!/usr/bin/env python3
"""Update the 1,699-PR D6 sensitivity using actual public-channel replay.

The replay concerns current GitHub records, with issue comments kept separate.
Published labels remain frozen outside the 65 source-linked Rspack PRs.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sensitivity_rspack65 as sens

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'results/rspack65_other_source_replay.json'
OUT=ROOT/'results/rspack65_observed_channel_sensitivity.json'


def run(audit_path:Path,source:Path=ROOT/'data/rq3_labels.csv',
        pairs:Path=ROOT/'results/rspack_65_comment_pairs.csv',
        boundary:Path=ROOT/'results/rspack_97_comment_boundary_audit.csv'):
    data=json.loads(Path(audit_path).read_text(encoding='utf8'))
    summary=data['summary']; rows=data['rows']
    if summary['schema']!='claimscope/rspack65-other-sources/v1':raise ValueError('Wrong audit schema')
    if len(rows)!=65 or len({int(x['pr_number']) for x in rows})!=65:raise ValueError('Incomplete source audit')
    if len(rows)!=summary['n_selected']:raise ValueError('Audit count mismatch')
    original,selected=sens.load_inputs(source,pairs,boundary)
    if {(sens.RSPACK,str(x['pr_number'])) for x in rows}!=set(selected):raise ValueError('Audit PR cohort changed')
    for r in rows:
        key=(sens.RSPACK,str(r['pr_number']))
        if r['sample_arm']!=selected[key] or r['published_D6'] is not True:
            raise ValueError('Audit label/arm mismatch')
        surv=(any(bool(r['surfaces'][k]['joined_detected']) for k in ('description','review_comments','commit_messages','ci_metadata','code_diff')) or r['surfaces']['issue_comments_atomic']['any_atomic'])
        if bool(r['retained_when_issue_boundaries_preserved'])!=surv:
            raise ValueError('Source retention formula mismatch')
        atomic=(any(bool(r['surfaces'][k]['any_atomic']) for k in ('description','review_comments','commit_messages','ci_metadata','code_diff')) or r['surfaces']['issue_comments_atomic']['any_atomic'])
        if bool(r['retained_when_all_source_records_atomic'])!=atomic:
            raise ValueError('Atomic retention formula mismatch')
    supported={ (sens.RSPACK,str(x['pr_number'])):selected[(sens.RSPACK,str(x['pr_number']))]
               for x in rows if x['retained_when_issue_boundaries_preserved'] }
    unsupported={k:v for k,v in selected.items() if k not in supported}
    atomic_supported={(sens.RSPACK,str(x['pr_number'])):selected[(sens.RSPACK,str(x['pr_number']))]
               for x in rows if x['retained_when_all_source_records_atomic']}
    atomic_unsupported={k:v for k,v in selected.items() if k not in atomic_supported}
    recoded=sens.set_selected_off(original,unsupported)
    atomic_recoded=sens.set_selected_off(original,atomic_unsupported)
    all_off=sens.set_selected_off(original,selected)
    # no changes outside the locked evidence cohort
    for a,b in zip(original,recoded):
        if (a.repo,a.pr) not in selected and a!=b:raise ValueError('Non-selected PR altered')
    original_view=sens.by_arm(original)
    keep_joined_view=sens.by_arm(recoded)
    keep_atomic_view=sens.by_arm(atomic_recoded)
    all_off_view=sens.by_arm(all_off)
    by_arm=collections.Counter(selected.values())
    changed_by_arm=collections.Counter(unsupported.values())
    remaining_by_arm=collections.Counter(supported.values())
    answer={
      'schema':'claimscope/rspack65-observed-channel-sensitivity/v1',
      'origin':{'source_dataset_sha256':sens.SOURCE_SHA256,'upstream_pinned_commit':summary['pinned_upstream_commit'],
                'audit_file_sha256':hashlib.sha256(Path(audit_path).read_bytes()).hexdigest(),
                'analysis':'Current public source-specific extraction; historical source snapshot unavailable'},
      'sample':{'n_prs':1699,'source_linked_rspack_prs':65,'selected_by_arm':dict(by_arm)},
      'observed_other_source_retention':{
        'retained':len(supported),'not_retained':len(unsupported),
        'retained_by_arm':dict(remaining_by_arm),'not_retained_by_arm':dict(changed_by_arm),
        'atomic_retained':len(atomic_supported),'atomic_not_retained':len(atomic_unsupported),
        'retained_PR_ids':sorted(int(k[1]) for k in supported),
        'not_retained_PR_ids':sorted(int(k[1]) for k in unsupported),
        'by_channel':summary['channel_detection'],
        'snapshot_patch_limit':summary['patch_incomplete_prs'],
      },
      'contrasts':{
        'published_labels':original_view,
        '65_flags_off_local_scenario':all_off_view,
        'retain_current_public_source_matches':keep_joined_view,
        'retain_current_atomic_record_matches':keep_atomic_view,
      },
      'gap_change_from_published_pp':keep_joined_view['gap_pp']-original_view['gap_pp'],
      'gap_attenuation_fraction':(original_view['gap_pp']-keep_joined_view['gap_pp'])/original_view['gap_pp'],
      'retention_interpretation':{
        'observed':'Source-specific D6 detection on current public GitHub material; issue comments inspected individually',
        'uncertain':'Missing original snapshot and changed PR-head or patch coverage can alter historical extraction',
        'conditional':'Original D6 labels for the remaining 1,634 PRs are unchanged',
      },
    }
    return answer


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-audit',type=Path,default=AUDIT)
    p.add_argument('--output',type=Path,default=OUT)
    args=p.parse_args()
    res=run(args.source_audit)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(res,indent=2,sort_keys=True)+'\n',encoding='utf8')
    print(json.dumps({'retained':res['observed_other_source_retention']['retained'],
       'gap_pp':res['contrasts']['retain_current_public_source_matches']['gap_pp'],
       'atomic_retained':res['observed_other_source_retention']['atomic_retained']},sort_keys=True))

if __name__=='__main__':main()
