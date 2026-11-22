# Rspack 65: independent-source D6 retention

## Fixed inputs

The 65 Rspack PRs come from the verified 72-pair witness ledger, with 60 `agentic` and five `human_candidate` observations. The published label export contains 1,699 analytic PRs. The upstream metric extractor is pinned at commit `64432e0b6ed7791bbfa929c6c183fc76c75b5d58`, with Git blob hashes checked before execution.

The evidence run retrieved public GitHub records on November 22, 2026 UTC. The source code replays the upstream `extract_dimensions()` function and its quantitative-claim rules.

## Current public evidence

| Channel | Retrieved source records | PRs with a D6 match |
| --- | ---: | ---: |
| PR title and description | 65 | 0 |
| Individual issue comments | 318 | 0 |
| Inline review comments | 99 | 0 |
| Commit messages | 236 | 0 |
| GitHub Actions workflow-run names | 439 | 0 |
| Changed-file patches | 389 | 0 |
| Supplementary review-body records | 54 | 0 |

The issue-comment audit preserves each comment's boundary. The other five upstream source channels retain the source-level concatenation used in `run_current.py`. A second check processes every retrieved record individually. Both approaches return zero retained D6 positives among the 65 PRs. All 389 changed-file patches were available through the public files API.

The archived [PR-level evidence JSON](../results/rspack65_other_source_replay.json) contains per-source match counts, PR URLs, current head SHAs, collection coverage, and traceable evidence links for positive matches. The [65-row table](../results/rspack65_other_source_replay.csv) records every channel's result.

## Full-cohort contrast

| Measure | Published D6 labels | Current public evidence with issue-comment boundaries |
| --- | ---: | ---: |
| Agentic | 115 / 858 | 55 / 858 |
| Human-candidate | 38 / 841 | 33 / 841 |
| Agentic minus human-candidate | +8.8848 pp | +2.4864 pp |

The change is a 72.0157% reduction in the observed contrast. The other 1,634 published labels and both group denominators remain fixed. The [full-cohort integration report](../results/rspack65_observed_channel_sensitivity.json) preserves this calculation with audited source checksums.

## Provenance and interpretation

The original source study's August 2026 parquet evidence snapshot is absent from its public Git tree. The current API results cannot recover deleted comments, prior revisions of PR bodies, historical workflow-run naming, or earlier patch variants. Workflow names here come from runs associated with each PR's currently returned head SHA; the original snapshot's run names remain unverified. All issue comments retrieved in this run had creation and update timestamps before the original snapshot reference date.

The result measures **D6 extraction under current public evidence and preserved issue-comment boundaries**. Its evidence is stronger than the earlier hypothetical 65-flag sensitivity because all five other source channels were actually tested. Historical classification claims remain conditional on the missing original snapshot.

## Reproduction

```bash
python3 code/audit_rspack65_other_sources.py --max-workers 5
python3 code/sensitivity_rspack65_observed_channels.py
python3 -m unittest discover -s code -p 'test_rspack65_other_sources.py'
python3 -m unittest discover -s code -p 'test_sensitivity_rspack65_observed_channels.py'
```

The collection requires public GitHub API access. `GITHUB_TOKEN` raises the API request quota. Offline integration requires the included frozen label CSV and source-replay JSON. The repository remains in research revision pending final source and snapshot checks.
