#!/usr/bin/env python3
"""Replay the pinned Peng et al. D6 extractor on public Rspack comment sources.

The historical label and the current GitHub issue-comment corpus are separate inputs.
Original code is loaded from pinned local copies if present (otherwise fetched) and its Git blob SHA is always verified.
Results are generated independently of the original private evidence snapshot.
"""
import argparse
import ast
from bisect import bisect_left, bisect_right
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import types
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PIN = "64432e0b6ed7791bbfa929c6c183fc76c75b5d58"
UPSTREAM = "PurdueDualityLab/EMSE-perf-pr-study"
PATH = "analysis/rq3_pattern_and_validation"
BLOB_SHAS = {
    "metric_patterns.py": "31aaf5eb77b97be24cb4be359d1a30c862c2293e",
    "extract_metrics.py": "cf5b93ff071a39a0e4b2d8a4fdb85a2059b80a86",
}
FUNCTIONS = {"_token_starts", "_tok", "_any_within", "_nearest_within", "_mask_spans", "_snippet", "extract_dimensions"}
REPO = "web-infra-dev/rspack"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "evidence/rspack_97_source_inventory_20261122.csv"
CUTOFF = "2026-08-27T23:59:59Z"


def checked_fetch(url, token=None):
    h = {"User-Agent": "claimscope-2026-rspack-public-audit", "Accept": "application/vnd.github+json"}
    if token and "api.github.com" in url:
        h["Authorization"] = "Bearer " + token
    for n in range(4):
        try:
            with urlopen(Request(url, headers=h), timeout=40) as resp:
                return resp.read()
        except HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < 3:
                time.sleep(2**n)
            else:
                raise
    raise RuntimeError("unreachable")


def git_blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_original_extractor():
    sources = {}
    for basename, expected in BLOB_SHAS.items():
        url = f"https://raw.githubusercontent.com/{UPSTREAM}/{PIN}/{PATH}/{basename}"
        pinned_local = ROOT / "code" / "upstream_pinned" / basename
        # The release bundles the original MIT-licensed bytes so offline
        # source verification needs no network connection.
        raw = pinned_local.read_bytes() if pinned_local.is_file() else checked_fetch(url)
        observed = git_blob_sha(raw)
        if observed != expected:
            raise ValueError(f"Pinned source hash mismatch: {basename}: {observed}")
        sources[basename] = raw.decode("utf-8")
    mp = types.ModuleType("metric_patterns")
    exec(compile(sources["metric_patterns.py"], f"{UPSTREAM}/{PIN}/metric_patterns.py", "exec"), mp.__dict__)
    src = sources["extract_metrics.py"]
    tree = ast.parse(src)
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FUNCTIONS]
    if {x.name for x in nodes} != FUNCTIONS:
        raise RuntimeError("Original extractor helper set changed")
    namespace = {"mp": mp, "re": re, "bisect_left": bisect_left,
                 "bisect_right": bisect_right, "SNIPPET_CHARS": 70}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), f"{UPSTREAM}/{PIN}/extract_metrics.py", "exec"), namespace)
    return namespace["extract_dimensions"]


def get_paginated(endpoint, token):
    result = []
    for page in range(1, 30):
        delim = "&" if "?" in endpoint else "?"
        url = f"https://api.github.com/repos/{REPO}/{endpoint}{delim}per_page=100&page={page}"
        batch = json.loads(checked_fetch(url, token))
        if not isinstance(batch, list):
            raise TypeError(f"Expected a list from {url}")
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise RuntimeError("Pagination capped")


def get_pr(num, token):
    url = f"https://api.github.com/repos/{REPO}/pulls/{num}"
    return json.loads(checked_fetch(url, token))


def bot_flag(comment):
    actor = comment.get("user") or {}
    return actor.get("type") == "Bot" or str(actor.get("login", "")).endswith("[bot]")


def any_D6(extract, text):
    return "D6" in extract(text)


def summarize_matches(extract, text):
    hits = extract(text, include_positions=True).get("D6", [])
    return {
        "detected": bool(hits), "matches": len(hits),
        "first_matches": [{"rule_id": r.get("rule_id"), "rule": r.get("rule"),
                          "cue": r.get("cue"), "quant": r.get("quant"),
                          "snippet": r.get("snippet", "")[:200]} for r in hits[:5]],
    }


def join_text(records, field="body"):
    return "\n".join(str(r.get(field)) for r in records if r.get(field) is not None)


