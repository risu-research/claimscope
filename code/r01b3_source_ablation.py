#!/usr/bin/env python3
"""R01-B3: frozen-cohort issue-comment source ablations using original extractor.
The selected report templates/IDs are fixed before executing ablations.
Whole-comment removal is a diagnostic, not a correction of reporting rates.
"""
import csv, collections, concurrent.futures, hashlib, json, re, datetime
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,extract,get,pages,repo_of,positive,sha,one,late,CHANNELS
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
SEP='\n'+' '.join(['zzcommentboundary']*32)+'\n'
SELECTED={
'getsentry/sentry-javascript':{19852:4076480031},
'ant-design/ant-design':{54455:3112640375},
'MetaMask/metamask-extension':{38237:3575775076,39309:3877411989,39310:3772871244,39314:3760112434,42685:4451765149,42686:4451737968,42687:4451777593,42688:4451777502,42795:4490087412,42862:4510848603},
'vercel/next.js':dict(zip([79987,79991,79997,80326,80551,81459,84225,84270,86589,88336,89555,90868,92023,92628],[2922800272,2922817478,2922886635,2956369843,2978234169,3052733129,3333523404,3338713575,3586867667,3729934063,3856486753,3998080155,4146203371,4226274630])),
'sanity-io/sanity':{12338:4011076631},
'streamlit/streamlit':{13099:3568623137},
'BoundaryML/baml':{3595:4569187166},
'lynx-family/lynx-stack':{1385:3139477674,2352:4082986141}}
def hits(t):return extract(t,include_positions=True).get('D6',[])
def compact(h):return {k:h.get(k) for k in ('rule_id','cue','quant','quant_kind')}
def bot(c):return (c.get('user') or {}).get('type')=='Bot'
def login(c):return (c.get('user') or {}).get('login','')
def body(c):return c.get('body') or ''
def report_template(repo,c):
    t=body(c).lower();a=login(c)
    if repo=='vercel/next.js':return a in ('ijjk','nextjs-bot') and 'stats from current pr' in t
    if repo=='MetaMask/metamask-extension':return a in ('metamaskbot','metamaskbotv2[bot]') and 'bundle size diffs' in t
    if repo=='lynx-family/lynx-stack':return a=='relativeci[bot]' and 'bundle size' in t
    if repo=='streamlit/streamlit':return a=='github-actions[bot]' and ('wheel size change detected' in t or 'bundle size change detected' in t or 'streamlit-bundle-size-check' in t)
    if repo=='BoundaryML/baml':return a=='github-actions[bot]' and 'binary size checks' in t
    if repo=='ant-design/ant-design':return a=='codecov[bot]' and 'total bundle size' in t and 'bundle' in t
    if repo=='sanity-io/sanity':return a=='github-actions[bot]' and 'bundle-stats-comment' in t
    if repo=='getsentry/sentry-javascript':return a=='github-actions[bot]' and 'cdn bundle' in t
    return False
