# Rspack D6 evidence audit

## Inputs and source code

- Upstream study: `PurdueDualityLab/EMSE-perf-pr-study`, commit `64432e0b6ed7791bbfa929c6c183fc76c75b5d58`
- Original files: `analysis/rq3_pattern_and_validation/metric_patterns.py` and `extract_metrics.py`
- Original Git blob SHAs: `31aaf5eb77b97be24cb4be359d1a30c862c2293e`, `cf5b93ff071a39a0e4b2d8a4fdb85a2059b80a86`
- Rspack population: 97 PRs, 88 agentic and 9 human-candidate; published D6-positive 83, D6-negative 14
- GitHub comments observed on November 22, 2026 UTC, retaining their API order

The audit executes the upstream function definitions and the upstream pattern definitions after verifying their Git blob SHAs. The original matcher uses a 12-token cue-to-quantity window. The original extractor concatenates the issue-comment bodies for each PR with newline separators.

## Eleven published-negative cases

Eleven published D6-negative PRs contain a GitHub Actions `Binary Size-limit` comment with a quantitative size measurement. Their nearest D6 cue-to-quantity distances in the normalized binary-size comment are 19–23 tokens. The original 12-token extractor returns D6-negative for all eleven. Removing the `Comparing ...` line from each bot comment changes all eleven to D6-positive. Increasing the cue window to 48 tokens also returns D6-positive for all eleven. The original measurement text remains intact in the comparison-line experiment.

The [13-row summary](../results/rspack_11_d6_rule_summary.csv) includes eleven published negatives and two published-positive controls. Source URLs lead to the original comments. The [full 11-case replay](../results/rspack_11_exact_extractor.json) and [rule diagnostics](../results/rspack_11_rule_diagnostics.json) record source-specific results and match offsets.

## All 97 PRs: comment-boundary test

| Original public D6 classification | PRs | Concatenated issue comments | Separate issue comments | 32-token boundary markers |
| --- | ---: | ---: | ---: | ---: |
| Positive | 83 | 83 | 18 | 18 |
| Negative | 14 | 0 | 0 | 0 |

Of 83 published positives, 65 depend on cross-comment concatenation on the currently accessible issue-comment surface. In the agentic group, 60 of 76 positives depend on the boundary. In the human-candidate group, 5 of 7 positives depend on the boundary.

The observation set contains 476 issue-thread comments, comprising 437 bot comments and 39 comments from other accounts. Running the same extraction function on the concatenated bot comments reproduces all 83 positive labels. Independent evaluation of each comment returns 18 positives.

The [97-PR results](../results/rspack_97_comment_boundary_audit.csv) and [summary](../results/rspack_97_comment_boundary_summary.json) record every classification. The [executable audit](../code/audit_rspack_97_comment_boundaries.py) fetches each PR's public comments, verifies the original extractor's source hashes, and calculates all three comment-boundary conditions.

## Interpretation and replication scope

The observed result identifies a source-processing mechanism: concatenation allows a metric cue in one comment to match a number in a neighboring comment. PR #13010 is a direct case: the `48.61MB` measurement in a binary-size comment is matched to `bundle` in the subsequent Rsdoctor comment.

The source-study D6 labels were produced from an earlier evidence snapshot containing PR descriptions, issue comments, review comments, commits, workflow names, and file patches. This audit isolates the comment channel in the public GitHub record observed on November 22, 2026. The original snapshot and source-specific match ledger are needed to attribute each original label exclusively to the cross-comment mechanism.

The separator and comment-removal tests are controlled changes to the text supplied to the original code. The observed D6 labels remain unchanged in the source CSV. The numerical sensitivity estimates reported here belong to the public comment-surface replay.

## Execute

The public repository includes GitHub Actions workflows `rspack-11-exact-audit.yml`, `rspack-positive-controls.yml`, and `rspack97-comment-boundaries.yml`. Each downloads and hash-verifies the two pinned upstream Python sources before running the original extractor. The workflows upload machine-readable replay outputs as Actions artifacts.

Execution uses GitHub's public API and a read-only `GITHUB_TOKEN` to stay within request quotas. The cached compact source labels in `data/rq3_labels.csv` anchor the PR identities and original classifications.
