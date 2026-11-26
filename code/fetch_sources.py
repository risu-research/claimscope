#!/usr/bin/env python3
"""Retrieve a recorded issue thread or five additional source channels for local verification."""
import argparse, collections, csv, hashlib, importlib.util, json, os, re, urllib.request, urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
BASE='https://api.github.com/repos/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def api(repo,path):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('Invalid repository')
    headers={'Accept':'application/vnd.github+json','User-Agent':'ClaimScope-source-check','X-GitHub-Api-Version':'2022-11-28'}
    if os.getenv('GITHUB_TOKEN'):headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(BASE+repo+'/'+path,headers=headers),timeout=30) as f:return json.load(f)
def pages(repo,path,request=api):
    items=[];sep='&' if '?' in path else '?'
    for i in range(1,1001):
        batch=request(repo,f'{path}{sep}per_page=100&page={i}')
        if not isinstance(batch,list):raise ValueError('Expected paginated array')
        items.extend(batch)
        if len(batch)<100:return items
    raise ValueError('Pagination limit')
def hash_text(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def check(expected,observed):
    if observed is None:return {'status':'unavailable'}
    if not isinstance(observed,str):return {'status':'invalid_body'}
    h=hash_text(observed);return {'status':'identical' if h==expected else 'changed','observed_sha256':h,**({'body':observed} if h==expected else {})}
def fetch_issue(repo,number,request=api):
    inv=next((r for r in json.loads((ROOT/'evidence/thread_inventory.json').read_text()) if r['repo']==repo and r['number']==number),None)
    if inv is None:raise ValueError('Thread is outside the frozen audit')
    observed=pages(repo,f'issues/{number}/comments',request); by={str(c['id']):c for c in observed};expected={c['comment_id']:c for c in inv['comments']}
    if len(by)!=len(observed):raise ValueError('Duplicate source records')
    result=[]
    for cid,c in expected.items():
        if not c['eligible']:continue
        q=by.get(cid);v=check(c['sha256'],q.get('body') if q else None)
        result.append({'comment_id':cid,'sha256':c['sha256'],**v,'timestamp_match':bool(q and q.get('created_at')==c['created'] and q.get('updated_at')==c['updated'])})
    return {'repo':repo,'number':number,'comments':result,'extra_ids':sorted(set(by)-set(expected)),'missing_ids':sorted(set(expected)-set(by)),'collection_complete':inv['collection_complete']}
def fetch_channels(repo,number,request=api):
    with (ROOT/'evidence/channel_records.csv').open(newline='',encoding='utf-8') as f:rows=[r for r in csv.DictReader(f) if (r['repo'],r['number'])==(repo,number)]
    if not rows:raise ValueError('No archived channel inventory for this PR')
    with (ROOT/'evidence/channel_summary.csv').open(newline='',encoding='utf-8') as f:summaries=[r for r in csv.DictReader(f) if (r['repo'],r['number'])==(repo,number) and r['channel']!='issue_comments']
    by=collections.defaultdict(list)
    for r in rows:by[r['channel']].append(r)
    # The frozen record order is retained. Fresh records are checked against that order and each digest.
    output=[]
    spec=importlib.util.spec_from_file_location('replay_detector',ROOT/'code/replay_detector.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    _,detect=mod.load_detector()
    for s in summaries:
        ch=s['channel']; records=by[ch]; observed={}; error=None
        try:
            if ch=='description':
                q=request(repo,f'pulls/{number}');observed={number:'\n'.join(str(q[k]) for k in ('title','body') if q.get(k) is not None)}
            elif ch=='review_comments':observed={str(q['id']):q.get('body') for q in pages(repo,f'pulls/{number}/comments',request)}
            elif ch=='commit_messages':observed={q['sha']:q['commit']['message'] for q in pages(repo,f'pulls/{number}/commits',request)}
            elif ch=='code_diff':observed={q['filename']:q.get('patch') for q in pages(repo,f'pulls/{number}/files',request)}
            elif ch=='ci_metadata':
                # Workflow IDs identify the recorded names; other runs may exist in the current collection.
                for r in records:
                    try:observed[r['record_id']]=request(repo,f'actions/runs/{r["record_id"]}').get('name')
                    except (OSError,ValueError,KeyError):pass
        except (OSError,ValueError,KeyError) as exc:error=type(exc).__name__
        matches=[{'record_id':r['record_id'],**check(r['sha256'],observed.get(r['record_id']))} for r in records]; expected={r['record_id'] for r in records}
        complete=error is None and all(r['status']=='identical' for r in matches)
        joined='\n'.join(r['body'] for r in matches) if complete else None
        digest_matches=bool(joined is not None and hash_text(joined)==s['joined_sha256'])
        count=len(detect(joined,include_positions=True).get('D6',[])) if digest_matches else None
        output.append({'channel':ch,'replayed_D6_hits':count,'recorded_D6_hits':int(s['joined_hits']),'replay_matches_recorded':count==int(s['joined_hits']) if count is not None else None,'records':matches,'source_error':error,'extra_ids':sorted(set(observed)-expected),'missing_ids':sorted(expected-set(observed)),'frozen_joined_sha256':s['joined_sha256'],'joined_digest_match':digest_matches,'original_coverage_issue':s['coverage_issue'],'workflow_population_check':'recorded IDs only' if ch=='ci_metadata' else 'listed current records'})
    return {'repo':repo,'number':number,'channels':output}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repo');p.add_argument('number');p.add_argument('--channels',action='store_true');p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if not a.number.isdigit():p.error('PR number must be numeric')
    r=(fetch_channels if a.channels else fetch_issue)(a.repo,a.number)
    a.output=a.output.resolve()
    if a.output==ROOT or ROOT in a.output.parents and a.output.relative_to(ROOT).parts[0]!='build':p.error('Choose build/ or an external output file')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(f'Source check saved locally: {a.output}')
if __name__=='__main__':main()
