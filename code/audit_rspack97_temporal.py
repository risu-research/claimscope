#!/usr/bin/env python3
"""Freeze public timestamp metadata for the 97 Rspack issue threads.

A two-mode audit: live collection from GitHub, or fully offline validation.
The public ledger contains IDs, timestamps and a bot flag. It never archives
comment bodies, usernames, email addresses, or any private original snapshot.
Metadata does not prove that earlier deleted comments never existed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from audit_rspack_11_exact import ROOT, get_paginated, bot_flag

INVENTORY = ROOT / "evidence/rspack_97_source_inventory_20261122.csv"
EXPECTED_INVENTORY_SHA256 = "039c8161e85c31940fd2c9333f21d8ae0a43219df694812538dfe45ebede776e"
LEDGER = ROOT / "evidence/rspack97_issue_comment_timestamps_20261122.csv"
SUMMARY = ROOT / "results/rspack97_temporal_provenance_20261122.json"
CUTOFF = "2026-08-27T22:00:14.356079Z"
EXPECTED = {"prs": 97, "comments": 476, "bot_comments": 437,
            "human_comments": 39, "late_created": 0, "late_updated": 0}
EXPECTED_MAX_UPDATE = "2026-06-02T07:58:45Z"
COLUMNS = ["pr_number","comment_id","created_at","updated_at","is_bot"]

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(obj):
    return (json.dumps(obj, sort_keys=True, indent=2) + "\n").encode("utf8")

def parse_utc(text: str) -> datetime:
    if not text.endswith("Z"):
        raise ValueError("Expected an explicit UTC Z timestamp")
    stamp = datetime.fromisoformat(text[:-1]+"+00:00")
    if stamp.utcoffset().total_seconds() != 0:
        raise ValueError("Expected UTC timestamp")
    return stamp

def load_inventory():
    raw=INVENTORY.read_bytes()
    if digest(raw)!=EXPECTED_INVENTORY_SHA256:
        raise ValueError("Source inventory hash mismatch")
    rows=list(csv.DictReader(raw.decode("utf8").splitlines()))
    if len(rows)!=97 or len({r["pr_number"] for r in rows})!=97:
        raise ValueError("Unexpected fixed Rspack population")
    for row in rows:
        if row["published_D6"] not in ("True","False"):
            raise ValueError("Invalid published D6 label")
    return {int(r["pr_number"]):r for r in rows}

def collect(ids:dict[int,dict], token:str|None):
    records=[]
    for n in sorted(ids):
        comments=get_paginated(f"issues/{n}/comments",token)
        if len(comments)!=int(ids[n]["comment_count_issue"]):
            raise ValueError(f"Comment population changed for PR {n}")
        for c in comments:
            row={"pr_number":str(n),"comment_id":str(int(c["id"])),
                 "created_at":c["created_at"],"updated_at":c["updated_at"],
                 "is_bot":str(bool(bot_flag(c)))}
            records.append(row)
        print(f"Audited PR {n}: {len(comments)} comments",flush=True)
    return sorted(records,key=lambda r:(int(r["pr_number"]),int(r["comment_id"])))

def write_csv(path:Path,rows:list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=COLUMNS,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def replay(ledger:Path,summary:Path):
    inv=load_inventory()
    rows=list(csv.DictReader(ledger.open(newline="",encoding="utf8")))
    if len({r["comment_id"] for r in rows})!=len(rows):
        raise ValueError("Duplicate public comment ID")
    cutoff=parse_utc(CUTOFF)
    by_id={n:0 for n in inv}
    last=""
    max_utc=None
    bots=0
    late_created=0
    late_updated=0
    for row in rows:
        if set(row)!=set(COLUMNS):
            raise ValueError("Unexpected column schema")
        num=int(row["pr_number"])
        if num not in inv:
            raise ValueError("Unlisted PR")
        if row["is_bot"] not in ("True","False"):
            raise ValueError("Invalid bot flag")
        if row["created_at"]>row["updated_at"]:
            raise ValueError("Comment update predates creation")
        created=parse_utc(row["created_at"])
        updated=parse_utc(row["updated_at"])
        if created>updated:
            raise ValueError("Timestamp order wrong")
        bots+=row["is_bot"]=="True"
        late_created+=created>cutoff
        late_updated+=updated>cutoff
        by_id[num]+=1
        if max_utc is None or updated>max_utc:
            max_utc=updated
            last=row["updated_at"]
    for num, n in by_id.items():
        if n!=int(inv[num]["comment_count_issue"]):
            raise ValueError(f"Incorrect thread comment count at PR {num}")
    counts={"prs":len(by_id),"comments":len(rows),"bot_comments":bots,
            "human_comments":len(rows)-bots,"late_created":late_created,
            "late_updated":late_updated}
    if counts!=EXPECTED or last!=EXPECTED_MAX_UPDATE:
        raise ValueError(f"Unexpected public temporal audit: {counts}, latest={last}")
    summary_data={
        "schema":"claimscope/rspack97-comment-temporal/v1",
        "source_repo":"web-infra-dev/rspack",
        "reference_snapshot_utc":CUTOFF,
        "fixed_inventory_sha256":EXPECTED_INVENTORY_SHA256,
        "ledger_sha256":digest(ledger.read_bytes()),
        "last_visible_comment_updated_at":last,
        "counts":counts,
        "scope":"Currently visible public issue-thread comments. No body text retained. Timestamps do not exclude deleted comments or prove bytes of the unavailable original source snapshot.",
        "replay_command":"python3 code/audit_rspack97_temporal.py --offline",
    }
    summary.parent.mkdir(parents=True,exist_ok=True)
    summary.write_bytes(canonical(summary_data))
    return summary_data

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_mutually_exclusive_group(required=True)
    modes.add_argument("--collect",action="store_true")
    modes.add_argument("--offline",action="store_true")
    ap.add_argument("--ledger",type=Path,default=LEDGER)
    ap.add_argument("--summary",type=Path,default=SUMMARY)
    args=ap.parse_args()
    if args.collect:
        write_csv(args.ledger,collect(load_inventory(),os.getenv("GITHUB_TOKEN")))
    print(json.dumps(replay(args.ledger,args.summary),sort_keys=True))

if __name__=="__main__":
    main()