def cond(a,keep,mode='compact'):
    retained=[c for c in a if keep(c)]
    if mode=='atomic':
        h=[h for c in retained for h in hits(body(c))]
    else:
        s='\n'.join(body(c) for c in retained) if mode=='compact' else '\n'.join(body(c) if keep(c) else SEP for c in a)
        h=hits(s)
    return {'positive':bool(h),'hits':len(h),'witnesses':[compact(x) for x in h[:3]],'kept':len(retained)}
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH
    rows=[r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines()) if positive(r['in_metric_layer'])]
    rsp=[r for r in rows if repo_of(r).lower()=='web-infra-dev/rspack']
    non=[r for r in rows if positive(r['D6']) and repo_of(r).lower()!='web-infra-dev/rspack']
    assert len(rsp)==97 and sum(positive(r['D6']) for r in rsp)==83 and len(non)==70
    assert sum(len(v) for v in SELECTED.values())==31
    snap=json.loads((ROOT/'evidence/rspack97_semantic_public_snapshot.json').read_text())
    frozen={int(x['pr_number']):{int(c['comment_id']):c['body_sha256'] for c in x['eligible_reports']} for x in snap['prs']}
    assert len(frozen)==97
    def work(r):
        repo=repo_of(r);n=int(r['number']);rid=int(r['repo_id']);is_rsp=repo.lower()=='web-infra-dev/rspack'
        z={'repo':repo,'number':n,'repo_id':rid,'arm':r['sample_arm'],'published_D6':positive(r['D6']),'rspack':is_rsp}
        try:
            try:p,_=get('/repos/'+repo+'/pulls/'+str(n))
            except RuntimeError:p,_=get('/repositories/'+str(rid)+'/pulls/'+str(n))
            assert p['number']==n and p['base']['repo']['id']==rid
            a=pages('/repos/'+p['base']['repo']['full_name']+'/issues/'+str(n)+'/comments')
            assert len(a)==p['comments']
            author=p['user']['login']; sel=SELECTED.get(repo,{}).get(n)
            if is_rsp:
                target=set(frozen[n]); mismatches=[c['id'] for c in a if c['id'] in target and sha(body(c))!=frozen[n][c['id']]]
                z['frozen_report_missing']=sorted(target-{c['id'] for c in a})
                z['frozen_report_hash_mismatch']=mismatches
                if z['frozen_report_missing'] or mismatches: raise ValueError('frozen Rspack report changed')
                producer={login(c) for c in a if c['id'] in target}
            else:
                target={c['id'] for c in a if report_template(repo,c)} if sel else set()
                z['selected_template_match']=sel in target if sel else None
                if sel and sel not in target: raise ValueError('selected report template not recovered')
                producer={login(c) for c in a if c['id'] in target}
            def t(c):return c['id'] in target
            def b(c):return bot(c)
            def au(c):return login(c)==author
            def pr(c):return login(c) in producer
            def pre(c):return not (late(c.get('created_at')) or late(c.get('updated_at')))
            tests={'full':lambda c:True,'target_only':t,'without_target':lambda c:not t(c),'bot_only':b,'without_bot':lambda c:not b(c),'without_target_or_bot':lambda c:not(t(c) or b(c)),'author_only':au,'without_author':lambda c:not au(c),'producer_only':pr,'without_producer':lambda c:not pr(c),'precutoff_full':pre,'precutoff_without_target':lambda c:pre(c) and not t(c)}
            if sel:tests['without_selected_only']=lambda c:c['id']!=sel
            z.update(author=author,head_sha=p['head']['sha'],issue_count=len(a),joined_sha256=sha('\n'.join(body(c) for c in a)),selected_id=sel,
                comments=[{'id':c['id'],'actor':login(c),'type':(c.get('user') or {}).get('type'),'sha256':sha(body(c)),'target':t(c),'producer':pr(c),'author':au(c),'late':not pre(c),'atomic_hits':len(hits(body(c))),'atomic_witnesses':[compact(h) for h in hits(body(c))[:2]]} for c in a],
                conditions={name:{m:cond(a,pred,m) for m in ('compact','gap','atomic')} for name,pred in tests.items()})
            # Rspack other channels are collected in this run; non-Rspack uses
            # the separately preserved B1 six-channel result with issue hash check.
            if is_rsp:
                full=one(r)
                z['other_channels']={k:v for k,v in full['channels'].items() if k!='issue_comments'}
                z['other_errors']=full['errors']
                z['other_issue_hash']=full['channels'].get('issue_comments',{}).get('joined_sha256')
                z['other_head_sha']=full.get('head_sha')
        except Exception as e:z['error']=str(e)
        return z
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        result=[]
        for f in concurrent.futures.as_completed([pool.submit(work,r) for r in non+rsp]):
            z=f.result();result.append(z)
            print('B3_ROW '+json.dumps({k:z.get(k) for k in ('repo','number','arm','published_D6','issue_count','error')},ensure_ascii=False),flush=True)
    result.sort(key=lambda z:(z['repo_id'],z['number']))
    summary={'n':len(result),'errors':[{'repo':z['repo'],'number':z['number'],'error':z['error']} for z in result if 'error'in z],
             'targeted_prs':sum(any(c['target'] for c in z.get('comments',[])) for z in result),
             'targeted_comments':sum(sum(c['target'] for c in z.get('comments',[])) for z in result)}
    OUT.write_text(json.dumps({'pin':PIN,'label_sha256':HASH,'source_blob_sha1':BLOB_SHAS,'retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'summary':summary,'rows':result},ensure_ascii=False,indent=2)+'\n')
    print('B3_SUMMARY '+json.dumps(summary),flush=True)
if __name__=='__main__':main()
