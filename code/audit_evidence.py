"""Join the frozen sample, comment inventory, and report classifications."""
import collections,csv,json,sys,datetime as dt,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def read(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def run(out):
    rows=read(ROOT/'data/audited_prs.csv'); population=read(ROOT/'data/rq3_labels.csv')
    key=lambda r:(r['repo_id'],r['number'])
    decisions={key(r):r for r in rows};assert len(rows)==len(decisions)==823
    inventory=json.loads((ROOT/'evidence/thread_inventory.json').read_text()); assert len(inventory)==823 and {key(r) for r in inventory}==decisions.keys()
    comments=read(ROOT/'evidence/comment_classifications.csv'); ledger={(r['repo_id'],r['number'],r['comment_id']):r for r in comments}; assert len(ledger)==len(comments)==2886
    cutoff=dt.datetime.fromisoformat('2026-08-27T22:00:00+00:00'); identity=set(); positive=collections.defaultdict(list); count_eligible=0; bots=0
    for r in inventory:
        for c in r['comments']:
            k=(*key(r),c['comment_id']);assert k not in identity;identity.add(k); q=ledger[k];assert c['sha256']==q['sha256'] and c['account_type']==q['account_type']
            if c['eligible']:
                count_eligible+=1;assert dt.datetime.fromisoformat(c['created'].replace('Z','+00:00'))<=cutoff and dt.datetime.fromisoformat(c['updated'].replace('Z','+00:00'))<=cutoff
                positive[key(r)].append((q,c))
                if q['broad']=='positive' and r['repo']=='web-infra-dev/rspack':assert c.get('bot_account')=='github-actions[bot]';bots+=1
    assert identity==ledger.keys() and count_eligible==2850 and bots==185
    for thread in inventory:
        k=key(thread); r=decisions[k]; cs=[ledger[(*k,c['comment_id'])] for c in thread['comments']]
        for e in ['broad','whole_artifact']:
            computed='positive' if any(q[e]=='positive' for q,c in positive[k]) else ('unknown' if not thread['collection_complete'] or any(q[e] in ('unknown','unclear_measurement') for q in cs) else 'no_observed_report')
            assert r[e]==computed,(k,e,r[e],computed)
    pairs=collections.Counter((r['broad'],r['whole_artifact']) for r in rows); assert pairs=={('positive','positive'):134,('positive','no_observed_report'):36,('no_observed_report','no_observed_report'):639,('unknown','unknown'):14}
    broad_only=[r for r in rows if r['broad']=='positive' and r['whole_artifact']=='no_observed_report'];assert collections.Counter(r['arm'] for r in broad_only)=={'agentic':2,'human_candidate':34};esp=[r for r in broad_only if r['repo_id']=='128479644']; assert len(esp)==32 and sum(r['arm']=='human_candidate' for r in esp)==31
    esp_population=collections.Counter(r['sample_arm'] for r in population if r['repo_id']=='128479644' and r['in_metric_layer']=='True');assert esp_population=={'agentic':2,'human_candidate':67}
    q=ledger['128479644','14029','3912175669'];assert q['broad']=='positive' and q['whole_artifact']=='no_observed_report' and '413,153' in q['reported_values'] and '413,073' in q['reported_values']
    result={'audited_PRs':len(rows),'reconstructed_PR_decisions':2*len(rows),'comment_records':len(comments),'eligible_comments':count_eligible,'observed_pairs':{'both_positive':134,'broad_only':36,'no_observed_report':639,'unknown':14},'broad_only_by_group':dict(collections.Counter(r['arm'] for r in broad_only)),'ESPHome_broad_only':len(esp),'ESPHome_broad_only_human_candidate':31,'ESPHome_population':dict(esp_population),'rspack_qualifying_bot_comments':bots,'incomplete_collections':sum(not r['collection_complete'] for r in inventory)}
    (out/'evidence_audit.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
if __name__=='__main__':
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);run(out)
