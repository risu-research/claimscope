# Reproducing the ClaimScope software archive

## Scope and fixed evidence

This release contains the original source study's published labels and the
ClaimScope code and evidence required to reproduce its numerical claims without
model inference. The source labels and original metric-pattern code are pinned
to the original authors' Git revision
`64432e0b6ed7791bbfa929c6c183fc76c75b5d58`, with independent file
hash checks.

The 97-PR source study subset comprises 88 agentic and nine human-candidate
Rspack PRs. The 1,699-PR metric cohort comprises 858 agentic and 841
human-candidate records.

The archive has two distinct types of source material:

1. **Frozen author-published outputs:** the original public D6 labels, whose
   source CSV is SHA-256 checked, and the pinned original extractor code.
2. **Frozen ClaimScope public observations:** source-linked public GitHub bot
   reports observed November 22, 2026, minimal 72-match boundary excerpts,
   published commit references, and 476 public comment timestamps.

The original authors' private August 27, 2026 full-input snapshot is not in
this archive. A different public collection cannot authenticate its exact bytes
or any now-deleted comments.

## A clean offline replay

Requires Python 3.10 or newer, a POSIX shell and Python's standard library.
There is no dependency on a language-model API, GPU, private dataset, token,
or GitHub availability once the release archive is downloaded.

```bash
bash run_checks.sh
DEEP=1 bash run_checks.sh
```

The first command validates the original public label hash and replays
the cohort and sensitivity statistics. It runs deterministic integrity and
tamper tests, the full 97-PR reported-size source census, the 476-comment
timestamp audit and **all 72 cross-comment matches from 65 PRs using the
original pinned extractor**, and the publication preflight.

The second adds the complete ten-metric repository scan and stage-eight
repository resampling. Results appear in `build/`. Two frozen semantic
validation files under `results/` and the timestamp summary are regenerated
byte-identically; the CI compares their hashes before and after.

The focused independent commands are:

```bash
python3 code/replay_rspack65_boundary_witnesses.py --offline
python3 code/rspack97_semantic_audit.py --offline
python3 code/audit_rspack97_temporal.py --offline
python3 code/preflight_release.py
```

### How the 72 minimal witnesses are tested

`evidence/rspack65_boundary_witnesses_20261122.json` contains 72 source-linked
pairs from 65 PRs. Each pair stores the end of one public automated comment
and the beginning of the next. All source comment identifiers are checked
against the frozen public pair ledger. The full original content SHA-256s,
source URLs and commit identity are retained for auditing.

The two original MIT-licensed upstream source files are included under
`code/upstream_pinned/`; their Git blob SHA-1 digests are verified against
the original source before execution. For every pair, the matcher must
recognize the recorded cue and quantity when the excerpts are joined by a
newline. Neither excerpt evaluated independently, nor their
32-token-separated combination, may produce the original D6 match.

These excerpts preserve the tested source-boundary behavior with 72 minimal
verbatim witnesses, in place of archiving all bot, human, or PR discussion
text. The witness replay is a **November 2026 public-evidence experiment**.
It is distinct from a byte-identical reconstruction of the original August
full-input collection.

### Report presence and timing controls

`code/rspack97_semantic_audit.py --offline` independently parses one
selected qualifying byte-based size report for each of 94 Rspack PRs and
examines all retained automated negative-case evidence for three others.
It checks 65 pre-existing manual audit records and the 32-case addendum.
Bot-authored measurements are historical claims made in public PR threads;
their existence alone does not verify the underlying binary's actual size.

`code/audit_rspack97_temporal.py --offline` verifies the complete 476-row
public metadata ledger, including 437 bot and 39 other comments. Every
currently visible comment was created and last updated before the source
study's August 27 reference timestamp. The latest recorded update is June 2,
2026. Timestamp checks do not prove absence of deleted comments or byte
identity with the original authors' private files.

## Live source re-collection (separate observation)

Only if a fresh source observation is desired, use public GitHub API access:

```bash
python3 code/audit_rspack_97_comment_boundaries.py
python3 code/audit_rspack_65_comment_pairs.py
python3 code/replay_rspack65_boundary_witnesses.py --collect \
  --output build/latest_public_boundary_witnesses.json
python3 code/rspack97_semantic_audit.py --collect \
  --snapshot build/latest_semantic_snapshot.json \
  --json build/latest_semantic_results.json \
  --csv build/latest_semantic_results.csv \
  --manifest build/latest_semantic_manifest.json
```

An optional `GITHUB_TOKEN` increases GitHub's API rate limit. Keep it in the
environment, never in a repository file or release. The live-source scripts
validate input identities and source hashes and will halt if current public
records no longer satisfy frozen historical counts. A changed later corpus
should receive its own version and must never overwrite a cited frozen release.

## Publication integrity and third-party attribution

The release publication gate is `python3 code/preflight_release.py`. It
checks source labels, Zenodo and citation metadata, evidence populations,
timestamp hashes, selected bot-text minimization, and high-confidence secret
patterns across the release checkout. Third-party material is governed by
`THIRD_PARTY_NOTICES.md`, and the upstream original MIT license is in
`data/UPSTREAM_LICENSE`.

The GitHub Actions main-branch check has `contents: read` permission and
runs the same frozen replay and preflight. The one-time workflow used to
collect the 72 boundary excerpts is deliberately excluded from the release.

## Interpretation

The original D6 flag is a result of deterministic text extraction, a
distinct outcome from observing a concrete size measurement in a bot report.
Changing the 65 boundary-dependent flags lowers the published 1,699-PR
D6 gap from 8.885 to 2.486 percentage points, with the other 1,634 source
flags fixed. All 65 affected PRs still contain real size reports. Thus the
change measures sensitivity of a detector to record assembly, not corrected
prevalence of genuine reporting or performance causality.
