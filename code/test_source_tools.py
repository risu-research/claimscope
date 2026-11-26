#!/usr/bin/env python3
"""Exercise the source review workflow using archived bodies and controlled API responses."""
import csv, json, sys, tempfile, importlib.util, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'code'/f'{name}.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def run(out):
    review=module('review_reports'); fetch=module('fetch_sources'); checks=[]
    def check(name,test):
        assert test,name;checks.append(name)
    def rejected(name,func):
        try:func()
        except ValueError:checks.append(name)
        else:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix='claimscope-review-') as tmp:
        t=Path(tmp); counts=review.prepare(t/'base');check('full source identity inventory',sum(counts.values())==2886 and counts['outside_cutoff']==36)
        check('body scope',counts['verified']+counts['redacted_replay']==508 and counts['source_required']==2342)
        decisions=t/'base'/'decisions.csv';initial=review.compare(decisions,t/'empty.json');check('empty review remains unreviewed',initial['completed_prs']==0 and initial['unreviewed_prs']==823)
        rows=review.read_csv(decisions);check('blank decisions and no group or D6 fields',len(rows)==823 and all(not r['broad'] and not r['whole_artifact'] for r in rows) and 'arm' not in rows[0] and 'D6' not in rows[0])
        threads=json.loads((ROOT/'evidence/replay_threads.json').read_text());r=next(x for x in threads if x['repo']=='web-infra-dev/rspack' and x['number']=='13020');inv=next(x for x in review.inventory() if review.key(x)==review.key(r)); bodies={c['comment_id']:c['body'] for c in r['comments']}; records=[dict(id=int(c['comment_id']),body=bodies[c['comment_id']],created_at=c['created'],updated_at=c['updated']) for c in inv['comments'] if c['eligible']]
        def request(repo,path):return records if 'page=1' in path else []
        fresh=fetch.fetch_issue(r['repo'],r['number'],request);check('matching API bodies and timestamps',all(x['status']=='identical' and x['timestamp_match'] for x in fresh['comments']))
        altered=[dict(x) for x in records];altered[0]['body']+=' changed';altered.pop();altered.append({'id':99999999999,'body':'additional record'})
        bad=fetch.fetch_issue(r['repo'],r['number'],lambda repo,path:altered);check('changed missing and added bodies distinguished',set(x['status'] for x in bad['comments'])=={'changed','unavailable','identical'} and len(bad['extra_ids'])==len(bad['missing_ids'])==1)
        check('changed body excluded',all('body' not in x for x in bad['comments'] if x['status']!='identical'))
        source=t/'fetched.json';source.write_text(json.dumps(fresh));new=review.prepare(t/'fresh',[source]);check('fetched result directly importable',new['verified']==counts['verified'])
        # Deliberately supply altered local bytes and verify that they are withheld.
        fresh['comments'][0]['body']+=' changed';source.write_text(json.dumps(fresh));new=review.prepare(t/'changed',[source]);check('local digest mismatch surfaced',new['digest_mismatch']==1)
        rejected('duplicate source identities rejected',lambda:review.prepare(t/'duplicate',[source,source]))
        rejected('previous review protected',lambda:review.prepare(t/'base'))
        def write_sheet(path,rs):
            with path.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
        idx=next(i for i,q in enumerate(rows) if review.key(q)==review.key(r));rows[idx].update(broad='positive',whole_artifact='positive',supporting_comment_ids=records[0]['id']);sheet=t/'review.csv';write_sheet(sheet,rows);result=review.compare(sheet,t/'review.json');check('separate review joins by identity',result['completed_prs']==1 and sum(x['count'] for x in result['comparison_counts'])==2)
        rows[idx]['broad']='no_observed_report';write_sheet(sheet,rows);rejected('nested definition violation rejected',lambda:review.compare(sheet,t/'bad.json'))
        rows[idx]['broad']='positive';rows[idx]['supporting_comment_ids']='99999999999';write_sheet(sheet,rows);rejected('unrecognized witness rejected',lambda:review.compare(sheet,t/'bad.json'))
        write_sheet(sheet,rows[:-1]);rejected('missing PR rejected',lambda:review.compare(sheet,t/'bad.json'))
        check('pagination',len(fetch.pages('a/b','issues/1/comments',lambda repo,path:list(range(100)) if path.endswith('page=1') else [100]))==101)
        # Exercise all five channel endpoints; exact original bodies are separately required for a real replay.
        rec=review.read_csv(ROOT/'evidence/channel_records.csv'); rr=[x for x in rec if x['repo']==r['repo'] and x['number']==r['number']];requested=[]
        def synthetic(repo,path):
            requested.append(path)
            if path.startswith('pulls/13020?') or path=='pulls/13020':return {'title':'synthetic','body':'body'}
            if '/comments?' in path:return [{'id':int(x['record_id']),'body':'synthetic'} for x in rr if x['channel']=='review_comments']
            if '/commits?' in path:return [{'sha':x['record_id'],'commit':{'message':'synthetic'}} for x in rr if x['channel']=='commit_messages']
            if '/files?' in path:return [{'filename':x['record_id'],'patch':'synthetic'} for x in rr if x['channel']=='code_diff']
            if path.startswith('actions/runs/'):return {'name':'synthetic'}
            raise ValueError('Unexpected path')
        ch=fetch.fetch_channels(r['repo'],r['number'],synthetic);check('five source channels routed',len(ch['channels'])==5 and len(requested)>=4);check('mismatched channel text cannot replay',all(q['replayed_D6_hits'] is None for q in ch['channels'] if q['records']))
        ex=next(q for q in ch['channels'] if q['channel']=='review_comments');check('historical exception retained',ex['original_coverage_issue']=='metadata count mismatch')
    out.mkdir(parents=True,exist_ok=True);(out/'source_tool_tests.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'external_reviewer_completed':False},indent=2)+'\n');print(f'{len(checks)} source/review workflow checks passed')
if __name__=='__main__':run(Path(sys.argv[1]))
