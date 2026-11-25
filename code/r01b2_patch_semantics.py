#!/usr/bin/env python3
"""R01-B2 exact witness census and targeted boundary interventions."""
import csv, collections, concurrent.futures, hashlib, json, re, datetime
from r01b1_six_channel_replay import ROOT, HASH, PIN, BLOB_SHAS, extract, get, pages, repo_of, positive, sha
OUT=ROOT/'results'/'rspack_11_exact_extractor.json'
SEP='\n'+' '.join(['zzcommentboundary']*32)+'\n'
def hits(t):
    return extract(t,include_positions=True).get('D6',[])
def stats(t):
    a=hits(t)
    return {'sha256':sha(t),'length':len(t),'hits':a}
def line_variant(patch,mode):
    out=[]
    for line in patch.splitlines():
        if line.startswith('@@'):
            keep=False
        else:
            keep=(line.startswith('+') and not line.startswith('+++')) if mode=='added' else (line.startswith(' ') or (line.startswith('+') and not line.startswith('+++'))) if mode=='postimage' else (line.startswith(' ') or (line.startswith('-') and not line.startswith('---')))
        out.append(line if keep else SEP)
    return '\n'.join(out)
def one(r):
    repo=repo_of(r); n=int(r['number']); rid=int(r['repo_id'])
    result={'repo':repo,'number':n,'repo_id':rid,'arm':r['sample_arm']}
    try:
        try:p,_=get('/repos/'+repo+'/pulls/'+str(n))
        except RuntimeError:p,_=get('/repositories/'+str(rid)+'/pulls/'+str(n))
        assert p['number']==n and p['base']['repo']['id']==rid
        base='/repos/'+p['base']['repo']['full_name']
        fs=pages(base+'/pulls/'+str(n)+'/files')
        result.update(head_sha=p['head']['sha'],base_sha=p['base']['sha'],file_count=len(fs),expected=p['changed_files'],files=[])
        patches=[]
        for f in fs:
            patch=f.get('patch')
            x={k:f.get(k) for k in ('filename','status','sha','additions','deletions','changes','blob_url')}
            if patch is not None:
                patches.append(patch)
                x['original']=stats(patch)
                if x['original']['hits']:
                    x['variants']={m:stats(line_variant(patch,m)) for m in ('added','postimage','preimage')}
                    # Original patch line ranges for source interpretation, no full text retained.
                    l=patch.splitlines(); cand=set()
                    for i,s in enumerate(l):
                        if re.search(r'chunk size|file size|bundle|binary size|tree.shak|minified|gzip|20% improvement|33%',s,re.I):
                            for j in range(max(0,i-2),min(len(l),i+3)):cand.add(j)
                    x['context_line_numbers']=sorted(j+1 for j in cand)
            else:
                x['original']=None
            result['files'].append(x)
        result['joined']=stats('\n'.join(patches))
        result['separated_count']=sum(len(f['original']['hits']) for f in result['files'] if f['original'] is not None)
        result['padded']=stats(SEP.join(patches))
        result['joined_variants']={m:stats(SEP.join(line_variant(p,m) for p in patches)) for m in ('added','postimage','preimage')}
    except Exception as e:result['error']=str(e)
    return result
def valkey():
    a=pages('/repos/valkey-io/valkey/issues/2311/comments')
    A,B=3041304632,3045883356
    d={x['id']:x['body'] for x in a}
    aa,bb=d[A],d[B]
    full='\n'.join(x['body'] for x in a if x.get('body') is not None)
    cue='bundle sizes';quant='5% is a great improvement'
    assert aa.count(cue)==1 and bb.count(quant)==1
    conditions={'full':full,'A':aa,'B':bb,'pair':aa+'\n'+bb,'reverse':bb+'\n'+aa,'padded_pair':aa+SEP+bb,
        'pair_without_cue':aa.replace(cue,'zzremovedcue')+'\n'+bb,
        'pair_without_quant':aa+'\n'+bb.replace(quant,'zzremovedquant'),
        'full_without_A':'\n'.join(x['body'] for x in a if x['id']!=A),
        'full_without_B':'\n'.join(x['body'] for x in a if x['id']!=B),
        'bot_only':'\n'.join(x['body'] for x in a if x['user']['type']=='Bot'),
        'nonbot_only':'\n'.join(x['body'] for x in a if x['user']['type']!='Bot')}
    return {'repo':'valkey-io/valkey','number':2311,'comments':[{'id':x['id'],'sha256':sha(x['body']),'created':x['created_at'],'updated':x['updated_at']} for x in a],
        'conditions':{k:stats(v) for k,v in conditions.items()}}
def main():
    raw=(ROOT/'data/rq3_labels.csv').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH
    rr=[r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines()) if positive(r['in_metric_layer']) and positive(r['D6']) and not positive(r['D6_nodiff']) and repo_of(r).lower()!='web-infra-dev/rspack']
    assert len(rr)==12 and len({(r['repo_id'],r['number']) for r in rr})==12
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(one,rr))
    v=valkey()
    data={'pin':PIN,'source_blob_sha1':BLOB_SHAS,'label_sha256':HASH,'retrieval_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':rows,'valkey':v}
    OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print('B2_SUMMARY '+json.dumps({'rows':[{'repo':x['repo'],'number':x['number'],'error':x.get('error'),'joined_hits':len(x.get('joined',{}).get('hits',[])),'separated':x.get('separated_count'),'added':len(x.get('joined_variants',{}).get('added',{}).get('hits',[])),'postimage':len(x.get('joined_variants',{}).get('postimage',{}).get('hits',[])),'preimage':len(x.get('joined_variants',{}).get('preimage',{}).get('hits',[]))} for x in rows],'valkey':{k:len(z['hits']) for k,z in v['conditions'].items()}}),flush=True)
if __name__=='__main__':main()
