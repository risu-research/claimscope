#!/usr/bin/env python3
"""Freeze minimal public bot-comment witnesses for 72 cross-comment D6 matches.

The original upstream matcher is loaded from hash-verified MIT-licensed source
code bundled in code/upstream_pinned. --offline never accesses the network.
--collect fetches 65 public issue threads and stores only short verbatim
boundary excerpts from the two source bot comments per detected pair.
This is a controlled November public observation, not the inaccessible
August 2026 historical evidence archive.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from audit_rspack_11_exact import (
    ROOT, PIN, BLOB_SHAS, get_paginated, load_original_extractor,
    bot_flag, git_blob_sha,
)

PAIR_LEDGER = ROOT / "results/rspack_65_comment_pairs.csv"
FIXTURE = ROOT / "evidence/rspack65_boundary_witnesses_20261122.json"
EXPECTED_SOURCE_BLOBS = {
    "metric_patterns.py": "31aaf5eb77b97be24cb4be359d1a30c862c2293e",
    "extract_metrics.py": "cf5b93ff071a39a0e4b2d8a4fdb85a2059b80a86",
}
EXPECTED_PAIRS = 72
EXPECTED_PRS = 65
INERT = "\n" + " ".join(["zzcommentboundary"]*32) + "\n"
SIZES = (96, 128, 192, 256, 384, 512, 768, 1024, 1536,
         2048, 3072, 4096, 6144, 8192, 16384, 65536)
SENSITIVE = (
    re.compile(r"(?i)ghp_[a-z0-9]{30,}"),
    re.compile(r"(?i)github_pat_[a-z0-9_]{15,}"),
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)sk-[a-z0-9_-]{24,}"),
    re.compile(r"(?i)[a-z]:\\users\\"),
)

def hashed_bytes(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()

def dumps(x):
    return (json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+"\n").encode("utf8")

def source_bytes():
    out={}
    if BLOB_SHAS!=EXPECTED_SOURCE_BLOBS:
        raise ValueError("Original source blob declaration changed")
    for name,sha in EXPECTED_SOURCE_BLOBS.items():
        raw=(ROOT/"code/upstream_pinned"/name).read_bytes()
        if git_blob_sha(raw)!=sha:
            raise ValueError("Vendored original source has been modified")
        out[name]=sha
    return out

def ledger():
    with PAIR_LEDGER.open(newline="",encoding="utf8") as fh:
        items=list(csv.DictReader(fh))
    if len(items)!=EXPECTED_PAIRS or len({int(x["pr_number"]) for x in items})!=EXPECTED_PRS:
        raise ValueError("Unexpected frozen source pair population")
    seen=set()
    for item in items:
        key=(int(item["pr_number"]),int(item["match_ordinal"]))
        if key in seen: raise ValueError("Duplicate original match ordinal")
        seen.add(key)
        if (item["source_comment_gap"]!="1" or item["cue_is_bot"]!="True"
                or item["quant_is_bot"]!="True" or item["pair_only_D6"]!="True"
                or item["pair_with_separator_D6"]!="False"):
            raise ValueError("Unexpected cross-comment trace invariants")
    return items

def wanted_match(m:dict,item:dict)->bool:
    return (str(m.get("rule_id"))==item["rule_id"]
            and str(m.get("cue")).lower()==item["cue"].lower()
            and str(m.get("quant")).lower()==item["quant"].lower())

def detection(extract,left,right,item):
    lm=extract(left,include_positions=True).get("D6",[])
    rm=extract(right,include_positions=True).get("D6",[])
    paired=extract(left+"\n"+right,include_positions=True).get("D6",[])
    padded=extract(left+INERT+right,include_positions=True).get("D6",[])
    return {
        "left_alone":len(lm),
        "right_alone":len(rm),
        "pair_matches":len(paired),
        "target_present":any(wanted_match(m,item) for m in paired),
        "separated_matches":len(padded),
    }

def trim(extract,left,right,item):
    if not (not extract(left).get("D6") and not extract(right).get("D6")):
        raise ValueError("Original individually negative source pair changed")
    full=detection(extract,left,right,item)
    if not full["target_present"] or full["separated_matches"]!=0:
        raise ValueError("Pinned published source pair no longer reproduces")
    for size in SIZES:
        a,b=left[-size:],right[:size]
        match=detection(extract,a,b,item)
        if (match["target_present"] and match["left_alone"]==0
                and match["right_alone"]==0 and match["separated_matches"]==0):
            return a,b,size
    raise ValueError("No compact boundary witness preserves the original match")

def collect():
    src=source_bytes()
    items=ledger()
    groups={}
    for x in items:groups.setdefault(int(x["pr_number"]),[]).append(x)
    extract=load_original_extractor()
    token=os.getenv("GITHUB_TOKEN")
    out=[]
    for num in sorted(groups):
        comments=get_paginated(f"issues/{num}/comments",token)
        by_id={int(c["id"]):c for c in comments}
        for item in groups[num]:
            qi,ci=int(item["quant_comment_id"]),int(item["cue_comment_id"])
            if qi not in by_id or ci not in by_id:raise ValueError("Source comment missing")
            q,c=by_id[qi],by_id[ci]
            if not bot_flag(q) or not bot_flag(c):
                raise ValueError("Expected bot-authored source pair")
            left,right=q.get("body") or "",c.get("body") or ""
            a,b,k=trim(extract,left,right,item)
            content=a+"\n"+b
            if any(pattern.search(content) for pattern in SENSITIVE):
                raise ValueError(f"Potential sensitive text in public excerpt at {num}")
            out.append({
                "pr_number":num,
                "match_ordinal":int(item["match_ordinal"]),
                "rule_id":item["rule_id"],
                "cue":item["cue"],
                "quant":item["quant"],
                "quant_comment_id":qi,
                "cue_comment_id":ci,
                "quant_comment_body_sha256":hashed_bytes(left.encode("utf8")),
                "cue_comment_body_sha256":hashed_bytes(right.encode("utf8")),
                "left_public_bot_tail":a,
                "right_public_bot_head":b,
                "max_source_excerpt_chars":k,
            })
        print(f"PR {num}: {len(groups[num])} original boundary match(es)",flush=True)
    return {
        "schema":"claimscope/rspack65-minimal-boundary-witness/v1",
        "public_observation_utc":"2026-11-22",
        "original_upstream_commit":PIN,
        "original_source_git_blob_sha1":src,
        "pair_ledger_sha256":hashed_bytes(PAIR_LEDGER.read_bytes()),
        "interpretation":"Minimal verbatim end and beginning excerpts from currently retrievable public automated issue comments. They reconstruct the original detector's source-boundary behavior, not a historical author archive or a direct measure of performance improvement.",
        "witnesses":out,
    }

def replay(path:Path):
    src=source_bytes()
    items=ledger()
    data=json.loads(path.read_text(encoding="utf8"))
    if (data.get("schema")!="claimscope/rspack65-minimal-boundary-witness/v1"
            or data.get("original_upstream_commit")!=PIN
            or data.get("original_source_git_blob_sha1")!=src
            or data.get("pair_ledger_sha256")!=hashed_bytes(PAIR_LEDGER.read_bytes())):
        raise ValueError("Witness provenance does not match released sources")
    rows=data.get("witnesses",[])
    if len(rows)!=EXPECTED_PAIRS or len({w["pr_number"] for w in rows})!=EXPECTED_PRS:
        raise ValueError("Unexpected witness population")
    fixed={(int(x["pr_number"]),int(x["match_ordinal"])):x for x in items}
    seen=set()
    extract=load_original_extractor()
    maxlen=0
    for w in rows:
        key=(w["pr_number"],w["match_ordinal"])
        if key in seen or key not in fixed:raise ValueError("Unknown or duplicate witness")
        seen.add(key)
        item=fixed[key]
        for name,col in (("rule_id","rule_id"),("cue","cue"),("quant","quant"),
                         ("quant_comment_id","quant_comment_id"),("cue_comment_id","cue_comment_id")):
            if str(w[name])!=str(item[col]):raise ValueError("Witness provenance mismatch")
        a=w["left_public_bot_tail"]
        b=w["right_public_bot_head"]
        if not a or not b or any(p.search(a+"\n"+b) for p in SENSITIVE):
            raise ValueError("Empty or unsafe public source excerpt")
        m=detection(extract,a,b,item)
        if (m["left_alone"]!=0 or m["right_alone"]!=0
                or m["separated_matches"]!=0 or not m["target_present"]):
            raise ValueError(f"Witness no longer reproduces original match: {key} {m}")
        maxlen=max(maxlen,max(len(a),len(b)))
    return {"pairs":len(rows),"prs":len({w["pr_number"] for w in rows}),
            "max_excerpt_length":maxlen,"original_source_blobs":src,
            "witness_sha256":hashed_bytes(path.read_bytes()),
            "offline_replay":"PASS: all 72 original-rule boundary matches, 0 individual, 0 separated"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--collect",action="store_true")
    modes.add_argument("--offline",action="store_true")
    p.add_argument("--output",type=Path,default=FIXTURE)
    a=p.parse_args()
    if a.collect:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_bytes(dumps(collect()))
    print(json.dumps(replay(a.output),sort_keys=True,ensure_ascii=False))

if __name__=="__main__":
    main()
