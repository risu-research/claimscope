#!/usr/bin/env python3
"""Check whether the rspack D6 contrast is sensitive to the validation-presence inclusion rule.
Input: published analysis/classification_labels/rq3_labels.csv, unchanged.
Python standard library only. Executes no GitHub queries or LLM calls.
"""
import csv
import sys
from pathlib import Path

RID = '476642602'
GROUPS = ('agentic','human_candidate')

def gap(rows):
    output={}
    for a in GROUPS:
        r=[x for x in rows if x['sample_arm']==a]
        output[a]=(sum(x['D6'].lower()=='true' for x in r),len(r))
    return 100*(output['agentic'][0]/output['agentic'][1]-output['human_candidate'][0]/output['human_candidate'][1]),output

def audit(rows,selector):
    d=[r for r in rows if selector(r)]
    pooled,counts=gap(d)
    rest,rcounts=gap([r for r in d if r['repo_id']!=RID])
    print(f'{len(d):,} PRs; pooled gap={pooled:.6f} pp; without rspack={rest:.6f} pp; reduction={(pooled-rest)/pooled*100:.6f}%')
    print('  by group:',counts,'without rspack:',rcounts)
    return round(pooled,3),round(rest,3),round(100*(pooled-rest)/pooled,1)

if __name__=='__main__':
    path=Path(sys.argv[1] if len(sys.argv)>1 else 'rq3_labels.csv')
    with path.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    assert len(rows)==2081
    print('Published validation-positive metric-layer sample:')
    assert audit(rows,lambda r:r['in_metric_layer']=='True')==(8.885,1.339,84.9)
    print('All published joint-analysis records:')
    assert audit(rows,lambda r:True)==(7.387,1.157,84.3)
    print('PASS')
