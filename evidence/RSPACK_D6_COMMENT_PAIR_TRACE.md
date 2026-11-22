# Rspack D6 comment-pair trace

## Fixed inputs

- Original extractor: `PurdueDualityLab/EMSE-perf-pr-study` at `64432e0b6ed7791bbfa929c6c183fc76c75b5d58`
- Original source blobs: `metric_patterns.py` `31aaf5eb77b97be24cb4be359d1a30c862c2293e`; `extract_metrics.py` `cf5b93ff071a39a0e4b2d8a4fdb85a2059b80a86`
- Published D6 labels: `data/rq3_labels.csv`, Rspack metric-layer cohort of 97 PRs
- Comment records: public `web-infra-dev/rspack` issue-comment API, retrieved November 22, 2026 UTC

## Original-rule replay

The original extractor joined issue-comment bodies with a newline before applying its D6 matching rules. Running that same extraction against current public issue comments reproduces the 83 positive and 14 negative D6 labels across all 97 Rspack PRs.

Among the 83 positive PRs, 65 produce a D6 match from joined comments and zero matches when each comment is evaluated separately. Adding a 32-token separator between comments also removes those 65 detections.

## Direct source-pair reconstruction

The original extractor returns the normalized-text offsets of the D6 cue and quantitative expression. For each of the 65 boundary-dependent PRs, the tracing script maps both offsets to the original GitHub comment IDs. Exact equality between normalized complete comment text and joined individually normalized comments confirms the offset mapping in all 65 cases.

| Result | Count |
| --- | ---: |
| PRs with boundary-dependent D6 | 65 |
| Located D6 cue/quantity matches | 72 |
| PRs with one cross-comment match | 58 |
| PRs with two cross-comment matches | 7 |
| Exact comment-offset mappings | 65 / 65 |
| Matches crossing adjacent comments | 72 / 72 |
| Matches joining two `github-actions[bot]` comments | 72 / 72 |
| Earlier quantitative expression, later D6 cue | 72 / 72 |
| Two-comment input reproduces the D6 hit | 72 / 72 |
| Boundary-separated two-comment input retains a D6 hit | 0 / 72 |

### Paired comment categories

The table lists the source of the **quantitative expression** first and the source of the **D6 cue** second.

| Quantitative comment | Cue comment | Matches |
| --- | --- | ---: |
| Rsdoctor bundle-diff report | Binary Size-limit report | 33 |
| Binary Size-limit report | Rsdoctor bundle-diff report | 29 |
| Other benchmark report | Rsdoctor bundle-diff report | 8 |
| Other benchmark report | Binary Size-limit report | 2 |

The 72 source pairs have individually resolvable GitHub comment URLs, author accounts, creation timestamps, cue text, quantitative expression, original rule ID, and normalized token distance. These fields appear in [`rspack_65_comment_pairs.csv`](../results/rspack_65_comment_pairs.csv).

### Three concrete traces

**PR #12560.** A [Binary Size-limit comment](https://github.com/web-infra-dev/rspack/pull/12560#issuecomment-3691422326) reports `48.00MB`. Eleven seconds later, an [Rsdoctor comment](https://github.com/web-infra-dev/rspack/pull/12560#issuecomment-3691422493) introduces `Bundle Diff Analysis`. The original D6 rule links `48.00mb` to `bundle` across the comment boundary.

**PR #13024.** An [Rsdoctor report](https://github.com/web-infra-dev/rspack/pull/13024#issuecomment-3875970196) includes `984.2 KB`. A [Binary Size-limit report](https://github.com/web-infra-dev/rspack/pull/13024#issuecomment-3875972600) follows 41 seconds later. The D6 rule links `984.2 kb` to `binary size` in the subsequent comment.

**PR #13020.** An [automated benchmark comment](https://github.com/web-infra-dev/rspack/pull/13020#issuecomment-3875526990) contains `-4.25 %`; the subsequent [Rsdoctor comment](https://github.com/web-infra-dev/rspack/pull/13020#issuecomment-3875553407) contains `bundle`. These separate records form a D6 match. A second pair in the same PR links `2.2 mb` from that Rsdoctor comment to `binary size` in the [following Binary Size-limit comment](https://github.com/web-infra-dev/rspack/pull/13020#issuecomment-3875556044).

## Reproduction and interpretation

The script [`audit_rspack_65_comment_pairs.py`](../code/audit_rspack_65_comment_pairs.py) downloads the two original source files at the pinned commit, checks their Git blob hashes, loads the source study's D6 extraction function, and links its returned match positions to public comment IDs. The workflow [`rspack65-comment-pairs.yml`](../.github/workflows/rspack65-comment-pairs.yml) executes the script with read-only GitHub API access. The [offline integrity tests](../code/test_rspack_65_comment_pairs.py) cross-check the pair ledger, the 97-PR baseline, and the source study's published D6 labels.

The [`rspack_65_comment_pair_audit.json`](../results/rspack_65_comment_pair_audit.json) retains all 65 PR-level match records and pair-only controls. The [summary JSON](../results/rspack_65_comment_pair_summary.json) records group-level counts and the original source identifiers.

The result establishes a concrete processing mechanism in the **current public issue-comment corpus**: the extractor can associate a numerical measurement in one automated comment with a D6 cue in a different automated comment. Some matched numerical expressions come from benchmark reports that measure other quantities. The original study's archived collection snapshot and its additional evidence surfaces remain separate audit targets. The paper's published D6 labels and the observed presence of quantitative measurements retain their original definitions.
