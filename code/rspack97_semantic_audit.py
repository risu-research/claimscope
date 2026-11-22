#!/usr/bin/env python3
"""Frozen, source-linked semantic artifact-size audit for all 97 Rspack PRs.

Collect public GitHub issue-comment evidence once, retain only necessary bot
reports, and replay the result offline. The original D6 regex is deliberately
NOT used to decide whether an artifact-size measurement is present.
Historical Peng et al. input bytes are unavailable; this is a November
public-record inspection, not an exact August snapshot reconstruction.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from audit_rspack_11_exact import ROOT, REPO, get_pr, get_paginated, bot_flag
from semantic_rspack65_size import binary_report, rsdoctor_report

INVENTORY = ROOT / "evidence/rspack_97_source_inventory_20261122.csv"
PAIRS = ROOT / "results/rspack_65_comment_pairs.csv"
PRIOR_65 = ROOT / "results/rspack65_semantic_size_audit.json"
PRIOR_32 = ROOT / "evidence/rspack97_semantic_addendum_32.csv"
SNAPSHOT = ROOT / "evidence/rspack97_semantic_public_snapshot.json"
RESULT_JSON = ROOT / "results/rspack97_semantic_size_audit.json"
RESULT_CSV = ROOT / "results/rspack97_semantic_size_audit.csv"
MANIFEST = ROOT / "results/rspack97_semantic_manifest.json"
SOURCE_LABEL_SHA256 = "c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9"
SOURCE_CUTOFF = "2026-08-27T22:00:00Z"
SCHEMA = "claimscope/rspack97-semantic-size/v1"
REQUIRED_COUNTS = {"sample": 97, "D6_positive": 83, "reports": 94,
                   "D6_negative_with_report": 11, "no_thread_report": 3,
                   "head": 91, "listed_commit": 2, "unverified_commit": 1}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def source_inputs() -> tuple[list[dict], dict[int, dict], dict[int, dict], set[int]]:
    actual = digest((ROOT / "data/rq3_labels.csv").read_bytes())
    if actual != SOURCE_LABEL_SHA256:
        raise ValueError("Original public label export SHA-256 changed")
    with INVENTORY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 97:
        raise ValueError("Rspack inventory does not contain exactly 97 PRs")
    inv: dict[int, dict] = {}
    for r in rows:
        num = int(r["pr_number"])
        if num in inv or r["sample_arm"] not in ("agentic", "human_candidate"):
            raise ValueError("Duplicate PR or invalid cohort label")
        if r["published_D6"] not in ("True", "False"):
            raise ValueError("Invalid published D6 label")
        inv[num] = r
    with PAIRS.open(newline="", encoding="utf-8") as f:
        ids = {int(r["pr_number"]) for r in csv.DictReader(f)}
    if len(ids) != 65 or not ids.issubset(inv):
        raise ValueError("Existing 65-case witness population changed")
    baseline = json.loads(PRIOR_65.read_text(encoding="utf-8"))
    baseline65 = {int(r["pr_number"]): r for r in baseline["rows"]}
    if set(baseline65) != ids:
        raise ValueError("Existing 65-case semantic audit and witness IDs disagree")
    with PRIOR_32.open(newline="", encoding="utf-8") as f:
        add = {int(r["pr_number"]): r for r in csv.DictReader(f)}
    if len(add) != 32 or set(add) != set(inv) - ids:
        raise ValueError("Incremental 32-case audit does not cover the remaining PRs")
    for num, r in add.items():
        if r["sample_arm"] != inv[num]["sample_arm"] or (r["published_D6"] == "1") != (inv[num]["published_D6"] == "True"):
            raise ValueError(f"Conflicting sample label for PR {num}")
    return rows, baseline65, add, ids


def before_cutoff(comment: dict) -> bool:
    created, updated = comment.get("created_at"), comment.get("updated_at")
    return bool(created and updated and created <= SOURCE_CUTOFF and updated <= SOURCE_CUTOFF)


def relation(commit: str | None, head: str, listed_commits: set[str]) -> str:
    if not commit:
        return "not_in_report"
    if commit == head:
        return "head"
    if commit in listed_commits:
        return "listed_pr_commit"
    return "not_verified_current_commits"


def select_reports(comments: list[dict], head: str, commits: set[str]) -> tuple[list[dict], list[dict], int]:
    """Return minimized public bot evidence, other bot digests and source count.

    Positive PRs retain only recognized report bodies. Negative PRs retain all
    bot bodies so the no-report judgment can be replayed without GitHub access.
    Human discussion text is never stored.
    """
    reports = []
    other = []
    num_bots = 0
    for c in comments:
        if not bot_flag(c):
            continue
        num_bots += 1
        raw = c.get("body") or ""
        binary = binary_report(raw)
        rsdoc = rsdoctor_report(raw)
        kind, measurement = ("binary", binary) if binary is not None else ("rsdoctor", rsdoc)
        if measurement is None:
            kind = None
        eligible = bool(measurement and measurement.get("structured") and before_cutoff(c))
        base = {
            "comment_id": int(c["id"]),
            "comment_url": c.get("html_url") or f"https://github.com/{REPO}/pull/0#issuecomment-{c['id']}",
            "author": (c.get("user") or {}).get("login"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
            "body_sha256": digest(raw.encode("utf-8")),
        }
        if eligible:
            reports.append({**base, "kind": kind, "body": raw, "measurement": measurement,
                            "commit_relation": relation(measurement.get("source_commit"), head, commits)})
        else:
            # A digest of every other bot comment documents collection coverage.
            other.append({**base, "kind": kind, "is_structured": bool(measurement and measurement.get("structured")),
                          "eligible": False})
    return reports, other, num_bots


def collect_one(inv: dict, token: str | None) -> dict:
    num = int(inv["pr_number"])
    pr = get_pr(num, token)
    if int(pr.get("number", -1)) != num:
        raise ValueError("Mismatched GitHub PR identity")
    head = pr.get("head", {}).get("sha")
    if not head:
        raise ValueError(f"Missing PR head for {num}")
    comments = get_paginated(f"issues/{num}/comments", token)
    commits = get_paginated(f"pulls/{num}/commits", token)
    sha_list = [x.get("sha") for x in commits if x.get("sha")]
    if len(sha_list) != len(set(sha_list)):
        raise ValueError(f"Duplicate commit SHA for {num}")
    reports, other, num_bots = select_reports(comments, head, set(sha_list))
    selected = sorted(reports, key=lambda r: (r["kind"] != "binary",
                          r["commit_relation"] not in ("head", "listed_pr_commit"),
                          r["comment_id"]))
    # Keep one full qualifying witness per PR; preserve IDs and digests for
    # other qualifying bot reports without retaining their potentially large
    # benchmark tables. This limits archived source text to the minimum
    # needed to reproduce the report-presence decision.
    if selected:
        for unused in selected[1:]:
            other.append({k: unused[k] for k in
                          ("comment_id", "comment_url", "author",
                           "created_at", "updated_at", "body_sha256", "kind")})
            other[-1].update(is_structured=True, eligible=True)
        selected = selected[:1]
    # Only needed source bodies are retained. For the three no-report PRs,
    # bot comment bodies are retained to independently replay a negative.
    absent_bot_bodies = []
    if not selected:
        for c in comments:
            if bot_flag(c):
                absent_bot_bodies.append({"comment_id": int(c["id"]),
                    "body": c.get("body") or "",
                    "body_sha256": digest((c.get("body") or "").encode("utf-8"))})
    return {
        "pr_number": num, "sample_arm": inv["sample_arm"],
        "published_D6": inv["published_D6"] == "True",
        "url": f"https://github.com/{REPO}/pull/{num}",
        "pr_head_sha": head, "listed_pr_commit_shas": sha_list,
        "issue_comment_count": len(comments), "bot_comment_count": num_bots,
        "eligible_reports": selected,
        "other_bot_comment_metadata": other,
        "negative_bot_bodies": absent_bot_bodies,
    }


def assess_saved(row: dict) -> dict:
    head = row["pr_head_sha"]
    commits = set(row["listed_pr_commit_shas"])
    valid = []
    for item in row["eligible_reports"]:
        raw = item["body"]
        if digest(raw.encode("utf-8")) != item["body_sha256"]:
            raise ValueError(f"Stored source body hash mismatch at PR {row['pr_number']}")
        if not before_cutoff(item):
            raise ValueError(f"Evidence was created or updated after cutoff for PR {row['pr_number']}")
        m = binary_report(raw) if item["kind"] == "binary" else rsdoctor_report(raw)
        if not m or not m.get("structured") or m != item["measurement"]:
            raise ValueError(f"Semantic parser cannot independently reproduce PR {row['pr_number']}")
        if relation(m.get("source_commit"), head, commits) != item["commit_relation"]:
            raise ValueError(f"PR commit attribution mismatch for {row['pr_number']}")
        valid.append(item)
    for item in row["other_bot_comment_metadata"]:
        if not item["body_sha256"] or not item["comment_id"]:
            raise ValueError("Incomplete bot source ledger")
    if len(valid) + len(row["other_bot_comment_metadata"]) != row["bot_comment_count"]:
        raise ValueError(f"Incomplete bot comment inventory for PR {row['pr_number']}")
    if not valid:
        if len(row["negative_bot_bodies"]) != row["bot_comment_count"]:
            raise ValueError(f"Negative PR {row['pr_number']} has no complete bot text inventory")
        for item in row["negative_bot_bodies"]:
            if digest(item["body"].encode("utf-8")) != item["body_sha256"]:
                raise ValueError("Negative bot source digest changed")
            b = binary_report(item["body"])
            d = rsdoctor_report(item["body"])
            if (b and b.get("structured")) or (d and d.get("structured")):
                raise ValueError(f"Unexpected structured report in negative PR {row['pr_number']}")
    else:
        if row["negative_bot_bodies"]:
            raise ValueError("Positive PR includes unnecessary negative raw bot evidence")
    choice = valid[0] if valid else None
    m = choice["measurement"] if choice else {}
    return {
        "pr_number": row["pr_number"], "sample_arm": row["sample_arm"],
        "published_D6": row["published_D6"],
        "report_presence": "confirmed" if choice else "no_qualifying_bot_report_in_thread",
        "source_kind": choice["kind"] if choice else "",
        "source_comment_id": choice["comment_id"] if choice else None,
        "source_url": choice["comment_url"] if choice else row["url"],
        "source_created_at": choice["created_at"] if choice else None,
        "source_updated_at": choice["updated_at"] if choice else None,
        "source_body_sha256": choice["body_sha256"] if choice else None,
        "size_value": m.get("after") or m.get("value") or (m.get("artifacts") or [{}])[0].get("size"),
        "direction": m.get("direction") or "",
        "source_commit": m.get("source_commit"),
        "revision_relation": choice["commit_relation"] if choice else "no_thread_measurement",
        "issue_comment_count": row["issue_comment_count"],
        "bot_comment_count": row["bot_comment_count"],
        "eligible_report_count": len(valid),
    }


def validate_against_previous(rows: list[dict], baseline65: dict[int, dict],
                              add32: dict[int, dict], witnesses: set[int]) -> dict:
    num_to_row = {int(r["pr_number"]): r for r in rows}
    if len(num_to_row) != 97:
        raise ValueError("Expected 97 unique source-linked PRs")
    for num in witnesses:
        newer = num_to_row[num]
        prior = baseline65[num]
        if newer["report_presence"] != "confirmed":
            raise ValueError(f"Published 65-case witness lost report: {num}")
        earlier = prior["chosen_evidence"]
        if (newer["source_comment_id"] != earlier["comment_id"]
              or newer["source_body_sha256"] != earlier["body_sha256"]
              or newer["revision_relation"] != "head"):
            raise ValueError(f"Previously frozen 65-case evidence differs at PR {num}")
    for num, prior in add32.items():
        r = num_to_row[num]
        expected_presence = prior["observed_size_report"] == "yes"
        if (r["report_presence"] == "confirmed") != expected_presence:
            raise ValueError(f"Incremental 32-case report status differs at PR {num}")
        expected_id = int(prior["evidence_comment_id"]) if expected_presence else None
        if r["source_comment_id"] != expected_id or r["revision_relation"] != prior["source_sha_relation"]:
            raise ValueError(f"Incremental 32-case evidence identity differs at PR {num}")
        if expected_presence and (r["direction"] != prior["direction"] or r["size_value"] != prior["observed_size_value"]):
            raise ValueError(f"Incremental 32-case size value differs at PR {num}")
    d6 = sum(r["published_D6"] for r in rows)
    reports = sum(r["report_presence"] == "confirmed" for r in rows)
    negative = sum(not r["published_D6"] and r["report_presence"] == "confirmed" for r in rows)
    counts = {
        "sample": len(rows), "D6_positive": d6, "reports": reports,
        "D6_negative_with_report": negative, "no_thread_report": len(rows)-reports,
        "head": sum(r["revision_relation"] == "head" for r in rows),
        "listed_commit": sum(r["revision_relation"] == "listed_pr_commit" for r in rows),
        "unverified_commit": sum(r["revision_relation"] == "not_verified_current_commits" for r in rows),
    }
    if counts != REQUIRED_COUNTS:
        raise ValueError(f"Unexpected 97-PR result distribution: {counts}")
    return counts


def run_replay(snapshot_file: Path, json_out: Path = RESULT_JSON,
               csv_out: Path = RESULT_CSV, manifest_out: Path = MANIFEST) -> dict:
    inventory, baseline65, add32, witnesses = source_inputs()
    snapshot_bytes = snapshot_file.read_bytes()
    data = json.loads(snapshot_bytes)
    if (data.get("schema") != SCHEMA or data.get("source_repo") != REPO
            or data.get("cutoff_utc") != SOURCE_CUTOFF
            or data.get("source_label_sha256") != SOURCE_LABEL_SHA256):
        raise ValueError("Unrecognized or incompatible snapshot")
    by_id = {int(r["pr_number"]): r for r in data["prs"]}
    if len(by_id) != 97 or set(by_id) != {int(r["pr_number"]) for r in inventory}:
        raise ValueError("Snapshot population disagrees with frozen public inventory")
    for x in inventory:
        p = by_id[int(x["pr_number"])]
        if p["sample_arm"] != x["sample_arm"] or p["published_D6"] != (x["published_D6"] == "True"):
            raise ValueError("Frozen D6 labels or study arm drifted")
    rows = [assess_saved(by_id[int(x["pr_number"])]) for x in sorted(inventory, key=lambda x: int(x["pr_number"]))]
    counts = validate_against_previous(rows, baseline65, add32, witnesses)
    result = {
        "schema": SCHEMA, "source_repository": REPO,
        "study": "Rspack subset of 1,699 PRs from the pinned public Peng et al. label export",
        "snapshot_collected_at_utc": data["collected_at_utc"],
        "historical_source_cutoff_utc": SOURCE_CUTOFF,
        "historical_author_snapshot_available": False,
        "source_snapshot_sha256": digest(snapshot_bytes),
        "source_label_sha256": SOURCE_LABEL_SHA256,
        "counts": counts,
        "by_arm": {
            arm: {
                "n": sum(r["sample_arm"] == arm for r in rows),
                "D6_positive": sum(r["sample_arm"] == arm and r["published_D6"] for r in rows),
                "size_report_confirmed": sum(r["sample_arm"] == arm and r["report_presence"] == "confirmed" for r in rows),
            } for arm in ("agentic", "human_candidate")
        },
        "interpretation": "Observed automated byte-based size reporting in publicly retrievable PR issue discussions. Not a blinded semantic truth set, a causal improvement estimate, a historical August input replay, or a corrected full-cohort D6 prevalence.",
        "rows": rows,
    }
    write_json(json_out, result)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["pr_number","sample_arm","published_D6","report_presence","source_kind",
              "source_comment_id","source_url","source_created_at","source_updated_at",
              "source_body_sha256","size_value","direction","source_commit",
              "revision_relation","issue_comment_count","bot_comment_count","eligible_report_count"]
    with csv_out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    write_json(manifest_out, {
        "schema": SCHEMA, "source_snapshot_sha256": digest(snapshot_bytes),
        "source_label_sha256": SOURCE_LABEL_SHA256,
        "frozen_65_source_sha256": digest(PRIOR_65.read_bytes()),
        "incremental_32_source_sha256": digest(PRIOR_32.read_bytes()),
        "inventory_sha256": digest(INVENTORY.read_bytes()),
        "results_json_sha256": digest(json_out.read_bytes()),
        "results_csv_sha256": digest(csv_out.read_bytes()),
        "rows": len(rows), "counts": counts,
        "replay_command": "python3 code/rspack97_semantic_audit.py --offline",
    })
    return result


def collect(snapshot_file: Path, token: str | None) -> None:
    inventory, _, _, _ = source_inputs()
    entries = []
    for inv in sorted(inventory, key=lambda r: int(r["pr_number"])):
        entries.append(collect_one(inv, token))
        print(f"PR {inv['pr_number']} collected: {len(entries)}/97", flush=True)
    obj = {
        "schema": SCHEMA, "source_repo": REPO,
        "collected_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_utc": SOURCE_CUTOFF,
        "source_label_sha256": SOURCE_LABEL_SHA256,
        "scope": "Bot-authored issue-comment evidence. Positive cases retain qualifying raw bot reports only; negative cases retain all bot comments. No human-comment bodies.",
        "prs": entries,
    }
    write_json(snapshot_file, obj)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--collect", action="store_true", help="Collect a new public GitHub snapshot, then replay")
    group.add_argument("--offline", action="store_true", help="Replay only the committed frozen snapshot")
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    ap.add_argument("--json", type=Path, default=RESULT_JSON)
    ap.add_argument("--csv", type=Path, default=RESULT_CSV)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    args = ap.parse_args()
    if args.collect:
        collect(args.snapshot, os.environ.get("GITHUB_TOKEN"))
    result = run_replay(args.snapshot, args.json, args.csv, args.manifest)
    print(json.dumps({"source_sha256": result["source_snapshot_sha256"],
                      "counts": result["counts"], "by_arm": result["by_arm"]}, sort_keys=True))

if __name__ == "__main__":
    main()
