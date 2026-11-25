#!/usr/bin/env python3
"""Frozen R02-B1 census: semantic witnesses fixed prior to extractor replay.
All public comment bodies are retained in the transient run artifact for audit.
No untrusted PR source is executed.
"""
import csv,collections,concurrent.futures,hashlib,json,datetime,re
from r01b1_six_channel_replay import ROOT,HASH,PIN,BLOB_SHAS,extract,get,pages,repo_of,positive,sha,one
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
CUT='2026-08-27T22:00:00Z'
# Exact subset from frozen R02-A sample SHA256 530fb02b8eca1a8ca5c2152080eb7e8b0b823d60d59cdbd1b4bcc34304c7abe6.
IDS={(42009758,39315),(939393745,1743),(701494311,2467),(34526884,55611),(42009758,39214),(3328572,17229),(70107786,86338),(70107786,82654),(70107786,81994),(204086862,13876),(79375056,12246),(70107786,88708),(70107786,94201),(70107786,94192),(70107786,80415),(70107786,81411)}
# Semantic adjudication from public issue comments before running D6.
# TypeDoc uses du -h (allocated disk space, not logical byte length); retain as a distinct documentation-artifact outcome.
WIT={55611:[3486780549,3486784358],86338:[3565202208],82654:[3188935214],81994:[3111513386],80415:[2963471445],12246:[3962749891]}
DOC={12246}
def eligible(c):return bool(c.get('created_at') and c.get('updated_at') and c['created_at']<=CUT and c['updated_at']<=CUT)
def hits(t):return extract(t,include_positions=True).get('D6',[])
def read_hits(t):return {'n':len(hits(t)),'hits':hits(t)}
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH
    rows=[r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines()) if (int(r['repo_id']),int(r['number'])) in IDS]
    assert len(rows)==16 and all(positive(r['in_metric_layer']) and not positive(r['D6']) for r in rows)
    def work(r):
        repo=repo_of(r);n=int(r['number']);rid=int(r['repo_id']);base='/repos/'+repo
        p,_=get(base+'/pulls/'+str(n));assert p['base']['repo']['id']==rid and p['number']==n
        cs=pages(base+'/issues/'+str(n)+'/comments');assert len(cs)==p['comments'] and len({c['id'] for c in cs})==len(cs)
        assert set(WIT.get(n,[]))<={c['id'] for c in cs if eligible(c)}
        items=[]
        for c in cs:
            body=c['body']
            items.append({'id':c['id'],'url':c['html_url'],'actor':c['user']['login'],'author_id':c['user']['id'],'type':c['user']['type'],'created':c['created_at'],'updated':c['updated_at'],'eligible':eligible(c),'body':body,'sha256':sha(body),'witness':c['id'] in WIT.get(n,[])})
        z={'repo':repo,'number':n,'repo_id':rid,'arm':r['sample_arm'],'published_D6':False,'head':p['head']['sha'],'base':p['base']['sha'],'expected_comments':p['comments'],'comments':items,
            'primary_report':bool(WIT.get(n)),'conventional_size_report':bool(WIT.get(n)) and n not in DOC,'documentation_allocated_size':n in DOC}
        # Replay after semantic outcomes were fixed.
        for c in items:c['D6']=read_hits(c['body'])
        z['joined_all']=read_hits('\n'.join(c['body'] for c in items))
        z['joined_eligible']=read_hits('\n'.join(c['body'] for c in items if c['eligible']))
        z['six_channel']=one(r)
        z['same_issue_hash']=z['six_channel']['channels']['issue_comments']['joined_sha256']==sha('\n'.join(c['body'] for c in items))
        assert z['same_issue_hash']
        # Counterfactual format transformations; preserve baseline original.
        for c in items:
            if not c['witness']:continue
            t=c['body']
            # Extract a compact independently interpretable report fragment, no cross-comment joining.
            lines=t.splitlines()
            if repo=='vercel/next.js':
                a=next(i for i,l in enumerate(lines) if 'Client Bundles (main, webpack)' in l)
                b=next(i for i in range(a+1,len(lines)) if '</details>' in lines[i])
                fragment='\n'.join(lines[a:b+1])
            else:fragment=t
            # Units-only and explicit cue changes are synthetic diagnostics, never new evidence.
            canonical=re.sub(r'(?<=\d)\s*kB\b',' KB',fragment)
            c['diagnostics']={'fragment':fragment,'fragment_hits':read_hits(fragment),
                'canonical_units_hits':read_hits(canonical),
                'explicit_size_heading_hits':read_hits('Bundle size\n'+fragment),
                'explicit_size_first_numeric_row_hits':read_hits('Bundle size '+next((l for l in fragment.splitlines() if re.search(r'\d(?:\.\d+)?\s*(?:kB|KB|MB|bytes| B)\b',l)),''))}
        try:
            runs=pages(base+'/actions/runs',{'event':'pull_request','head_sha':p['head']['sha']},'workflow_runs')
            z['runs']=[{k:x.get(k) for k in ('id','name','head_sha','status','conclusion','path','html_url','created_at','updated_at')} for x in runs]
        except Exception as e:z['runs_error']=str(e)
        return z
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for f in concurrent.futures.as_completed([pool.submit(work,r) for r in rows]):
            z=f.result();out.append(z)
            print('B1_ROW '+json.dumps({'repo':z['repo'],'number':z['number'],'comments':len(z['comments']),'primary':z['primary_report'],'issue_D6':z['joined_eligible']['n'],'six_D6':z['six_channel'].get('current_D6'),'errors':z['six_channel'].get('errors',{})}),flush=True)
    out.sort(key=lambda x:(x['repo_id'],x['number']))
    d={'pin':PIN,'source_blob_sha1':BLOB_SHAS,'label_sha256':HASH,'cutoff':CUT,'retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':out}
    OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    print('R02B1_SUMMARY '+json.dumps({'n':len(out),'comments':sum(len(z['comments']) for z in out),'eligible':sum(c['eligible'] for z in out for c in z['comments']),'primary':sum(z['primary_report'] for z in out),'conventional':sum(z['conventional_size_report'] for z in out),'issue_D6':sum(bool(z['joined_eligible']['n']) for z in out),'six_D6':sum(bool(z['six_channel'].get('current_D6')) for z in out),'witness_diagnostics':[{'number':z['number'],'id':c['id'],'full':c['D6']['n'],'fragment':c['diagnostics']['fragment_hits']['n'],'units':c['diagnostics']['canonical_units_hits']['n'],'heading':c['diagnostics']['explicit_size_heading_hits']['n'],'row':c['diagnostics']['explicit_size_first_numeric_row_hits']['n']} for z in out for c in z['comments'] if c['witness']]}),flush=True)
if __name__=='__main__':main()
