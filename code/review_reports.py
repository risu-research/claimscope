#!/usr/bin/env python3
"""Prepare source-linked review packets and compare separately recorded decisions."""
import argparse, collections, csv, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
LABELS={'positive','no_observed_report','unknown'}

def read_csv(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(body):return hashlib.sha256(body.encode('utf-8')).hexdigest()
def key(r):return r['repo'],str(r['number'])
def inventory():return json.loads((ROOT/'evidence/thread_inventory.json').read_text())
def prepare(out, sources=()):
    """Source is an optional independently acquired inventory-shaped corpus."""
    out=out.resolve()
    if out==ROOT or ROOT in out.parents and out.relative_to(ROOT).parts[0] not in ('build',):raise ValueError('Choose build/ or an external output directory')
    out.mkdir(parents=True,exist_ok=True)
    if (out/'decisions.csv').exists():raise ValueError('Use a new review directory to preserve prior decisions')
    retained=json.loads((ROOT/'evidence/replay_threads.json').read_text())
    archived={(key(r),c['comment_id']):c for r in retained for c in r['comments']}
    provided={}
    for source in sources:
        data=json.loads(source.read_text(encoding='utf-8'))
        for r in (data if isinstance(data,list) else [data]):
            for c in r['comments']:
                k=key(r),str(c['comment_id'])
                if k in provided:raise ValueError(f'Duplicate source identity: {k}')
                provided[k]=c
    expected={(key(r),c['comment_id']):c for r in inventory() for c in r['comments']}
    if set(provided)-set(expected):raise ValueError('Unexpected source identities')
    counts=collections.Counter(); packets=[]
    for r in inventory():
        cs=[]
        for c in r['comments']:
            k=key(r),c['comment_id']; record={x:c[x] for x in ['comment_id','url','created','updated','eligible','sha256']}
            item=provided.get(k) or archived.get(k)
            if not c['eligible']:status='outside_cutoff'
            elif item is None or not isinstance(item.get('body'),str):status='source_required'
            elif digest(item['body'])==c['sha256']:status='verified';record['body']=item['body']
            elif k not in provided and item.get('replay_sha256')==digest(item['body']):status='redacted_replay';record['body']=item['body']
            else:status='digest_mismatch'
            record['source_status']=status;counts[status]+=1;cs.append(record)
        packets.append({'repo':r['repo'],'number':r['number'],'collection_complete':r['collection_complete'],'comments':cs})
    dump(out/'review_sources.json',packets)
    (out/'decisions.csv').write_bytes((ROOT/'evidence/review_template.csv').read_bytes())
    dump(out/'coverage.json',dict(threads=len(packets),comment_status=dict(counts)))
    return counts

def compare(decisions,out):
    expected={key(r):r for r in inventory()}; rows=read_csv(decisions); got={key(r):r for r in rows}
    if len(got)!=len(rows) or set(got)!=set(expected):raise ValueError('Decision sheet must retain each of the 823 identities once')
    original={(r['repo_id'],r['number']):r for r in read_csv(ROOT/'data/audited_prs.csv')}
    pairs=collections.Counter(); disagreements=[]; completed=0
    for k,r in got.items():
        b,w=r['broad'],r['whole_artifact']
        if b==w=='':continue
        if b not in LABELS or w not in LABELS or (w=='positive' and b!='positive'):raise ValueError(f'Invalid nested decisions: {k}')
        inv=expected[k]; ids={c['comment_id'] for c in inv['comments'] if c['eligible']}
        witnesses=set(filter(None,re.split(r'[;,\s]+',r['supporting_comment_ids'].strip())))
        if witnesses-ids or ('positive' in (b,w) and not witnesses):raise ValueError(f'Positive decisions require eligible supporting IDs: {k}')
        if not inv['collection_complete'] and 'no_observed_report' in (b,w):raise ValueError(f'Incomplete original collection requires a qualifying report or unknown: {k}')
        ref=original[(inv['repo_id'],inv['number'])];completed+=1
        for e,new in [('broad',b),('whole_artifact',w)]:
            old=ref[e];pairs[e,old,new]+=1
            if old!=new:disagreements.append(dict(repo=k[0],number=k[1],definition=e,recorded=old,reviewed=new))
    report={'completed_prs':completed,'unreviewed_prs':823-completed,'comparison_counts':[dict(definition=e,recorded=o,reviewed=n,count=v) for (e,o,n),v in sorted(pairs.items())],'disagreements':disagreements}
    out=out.resolve()
    if out==ROOT or ROOT in out.parents and out.relative_to(ROOT).parts[0] not in ('build',):raise ValueError('Choose build/ or an external output file')
    out.parent.mkdir(parents=True,exist_ok=True)
    dump(out,report);return report

def main():
    p=argparse.ArgumentParser(description=__doc__);sp=p.add_subparsers(dest='command',required=True);a=sp.add_parser('prepare');a.add_argument('--output',type=Path,required=True);a.add_argument('--source',type=Path,action='append',default=[]);b=sp.add_parser('compare');b.add_argument('decisions',type=Path);b.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.command=='prepare':print(dict(prepare(args.output,args.source)))
    else:print(json.dumps(compare(args.decisions,args.output),indent=2))
if __name__=='__main__':main()
