"""Replay the pinned D6 function on preserved public comment records."""
import ast, bisect, collections, csv, hashlib, json, re, types
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'; EVIDENCE=ROOT/'evidence'; REFERENCE=ROOT/'reference'
def read_csv(p):
    with p.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))
def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def write_csv(p, rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load_detector():
    upstream=ROOT/'code'/'upstream'; source=json.loads((upstream/'source.json').read_text()); files={}
    assert source['commit']=='64432e0b6ed7791bbfa929c6c183fc76c75b5d58'
    for name,digest in source['git_blob_sha1'].items():
        b=(upstream/name).read_bytes(); assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==digest;files[name]=b
    mp=types.ModuleType('metric_patterns');exec(compile(files['metric_patterns.py'],'metric_patterns.py','exec'),mp.__dict__)
    names={'_token_starts','_tok','_any_within','_nearest_within','_mask_spans','_snippet','extract_dimensions'}
    nodes=[n for n in ast.parse(files['extract_metrics.py']).body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==names
    ns={'mp':mp,'re':re,'bisect_left':bisect.bisect_left,'bisect_right':bisect.bisect_right,'SNIPPET_CHARS':70}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'extract_metrics.py','exec'),ns)
    return mp,ns['extract_dimensions']
def run(out):
    mp,ex=load_detector(); hits=lambda text:ex(text,include_positions=True).get('D6',[])
    join=lambda cs,sep='\n':sep.join(c['body'] for c in cs)
    pad='\n'+' '.join(['zzcommentboundary']*32)+'\n'
    allthreads=json.loads((EVIDENCE/'replay_threads.json').read_text())
    for r in allthreads:
        assert r['collection_complete'] and all(sha(c['body'])==c.get('replay_sha256',c['sha256']) for c in r['comments'])
    rs=[r for r in allthreads if r['repo']=='web-infra-dev/rspack'];assert len(rs)==97
    saved={r['number']:r for r in read_csv(REFERENCE/'actor_ablation.csv')}; ab=[]; order=[]; provenance=[]; lost=[]; changes=[]
    manual=collections.defaultdict(list)
    for r in read_csv(DATA/'rspack_match_labels.csv'): manual[r['number']].append(r)
    def kind(c):
        b=c['body'].lstrip()
        return 'binary' if b.startswith('## 📦 Binary Size-limit') else 'rsdoctor' if b.startswith('## Rsdoctor Bundle Diff Analysis') else 'codspeed' if c.get('bot_account')=='codspeed[bot]' else 'other'
    for r in sorted(rs,key=lambda r:int(r['number'])):
        n=r['number'];cs=r['comments'];bots=[c for c in cs if c['account_type']=='Bot'];other=[c for c in cs if c['account_type']!='Bot']; joined=hits(join(cs));atomic=sum(len(hits(c['body'])) for c in cs)
        a=dict(number=n,comments=len(cs),bot_comments=len(bots),other_comments=len(other),all_joined=len(joined),atomic=atomic,bot_only_joined=len(hits(join(bots))),non_bot_joined=len(hits(join(other))),non_bot_atomic=sum(len(hits(c['body'])) for c in other))
        assert {k:str(v) for k,v in a.items()}==saved[n],n;ab.append(a)
        if joined and not atomic:lost.append(n)
        # Map each normalized source span to its original comment.
        normalized=[mp.normalize(c['body']) for c in cs];assert mp.normalize(join(cs))=='\n'.join(normalized),n
        spans=[];start=0
        for c,s in zip(cs,normalized):spans.append((start,start+len(s),c['comment_id']));start+=len(s)+1
        def locate(s,e):return next(cid for lo,hi,cid in spans if lo<=s<e<=hi)
        mapped=[]
        for m in joined:
            mapped.append((locate(m['cue_start'],m['cue_end']),locate(m['quant_start'],m['quant_end']),m['cue'],m['quant'],m['rule_id']))
        expected=[(m['cue_comment_id'],m['quant_comment_id'],m['cue'],m['quant'],m['rule_id']) for m in manual[n]]
        assert collections.Counter(mapped)==collections.Counter(expected),(n,mapped,expected)
        provenance.extend(dict(number=n,cue_comment_id=x[0],quant_comment_id=x[1],cue=x[2],quant=x[3],rule_id=x[4]) for x in mapped)
        B=[i for i,c in enumerate(cs) if kind(c)=='binary'];R=[i for i,c in enumerate(cs) if kind(c)=='rsdoctor']
        if B and R:
            assert len(B)==len(R)==1; i,j=sorted([B[0],R[0]]);order.append(dict(number=n,intervening=j-i-1,positive=bool(joined)))
            if not joined:
                assert j==i+2 and kind(cs[i+1])=='codspeed';moved=cs[:i]+[cs[i],cs[j],cs[i+1]]+cs[j+1:]
                assert collections.Counter((c['comment_id'],c['sha256']) for c in moved)==collections.Counter((c['comment_id'],c['sha256']) for c in cs)
                h=hits(join(moved));assert len(h)==1
                assert not hits(join([cs[i],cs[j]],pad))
                changes.append(dict(number=n,original_ids=';'.join(c['comment_id'] for c in cs),reordered_ids=';'.join(c['comment_id'] for c in moved),original_hits=0,reordered_hits=len(h),cue=h[0]['cue'],quantity=h[0]['quant']))
    assert len(lost)==65 and len(changes)==8 and len(provenance)==133
    assert collections.Counter((r['intervening']==0,r['positive']) for r in order)=={(True,True):79,(False,True):4,(False,False):8}
    # The mechanism labels retain human interpretation; source spans and match signatures are computed above.
    categories=collections.Counter(m['standard_mechanism'] for rows in manual.values() for m in rows)
    assert categories=={'cross_record_distinct_artifacts':75,'cross_record_runtime_memory':14,'within_record_component':32,'within_record_runtime_or_memory':10,'within_record_title_or_version':2}
    cross=sum(m['cue_comment_id']!=m['quant_comment_id'] for m in provenance);assert cross==89
    val=next(r for r in allthreads if r['repo']=='valkey-io/valkey');cs=val['comments'];v=hits(join(cs));assert len(v)==1 and sum(len(hits(c['body'])) for c in cs)==0
    # Next.js: change a single character or constrain only the HTML-comment-removal step.
    original_regex=mp._HTML_COMMENT_RE;nextjs=[]
    for trace in read_csv(REFERENCE/'nextjs_mechanism_trace.csv'):
        r=next(r for r in allthreads if r['repo']==trace['repo'] and r['number']==trace['number']);cs=r['comments']; ids=[c['comment_id'] for c in cs];ss=[c['body'] for c in cs if c['body'].strip()];i=ids.index(trace['opener_id']);w=next(c['body'] for c in cs if c['comment_id']==trace['witness_id']);assert sha(w)==trace['raw_witness_sha256'];op=cs[i]['body'];assert op=='## Tests Passed\n\n<!-- ## Failing test suites -- >'
        fixed=[dict(c,body=c['body'].replace('-- >','-->',1)) if c['comment_id']==trace['opener_id'] else c for c in cs]
        full='\n'.join(ss);fixedtext=join([c for c in fixed if c['body'].strip()]);parts=[mp._LONG_TOKEN_RE.sub(' ',s) for s in ss]
        assert '\n'.join(parts)==mp._LONG_TOKEN_RE.sub(' ',full)
        class Bounded:
            def sub(self,replacement,text):
                assert replacement==' ' and text=='\n'.join(parts)
                return '\n'.join(original_regex.sub(replacement,s) for s in parts)
        before=hits(full);after=hits(fixedtext);single=hits(w);mp._HTML_COMMENT_RE=Bounded()
        try: bounded=hits(full)
        finally:mp._HTML_COMMENT_RE=original_regex
        sig=lambda a:collections.Counter((x['rule_id'],x['cue'],x['quant_kind'],x['quant']) for x in a)
        assert (len(single),len(before),len(after),len(bounded))==(67,0,67,67);assert sig(single)==sig(after)==sig(bounded)
        nextjs.append(dict(number=r['number'],single=len(single),joined=len(before),one_space_removed=len(after),html_per_record=len(bounded)))
    write_csv(out/'actor_ablation.csv',ab);write_csv(out/'order_only.csv',changes);write_csv(out/'match_sources.csv',provenance);write_csv(out/'nextjs_replay.csv',nextjs)
    summary={'rspack_threads':97,'rspack_comments':sum(r['comments'] for r in ab),'bot_comments':sum(r['bot_comments'] for r in ab),'conditions':{k:{'positive_prs':sum(r[k]>0 for r in ab),'matches':sum(r[k] for r in ab)} for k in ['all_joined','bot_only_joined','non_bot_joined','atomic']},'boundary_dependent_prs':len(lost),'order_only_changes':len(changes),'cross_comment_matches':cross,'manual_mechanism_counts':dict(categories),'valkey_joined_matches':len(v),'valkey_separate_matches':0,'nextjs_threads':len(nextjs)}
    (out/'detector_summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
if __name__=='__main__':
    import sys
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);run(out)
