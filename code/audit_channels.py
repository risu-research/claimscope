#!/usr/bin/env python3
"""Verify the frozen source-channel inventory and its coverage exceptions."""
import csv,collections,json,sys,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def read(name):
    with (ROOT/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def run(out):
    summaries=read('evidence/channel_summary.csv'); records=read('evidence/channel_records.csv')
    groups=collections.defaultdict(list); key=lambda r:(r['repo'],r['number'],r['channel'])
    for r in records:
        assert re.fullmatch('[a-f0-9]{64}',r['sha256']) and int(r['length'])>=0
        groups[key(r)].append(r)
    keys={key(r) for r in summaries}; assert len(keys)==len(summaries)==396 and set(groups)<=keys
    assert len(records)==1477
    thread_counts=collections.Counter((r['repo'],r['number']) for r in summaries);assert len(thread_counts)==66 and set(thread_counts.values())=={6}
    for r in summaries:
        rs=groups[key(r)];assert len(rs)==int(r['record_count']);assert [int(q['position']) for q in rs]==list(range(len(rs)));assert len({q['record_id'] for q in rs})==len(rs)
        assert (r['joined_D6']=='True')==(r['channel']=='issue_comments')
        if r['channel']!='issue_comments':assert int(r['joined_hits'])==0
    exceptions=[r for r in summaries if r['coverage_issue']];assert len(exceptions)==1
    e=exceptions[0];assert (e['number'],e['channel'],e['record_count'],e['expected_count'],e['coverage_issue'])==('13020','review_comments','2','1','metadata count mismatch')
    inventory=json.loads((ROOT/'evidence/thread_inventory.json').read_text()); comments={(r['repo'],r['number'],c['comment_id']):c['sha256'] for r in inventory for c in r['comments']}
    inline={(r['repo'],r['number'],r['record_id']):r['sha256'] for r in records if r['channel']=='review_comments'}
    receipt=read('evidence/public_source_recheck.csv');assert len(receipt)==41
    for r in receipt:
        k=(r['repo'],r['number'],r['record_id']);expected=(inline if r['channel']=='inline' else comments)[k]
        assert r['status']=='identical' and r['observed_sha256']==r['frozen_sha256']==expected
    assert sum(r['channel']=='inline' for r in receipt)==2
    summary={'threads':66,'channels':396,'record_digests':1477,'nonissue_record_digests':sum(r['channel']!='issue_comments' for r in records),'nonissue_channels_with_recorded_D6_matches':0,'coverage_exceptions':[{k:e[k] for k in ['repo','number','channel','record_count','expected_count','coverage_issue']}],'fresh_public_digest_receipts':len(receipt),'fresh_inline_receipts':2}
    out.mkdir(parents=True,exist_ok=True);(out/'channel_audit.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':run(Path(sys.argv[1]))
