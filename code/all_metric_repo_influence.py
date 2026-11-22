#!/usr/bin/env python3
"""Complete repository-by-metric leave-one-out audit of published PR-level Boolean flags.

Replicates published extraction labels, not historical source-text matches.
Requires only Python 3 standard library. Run from this folder:
    python all_metric_repo_influence.py --csv rq3_labels.csv --output all_metric_repo_influence.csv
"""
import argparse, collections, csv
from pathlib import Path
from stage8_audit import load


def export(rows, outpath):
    arms = ('agentic', 'human_candidate')
    dims = [f'D{i}' for i in range(10)]
    groups = {arm: [r for r in rows if r['sample_arm'] == arm] for arm in arms}
    allcounts = {arm: (len(groups[arm]), {d: sum(r[d] == 'True' for r in groups[arm]) for d in dims}) for arm in arms}
    repos = collections.defaultdict(lambda: {arm: [0, collections.Counter()] for arm in arms})
    for r in rows:
        entry = repos[r['repo_id']][r['sample_arm']]
        entry[0] += 1
        entry[1].update(d for d in dims if r[d] == 'True')
    records=[]
    for d in dims:
        baseline=100*(allcounts['agentic'][1][d]/allcounts['agentic'][0]-allcounts['human_candidate'][1][d]/allcounts['human_candidate'][0])
        for repo in sorted(repos):
            ra,rh=repos[repo]['agentic'],repos[repo]['human_candidate']
            na,nh=allcounts['agentic'][0]-ra[0],allcounts['human_candidate'][0]-rh[0]
            if not na or not nh:
                raise ValueError(f'Empty group after repository removal: {repo}')
            ya,yh=allcounts['agentic'][1][d]-ra[1][d],allcounts['human_candidate'][1][d]-rh[1][d]
            drop=100*(ya/na-yh/nh)
            records.append({'dimension':d,'repo_id':repo,'n_agentic_repo':ra[0],
                'n_human_candidate_repo':rh[0],'n_agentic_positive_repo':ra[1][d],
                'n_human_candidate_positive_repo':rh[1][d],
                'overall_gap_pp':f'{baseline:.10f}','gap_excluding_repo_pp':f'{drop:.10f}',
                'repository_influence_pp':f'{(baseline-drop):.10f}'})
    header=['dimension','repo_id','n_agentic_repo','n_human_candidate_repo',
        'n_agentic_positive_repo','n_human_candidate_positive_repo',
        'overall_gap_pp','gap_excluding_repo_pp','repository_influence_pp']
    with open(outpath,'w',newline='') as handle:
        w=csv.DictWriter(handle,fieldnames=header);w.writeheader();w.writerows(records)
    if len(records)!=4400:
        raise ValueError(f'Expected 4400 rows (440 repositories x 10 metrics): {len(records)}')
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--csv',default='rq3_labels.csv');p.add_argument('--output',default='all_metric_repo_influence.csv');a=p.parse_args()
    records=export(load(a.csv),a.output)
    print(f'PASS: {len(records)} metric x repository records written to {a.output}')
