# Rspack 97-PR public semantic size-report audit

This audit covers all 97 Rspack PRs in the pinned Peng et al. 1,699-PR metric-layer sample. It measures **the presence of a concrete automated artifact-size report in a PR discussion**, using the source-linked rubric already applied to 65 boundary-dependent cases. The other 32 cases are independently checked and frozen in `evidence/rspack97_semantic_addendum_32.csv`.

## What to run

Requires Python 3.10+ and the included standard-library-only Python code.

**Offline, from the frozen evidence snapshot**:

    python3 -m unittest discover -s code -p 'test_rspack97_semantic.py' -v
    python3 code/rspack97_semantic_audit.py --offline

This validates the original public label CSV hash, the 97-row inventory, the original 65-case witness set, the other 32 cases, each retained report body digest, semantic parsing, pre-cutoff timestamps, PR-commit relationships, and summary counts. It regenerates:

- `results/rspack97_semantic_size_audit.csv` (one row per PR)
- `results/rspack97_semantic_size_audit.json` (results and scope)
- `results/rspack97_semantic_manifest.json` (SHA-256 digests of source and output files)

**Collect again from public GitHub**, explicitly producing a **new observation**:

    GITHUB_TOKEN=... python3 code/rspack97_semantic_audit.py --collect
    python3 code/rspack97_semantic_audit.py --offline

The optional token is an ordinary GitHub API token used for rate limiting; it is read from the environment and **never written** to output. All PR IDs come from the checked frozen inventory. The collection command fails closed if historical witness identities, record hashes, measurements, source timestamps, or publication controls change. A new observation may need a separate versioned audit if GitHub content has changed.

## Source evidence, with narrow retention

The frozen `evidence/rspack97_semantic_public_snapshot.json` contains PR IDs and current commit lists, source timestamps and digests, and **public bot issue-comment text** limited to qualifying size reports. For three PRs with no qualifying report, it includes all bot-comment bodies to permit offline verification of absence within that channel. Ordinary human issue-comment bodies, local paths, private author records, credentials, personal contact data and any private original-study snapshots are excluded. The current GitHub public records are the sole source of the retained comments.

All 94 report-positive cases contain a structured `Binary Size-limit` bot comment with a measured byte-based size. A concrete observed size (including an unchanged measurement) qualifies; a threshold, a memory measurement, a percentage without a size metric, or an anticipated improvement does not. The reporting decision is independent of the upstream D6 extractor.

The negative classification means **no qualifying automated report in the collected issue-thread channel**. It is neither proof that the PR never had artifact-size data elsewhere nor a verified negative ground-truth label. All reports are assessed against the *original source reference cutoff* of **August 27, 2026, 22:00 UTC** using both creation and last-edit timestamps.

## Frozen result and interpretation

| Published D6 | Observed automated byte-based size report | No qualifying report in inspected thread | Total |
| --- | ---: | ---: | ---: |
| Positive | 83 | 0 | 83 |
| Negative | 11 | 3 | 14 |
| Total | 94 | 3 | 97 |

Among 94 confirmed reports, 91 cite the currently retrieved head revision, two cite earlier PR-listed commits (#11320, #13975), and one (#14172) cites a source SHA not found in the currently listed PR commits. The last case is counted as a **report attached to the PR**, with revision attribution unresolved.

The separate 65-case comment-boundary experiment yields 65 detector-sensitive detections, and the 97-PR original-rule replay yields 18 within-comment detections. Those are **detector outcomes**. The 94 observed reports measure **actual report presence** in this repository. Do not treat the detector-specific +2.486 percentage point full-cohort sensitivity as an estimate of actual reporting prevalence or a causal difference between agentic and human-candidate PRs.

## Provenance and validity boundaries

- Public label source and fixed Git blob / file SHA-256: `SOURCE.md`
- Original rule and public code revision: `evidence/RSPACK_D6_COMMENT_PAIR_TRACE.md`
- Older, independent 65-case semantic presence baseline: `evidence/RSPACK65_SEMANTIC_SIZE_PRESENCE.md`
- Full fixed 97-PR source inventory: `evidence/rspack_97_source_inventory_20261122.csv`
- Additional 32-case witness IDs: `evidence/rspack97_semantic_addendum_32.csv`
- Full PR-level results and hashes: `results/rspack97_semantic_size_audit.*`

The August 2026 input snapshot used by the original authors is restricted. This audit uses publicly accessible GitHub evidence retrieved in November 2026 and freezes those observed source contents. The 97 PRs belong to one influential repository and were identified from the source study's published sample. The audit is a deterministic, inspectable source rubric; it is not blinded, external adjudication or build reproduction.

Re-running `--offline` needs no API, external package, or credential. Re-running `--collect` can generate a later GitHub snapshot, which should be treated as a new dated observation.
