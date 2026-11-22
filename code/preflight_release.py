#!/usr/bin/env python3
"""Read-only, standard-library publication preflight for the ClaimScope archive.

Checks pinned upstream bytes, complete frozen evidence, minimum citation/Zenodo
metadata, accidental secrets and non-public paths. Run before any immutable
software archive. This is a conservative guard, not a general secret scanner.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED={
    "LICENSE","CITATION.cff",".zenodo.json","THIRD_PARTY_NOTICES.md",
    "data/UPSTREAM_LICENSE","data/rq3_labels.csv",
    "code/upstream_pinned/metric_patterns.py",
    "code/upstream_pinned/extract_metrics.py",
    "code/replay_rspack65_boundary_witnesses.py",
    "evidence/rspack65_boundary_witnesses_20261122.json",
    "evidence/rspack97_semantic_public_snapshot.json",
    "evidence/rspack97_issue_comment_timestamps_20261122.csv",
    "results/rspack97_semantic_manifest.json",
    "results/rspack97_temporal_provenance_20261122.json",
}
FILE_FORBIDDEN=(
    re.compile(r"(?i)(?:^|/)(?:\.env(?:\.|$)|secrets?\.json$|credentials?\.txt$|id_rsa$|private[_ -]submission)"),
    re.compile(r"(?i)(?:^|/)(?:\.venv/|\.git/|__pycache__/|build/|dist/)"),
)
TEXT_SECRET_RULES=(
    re.compile(rb"\bghp_[a-zA-Z0-9]{30,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)[a-z]:\\users\\[a-z0-9_.-]+"),
    re.compile(rb"(?i)[a-z0-9_.+-]+@(?:hotmail|gmail|outlook)\.com"),
)
SOURCE_LABEL_SHA256="c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9"

def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
    missing=sorted(p for p in REQUIRED if not (ROOT/p).is_file())
    if missing:raise ValueError(f"Release inputs missing: {missing}")
    if sha((ROOT/"data/rq3_labels.csv").read_bytes())!=SOURCE_LABEL_SHA256:
        raise ValueError("Published source label bytes changed")
    zenodo=json.loads((ROOT/".zenodo.json").read_text(encoding="utf8"))
    if (zenodo.get("upload_type")!="software" or
        zenodo.get("title","").split(":")[0]!="ClaimScope" or
        zenodo.get("license","").lower()!="mit" or
        zenodo.get("creators")!=[{"name":"Lee, Moon Hwan","affiliation":"RISU Institute"}]):
        raise ValueError("Zenodo metadata incomplete or changed")
    cff=(ROOT/"CITATION.cff").read_text(encoding="utf8")
    for marker in ("cff-version: 1.2.0","family-names: Lee",
                   "given-names: Moon Hwan","type: software",
                   "version: 1.0.0","license: MIT"):
        if marker not in cff:raise ValueError(f"Missing citation metadata: {marker}")
    if (ROOT/"LICENSE").read_text(encoding="utf8").splitlines()[0]!="MIT License":
        raise ValueError("Software license missing or unexpected")
    temp=(ROOT/"results/rspack97_temporal_provenance_20261122.json")
    tem=json.loads(temp.read_text(encoding="utf8"))
    if tem["counts"]!={"prs":97,"comments":476,"bot_comments":437,
            "human_comments":39,"late_created":0,"late_updated":0}:
        raise ValueError("Temporal provenance changed")
    if sha((ROOT/"evidence/rspack97_issue_comment_timestamps_20261122.csv").read_bytes())!=tem["ledger_sha256"]:
        raise ValueError("Frozen timestamp ledger digest changed")
    witness=json.loads((ROOT/"evidence/rspack65_boundary_witnesses_20261122.json").read_text(encoding="utf8"))
    if len(witness.get("witnesses",[]))!=72 or len({r["pr_number"] for r in witness["witnesses"]})!=65:
        raise ValueError("Frozen boundary witness population changed")
    snapshot=json.loads((ROOT/"evidence/rspack97_semantic_public_snapshot.json").read_text(encoding="utf8"))
    if len(snapshot.get("prs",[]))!=97:
        raise ValueError("Semantic evidence cohort changed")
    if any("body" in meta for r in snapshot["prs"] for meta in r["other_bot_comment_metadata"]):
        raise ValueError("Extra nonselected bot text retained")
    if any("human_comment_bodies" in r or "human_comments" in r for r in snapshot["prs"]):
        raise ValueError("Human discussion body unexpectedly retained")
    skip={".git","build","dist",".venv","__pycache__"}
    checked=[]
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in skip for part in p.relative_to(ROOT).parts):
            continue
        name=p.relative_to(ROOT).as_posix()
        if any(rule.search(name) for rule in FILE_FORBIDDEN):
            raise ValueError(f"Nonpublic path in release: {name}")
        if p.stat().st_size>2_000_000:raise ValueError(f"Unexpected oversized artifact: {name}")
        raw=p.read_bytes()
        if b"\0" in raw:raise ValueError(f"Unexpected binary artifact: {name}")
        if any(rule.search(raw) for rule in TEXT_SECRET_RULES):
            raise ValueError(f"Potential credential or private identifier: {name}")
        checked.append(name)
    print(json.dumps({"status":"PASS","files_scanned":len(checked),
        "label_sha256":SOURCE_LABEL_SHA256,
        "temporal_comments":476,"semantic_prs":97,
        "boundary_pairs":72,"boundary_prs":65,
        "zenodo_metadata":"complete","private_secret_high_confidence_matches":0},
        sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