def replay_one(num, row, extract, token):
    pr = get_pr(num, token)
    issues = get_paginated(f"issues/{num}/comments", token)
    reviews = get_paginated(f"pulls/{num}/comments", token)
    commits = get_paginated(f"pulls/{num}/commits", token)
    files = get_paginated(f"pulls/{num}/files", token)
    if pr["number"] != num:
        raise ValueError("PR identity mismatch")
    bots = [c for c in issues if bot_flag(c)]
    size_bots = [c for c in bots if "binary size-limit" in str(c.get("body", "")).lower()]
    others = [c for c in issues if not bot_flag(c)]
    pieces = {
        "description": "\n".join(str(v) for v in (pr.get("title"), pr.get("body")) if v is not None),
        "issue_comments": join_text(issues),
        "issue_comments_no_bots": join_text(others),
        "issue_comments_bots_only": join_text(bots),
        "binary_size_bot_comments_only": join_text(size_bots),
        "review_comments": join_text(reviews),
        "commit_messages": "\n".join(str(c["commit"].get("message")) for c in commits if c.get("commit", {}).get("message") is not None),
        "code_diff": "\n".join(str(f.get("patch")) for f in files if f.get("patch") is not None),
    }
    detected = {key: summarize_matches(extract, value) for key, value in pieces.items()}
    with_bots = ["description", "issue_comments", "review_comments", "commit_messages", "code_diff"]
    without_bots = ["description", "issue_comments_no_bots", "review_comments", "commit_messages", "code_diff"]
    result = {
        "pr_number": num,
        "published_D6": row["published_D6"] == "True",
        "published_D6_nodiff": None,
        "pr_url": f"https://github.com/{REPO}/pull/{num}",
        "pr_created_at": pr["created_at"],
        "pr_author_login": pr.get("user", {}).get("login"),
        "current_pr_body_updated_at": pr.get("updated_at"),
        "source_counts": {"issue_comments": len(issues), "bot_issue_comments": len(bots),
                          "binary_size_bot_comments": len(size_bots),
                          "review_comments": len(reviews), "commits": len(commits), "files": len(files),
                          "issue_comments_updated_after_snapshot": sum(bool(c.get("updated_at") and c["updated_at"] > CUTOFF) for c in issues),
                          "issue_comments_created_after_snapshot": sum(bool(c.get("created_at") and c["created_at"] > CUTOFF) for c in issues)},
        "current_replay": {
            "by_source": detected,
            "combined_any_without_bot_comments": any(detected[k]["detected"] for k in without_bots),
            "combined_any_with_bot_comments": any(detected[k]["detected"] for k in with_bots),
            "binary_size_bot_comments_original_D6": detected["binary_size_bot_comments_only"]["detected"],
            "all_bot_comments_original_D6": detected["issue_comments_bots_only"]["detected"],
        },
        "bot_binary_size_comment_refs": [
            {"id": c.get("id"), "url": c.get("html_url"), "user_login": c.get("user",{}).get("login"),
             "created_at": c.get("created_at"), "updated_at": c.get("updated_at"),
             "original_D6": summarize_matches(extract, c.get("body") or "")["detected"]}
            for c in size_bots],
    }
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--labels", type=Path, default=DEFAULT_CSV)
    p.add_argument("--out", type=Path, default=ROOT/"results/rspack_11_exact_extractor.json")
    p.add_argument("--only", type=int, nargs="*")
    args=p.parse_args()
    with args.labels.open(newline="", encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    targets = [r for r in rows if r["published_D6"] == "False" and r["bot_binary_size_present"] == "True"]
    if len(targets) != 11:
        raise ValueError(f"11 expected candidates, found {len(targets)}")
    if args.only:
        targets=[r for r in targets if int(r["pr_number"]) in args.only]
    extractor=load_original_extractor()
    token=os.environ.get("GITHUB_TOKEN")
    results=[]
    for row in targets:
        n=int(row["pr_number"])
        result=replay_one(n,row,extractor,token)
        results.append(result)
        print("PR_RESULT_JSON " + json.dumps({"pr":n,"published_D6":False,"binary_comments":result["source_counts"]["binary_size_bot_comments"],
              "original_detects_bot_D6":result["current_replay"]["binary_size_bot_comments_original_D6"],
              "original_detects_all_bot_D6":result["current_replay"]["all_bot_comments_original_D6"],
              "with_bot":result["current_replay"]["combined_any_with_bot_comments"],
              "without_bot":result["current_replay"]["combined_any_without_bot_comments"],
              "source_hits":{k:v["matches"] for k,v in result["current_replay"]["by_source"].items()},
              "comment_edits_after_snapshot":result["source_counts"]["issue_comments_updated_after_snapshot"]},ensure_ascii=False),flush=True)
    summary={
        "cohort": "Published D6-negative Rspack PRs carrying a current bot binary-size comment",
        "pin":PIN,
        "source_blob_sha1": BLOB_SHAS,
        "retrieval_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "limits": ["Current GitHub content differs potentially from the original evidence snapshot.",
                   "This audit omits the original snapshot's CI workflow names.",
                   "PR body, commits and patch content are current API representations."],
        "n":len(results),"n_original_detects_binary_bot_D6":sum(r["current_replay"]["binary_size_bot_comments_original_D6"] for r in results),
        "n_current_any_source_detects_D6":sum(r["current_replay"]["combined_any_with_bot_comments"] for r in results),
        "n_current_without_bot_detects_D6":sum(r["current_replay"]["combined_any_without_bot_comments"] for r in results),
        "results":results,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SUMMARY_JSON " + json.dumps({k:v for k,v in summary.items() if k!="results"}),flush=True)
    print("WROTE "+str(args.out),flush=True)

if __name__=="__main__":
    from r02c3b3_replay import main as replay_main
    replay_main()
