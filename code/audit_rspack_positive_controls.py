#!/usr/bin/env python3
"""Locate original-rule D6 matches in selected published-positive Rspack PRs."""
import datetime as dt
import json
import os
from pathlib import Path
from audit_rspack_11_exact import load_original_extractor, replay_one, PIN

PR_NUMBERS=[12560,13010,13229,13759,13936,14196]
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rspack_positive_control_sources.json'


def main():
    extractor=load_original_extractor()
    token=os.environ.get('GITHUB_TOKEN')
    results=[]
    for n in PR_NUMBERS:
        x=replay_one(n,{'published_D6':'True'},extractor,token)
        y=x['current_replay']['by_source']
        if x['published_D6'] is not True:
            raise ValueError('Expected published positive')
        results.append(x)
        print('CONTROL_JSON '+json.dumps({'pr':n,
            'binary_bot':y['binary_size_bot_comments_only']['detected'],
            'all_bot_issue_comments':y['issue_comments_bots_only']['detected'],
            'all_issue_comments':y['issue_comments']['detected'],
            'nonbot_issue_comments':y['issue_comments_no_bots']['detected'],
            'description':y['description']['detected'],
            'review_comments':y['review_comments']['detected'],
            'commit_messages':y['commit_messages']['detected'],
            'code_diff':y['code_diff']['detected'],
            'current_any':x['current_replay']['combined_any_with_bot_comments'],
            'bot_match_examples':y['issue_comments_bots_only']['first_matches'][:2]},ensure_ascii=False),flush=True)
    o={'pinned_upstream_commit':PIN,'retrieval_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
       'purpose':'Positive-label checks on current public source surfaces',
       'n':len(results),
       'n_binary_bot_D6':sum(x['current_replay']['by_source']['binary_size_bot_comments_only']['detected'] for x in results),
       'n_all_bot_issue_D6':sum(x['current_replay']['by_source']['issue_comments_bots_only']['detected'] for x in results),
       'n_current_any_D6':sum(x['current_replay']['combined_any_with_bot_comments'] for x in results),
       'limits':['Selected positive cases only','Current public sources; original private snapshot unavailable','Original CI workflow names omitted'],
       'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CONTROL_SUMMARY '+json.dumps({k:v for k,v in o.items() if k!='results'},ensure_ascii=False),flush=True)

if __name__=='__main__': main()
