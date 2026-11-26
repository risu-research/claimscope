#!/usr/bin/env python3
"""Prospectively specified finite-population estimates; requires one row per fixed selection.
Usage: python estimate.py outcomes.csv  # columns repo_id,number,status=positive|no_report|unknown
"""
import csv, math, json, sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent

def prob(N,K,n,x,upper):
    lo=max(0,n-(N-K));hi=min(n,K)
    if upper:lo=max(lo,x)
    else:hi=min(hi,x)
    return sum(math.comb(K,i)*math.comb(N-K,n-i) for i in range(lo,hi+1))/math.comb(N,n)
def interval(N,n,k,u,alpha=.05/8):
    assert 0<=k<=k+u<=n<=N
    if N==n:return k,k+u
    lo,hi=0,N
    while lo<hi:
        m=(lo+hi)//2
        if prob(N,m,n,k,True)>=alpha:hi=m
        else:lo=m+1
    L=lo;lo,hi=0,N
    while lo<hi:
        m=(lo+hi+1)//2
        if prob(N,m,n,k+u,False)>=alpha:lo=m
        else:hi=m-1
    return L,lo

def estimate(outcomes):
    selected=list(csv.DictReader((ROOT/'frozen_sample.csv').open()))
    expected={(r['repo_id'],r['number']) for r in selected}
    assert len(outcomes)==len(expected) and set(outcomes)==expected, 'missing or extraneous outcomes; no substitution'
    cells=defaultdict(list)
    for r in selected:cells[(r['arm'],r['stratum'])].append((int(r['inclusion_denominator']),outcomes[r['repo_id'],r['number']]))
    result=[]
    for (arm,st),v in sorted(cells.items()):
        N=v[0][0];n=len(v);k=sum(x[1]=='positive' for x in v);u=sum(x[1]=='unknown' for x in v)
        assert all(x[0]==N and x[1] in ('positive','no_report','unknown') for x in v)
        L,U=interval(N,n,k,u)
        result.append(dict(arm=arm,stratum=st,N=N,n=n,k=k,u=u,weighted_lower=N*k/n,weighted_upper=N*(k+u)/n,simultaneous_lower_K=L,simultaneous_upper_K=U))
    arms={}
    for a,den in [('agentic',858),('human_candidate',841)]:
        r=[x for x in result if x['arm']==a];N=sum(x['N'] for x in r)
        t={key:sum(x[key] for x in r) for key in ('weighted_lower','weighted_upper','simultaneous_lower_K','simultaneous_upper_K')}
        arms[a]={'negative_N':N,'original_metric_N':den,**t,'negative_rate_range':[t['weighted_lower']/N,t['weighted_upper']/N],'simultaneous_rate_range':[t['simultaneous_lower_K']/N,t['simultaneous_upper_K']/N]}
    A,H=arms['agentic'],arms['human_candidate']; gap=[100*(A['simultaneous_lower_K']/858-H['simultaneous_upper_K']/841),100*(A['simultaneous_upper_K']/858-H['simultaneous_lower_K']/841)]
    return {'cells':result,'arms':arms,'simultaneous_missed_report_contribution_gap_pp':gap,'warning':'Current-source observable report endpoint; not corrected overall reporting rates.'}
if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='--test':
        assert interval(10,10,3,2)==(3,5)
        assert interval(10,5,0,0)[0]==0
        assert interval(10,5,5,0)[1]==10
        assert interval(10,5,0,5)==(0,10)
        for N in range(2,14):
            for n in range(1,N+1):
                for k in range(n+1):
                    for u in range(n-k+1):
                        L,U=interval(N,n,k,u)
                        assert 0<=L<=U<=N
                        assert L==min(K for K in range(N+1) if prob(N,K,n,k,True)>=.05/8)
                        assert U==max(K for K in range(N+1) if prob(N,K,n,k+u,False)>=.05/8)
        print('exact inversion tests passed')
    else:
        r=list(csv.DictReader(open(sys.argv[1]))); d={(x['repo_id'],x['number']):x['status'] for x in r};assert len(r)==len(d)
        print(json.dumps(estimate(d),indent=2))
