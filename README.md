# ClaimScope

Reproducible repository-level reanalysis of artifact-size reporting in agentic pull requests.

The study reanalyzes the public D6 labels released by Peng et al., *How Do Coding Agents Optimize Software and Report Performance Validation?* The primary sample contains 1,699 pull requests across 440 repositories, drawn from the original compact RQ3 label export. The source study reports this metric under journal RQ4.

## Reproduce

Python 3.10+ and Bash. The analysis uses the Python standard library.

```bash
bash run_checks.sh
DEEP=1 bash run_checks.sh
```

The first command checks the source hash, replays D6 counts, runs the offline integrity tests, and regenerates Stage 5, Stage 6, and Rspack boundary-sensitivity results. The second command adds the ten-metric repository influence scan and Stage 8 decomposition with fixed-seed repository resampling. Generated files appear in `build/`.

The repository includes the pinned `data/rq3_labels.csv` for offline execution. To obtain the source directly from the original project:

```bash
python3 code/replay_public.py --download --cache data/rq3_labels.csv --output build/observed_replay.json
```

## Core results

| Measurement | Value |
| --- | ---: |
| D6 agentic | 115 / 858 (13.403%) |
| D6 human-candidate | 38 / 841 (4.518%) |
| Pooled difference | +8.885 percentage points |
| Rspack sample | 88 agentic; 9 human-candidate |
| D6 detections from Rspack | 76 agentic; 7 human-candidate |
| Difference after removing Rspack | +1.339 percentage points |
| Symmetric two-stratum composition component | +7.135 percentage points (80.310% of pooled difference) |

`human_candidate` is the source dataset's sample-arm label. D6 records the source study's extraction flag for quantitative artifact-size reporting. Cluster resampling measures sensitivity to repository composition in this observed sample.

## Files

- `code/replay_public.py`: checked source replay and D6 certificate
- `code/claimscope_stage5.py`: unit, category, evidence-surface, and repository checks
- `code/claimscope_stage6.py`: repository influence certificate and shared-repository analysis
- `code/stage8_audit.py`: two-stratum decomposition, ten dimensions, repository resampling
- `code/all_metric_repo_influence.py`: 440 repositories × 10 metric flags
- `code/test_stage*.py`: 39 analysis-contract tests
- `code/sensitivity_rspack65.py`: 65-record source-boundary sensitivity across all 1,699 analytic PRs
- `results/`: frozen baseline and boundary-sensitivity outputs
- `evidence/`: source inventory, original-rule replay, and comment-boundary audit

## Scope

The included CSV supports exact recomputation of the released labels and repository comparisons. Source-text spans and the historical comment snapshots used by Peng et al. remain outside the compact export. The comment checks in `evidence/` capture a separate inspection of selected public PR discussions.

Source identity, hashes, field definitions, and attribution are recorded in [`SOURCE.md`](SOURCE.md).

Artifact status: active research revision. Versioned archival release and DOI will follow the final experiments.

## Rspack source inventory

The [97-PR evidence ledger](evidence/rspack_97_source_inventory_20261122.csv) records GitHub creator accounts, issue/review comment counts, source URLs, and the source study's D6 labels. A `Binary Size-limit` bot comment appears in 94 PRs, including 83 D6-positive and 11 D6-negative records. The [inventory protocol](evidence/README.md) defines these counts and their observation window.

```bash
python3 code/rspack_source_inventory.py --max-prs 5
```

The full source-inventory collection uses public GitHub API endpoints and an optional `GITHUB_TOKEN` to increase the API request quota. The original-rule replay and comment-boundary results are documented in [Rspack D6 evidence audit](evidence/RSPACK_D6_EVIDENCE_AUDIT.md).

## Original-rule replay on Rspack comments

The pinned upstream extractor at commit `64432e0b6ed7791bbfa929c6c183fc76c75b5d58` was executed against November 22, 2026 UTC public GitHub issue comments for all 97 Rspack PRs. The concatenated-comment replay matched all 97 released D6 labels. Of 83 D6-positive PRs, 18 produced a D6 match within at least one individual comment. The other 65 produced D6 only when comment bodies were concatenated without a boundary marker.

All 83 positive matches also appeared in the concatenated bot-comment layer. In the 11 published D6-negative PRs with a `Binary Size-limit` bot comment, the nearest D6 cue-to-quantity distances measured 19–23 tokens against the original 12-token threshold. Removing the `Comparing` line changed all 11 bot-comment replay results to D6-positive.

- [Per-PR comment-boundary results](results/rspack_97_comment_boundary_audit.csv)
- [Full-cohort counts and provenance](results/rspack_97_comment_boundary_summary.json)
- [Eleven-case rule diagnostics](results/rspack_11_d6_rule_summary.csv)
- [Audit protocol and interpretation](evidence/RSPACK_D6_EVIDENCE_AUDIT.md)
- [Executable 97-PR source audit](code/audit_rspack_97_comment_boundaries.py)

The audit applies the exact pinned original matching function to currently accessible public comments. The source study's archived evidence snapshot, independent source-specific matches, and CI workflow metadata remain separate replication targets.

## Original-match comment pair trace

The 65 Rspack PRs with boundary-dependent D6 labels contain 72 matched cue/quantity pairs. All 72 link two adjacent `github-actions[bot]` issue comments. Each pair independently produces a D6 match when its two comment bodies are joined. A 32-token boundary separator removes every pair's D6 match.

The [65-PR pair ledger](results/rspack_65_comment_pairs.csv) records the source GitHub comment IDs, URLs, bot accounts, timestamps, matched expressions, and upstream rule IDs. The [source-level audit](evidence/RSPACK_D6_COMMENT_PAIR_TRACE.md) describes the direct traces and the exact original-code replay. The [trace script](code/audit_rspack_65_comment_pairs.py) regenerates the records using current public GitHub comments.

The trace uses public issue comments retrieved on November 22, 2026 UTC. The historical evidence snapshot and additional PR evidence channels remain separate audit targets.

## Full-cohort D6 boundary sensitivity

The 65 source-linked Rspack PRs contain 60 `agentic` and five `human_candidate` observations. The published 1,699-PR D6 contrast is +8.885 percentage points. A controlled scenario setting those 65 D6 flags to false, with all other published labels and denominators fixed, produces +2.486 percentage points, a 72.016% attenuation.

| Sensitivity operation | D6 contrast |
| --- | ---: |
| Published 1,699-PR cohort | +8.885 pp |
| 65 Rspack boundary-dependent flags set to false | +2.486 pp |
| 65 affected PRs excluded from the cohort | +2.945 pp |
| Entire Rspack repository excluded | +1.339 pp |

The [full-cohort report](evidence/RSPACK65_FULLCOHORT_SENSITIVITY.md) records the exact denominators, accounting decomposition, 12,000-draw paired repository resampling, and conditional retention range for independent D6 evidence channels. The [frozen sensitivity JSON](results/rspack_65_fullcohort_sensitivity.json) and [scenario table](results/rspack_65_fullcohort_scenarios.csv) can be regenerated with `code/sensitivity_rspack65.py` or `bash run_checks.sh`.

The 65-flag intervention is a local sensitivity scenario. Full historical re-extraction additionally requires source-specific matches from the original collection snapshot.

## Rspack 65: other evidence channels

The original pinned D6 extractor was replayed against current public GitHub evidence for the 65 boundary-dependent Rspack PRs. Individual issue comments, PR descriptions, inline reviews, commit messages, workflow-run names, and code patches yielded **zero retained D6 detections**. The run checked 318 issue comments, 99 inline reviews, 236 commits, 439 workflow runs, and 389 available patches.

With issue-comment boundaries preserved, the observed 65-case replay produces the same +2.486 percentage-point local scenario across the original 1,699 PRs. The original 1,634 other labels remain fixed. The [source-retention audit](evidence/RSPACK65_OTHER_SOURCE_RETENTION.md) records the method and historical-snapshot scope.

- [65-PR source-by-source evidence table](results/rspack65_other_source_replay.csv)
- [65-PR source evidence and provenance](results/rspack65_other_source_replay.json)
- [1,699-PR recalculation](results/rspack65_observed_channel_sensitivity.json)
- [Public API source replay](code/audit_rspack65_other_sources.py)
- [Offline full-cohort integration](code/sensitivity_rspack65_observed_channels.py)

The comparison is a controlled re-extraction using current public GitHub records. The original August 2026 evidence snapshot remains a separate archival verification target.

## Semantic size-report presence in the 65 boundary-dependent PRs

A separate, source-based audit tested whether each Rspack PR contains a concrete observed artifact-size measurement. **All 65 contain a `Binary Size-limit` report tied to the current PR head:** 37 report increases, 23 decreases, and five unchanged sizes. All 65 also contain Rsdoctor project-size tables. The audit rule checks numeric byte-based observations and source revisions, independently of the upstream D6 regex.

This is a critical distinction for interpreting the earlier +2.486 pp boundary-preserving scenario: that number measures **D6 extractor sensitivity**, whereas the 65 PRs have genuine reported size measurements in their public discussion threads. [Decision rule and interpretation](evidence/RSPACK65_SEMANTIC_SIZE_PRESENCE.md), [65-row source ledger](results/rspack65_semantic_size_audit.csv), and [replay code](code/semantic_rspack65_size.py) document the audit. The original historical private snapshot remains a separate replication target.

## Complete Rspack 97-PR semantic size-report audit

The frozen source-based audit covers **all 97 Rspack PRs**, beyond the 65 boundary-dependent positive cases. A structured byte-based size measurement appears in **94/97** inspected public PR discussions, including **83/83** published D6-positive PRs and **11/14** published D6-negative PRs. Three discussions lack a qualifying automated size report in the inspected channel.

Of the 94 qualifying reports, 91 refer to the current PR head, two to earlier PR-listed commits, and one to a source commit that could not be verified against the current PR commit list. These are measurements reported in public discussion threads; their presence is separate from D6 extraction and from the causal effects of a PR.

The frozen audit keeps one qualifying public bot report per positive PR, all bot-comment evidence for the three negative PRs, and minimal identity/digest metadata for other bot comments. No human discussion bodies or private source snapshots are retained.

Reproduce the full quantitative analysis and 97-PR semantic audit offline with:

    bash run_checks.sh

Or replay just the 97-PR evidence without a network connection:

    python3 code/rspack97_semantic_audit.py --offline

See the [97-PR reproduction protocol](evidence/RSPACK97_SEMANTIC_REPRODUCTION.md), [per-PR evidence table](results/rspack97_semantic_size_audit.csv), [source snapshot](evidence/rspack97_semantic_public_snapshot.json), [integrity manifest](results/rspack97_semantic_manifest.json), and [source-audit code](code/rspack97_semantic_audit.py). Regenerating the dated source collection requires public GitHub API access, which is a separate mode of execution.

## Temporal provenance of the 97 public Rspack issue threads

The original metric extraction records an August 27, 2026 **22:00:14 UTC** evidence snapshot. On November 22, 2026 we independently enumerated every currently visible issue-thread comment in the same 97 Rspack PRs.

| Verified temporal property | Result |
| --- | ---: |
| PR threads | **97** |
| Public issue comments | **476** |
| Bot comments | 437 |
| Other comments | 39 |
| Comments created after reference snapshot | **0** |
| Comments last updated after reference snapshot | **0** |
| Latest recorded comment update | **2026-06-02 07:58:45 UTC** |

The [476-row minimal metadata ledger](evidence/rspack97_issue_comment_timestamps_20261122.csv) records only PR ID, public GitHub comment ID, creation and last-update UTC timestamps, and a bot indicator. It contains **no comment text or account names**. [Its reproducibility summary](results/rspack97_temporal_provenance_20261122.json) locks the original study's reference time, source-inventory SHA-256, row counts, latest timestamp, and ledger digest.

To reproduce these timestamp checks **without the network**, run:

    python3 code/audit_rspack97_temporal.py --offline

The existing `bash run_checks.sh` also runs this check automatically. To fetch a **new** public observation rather than replay the frozen ledger:

    python3 code/audit_rspack97_temporal.py --collect

Live collection uses a GitHub API token only if provided through the environment. Changes in comment populations, timestamps, or the frozen sample fail validation. The timestamp audit supports the claim that the **currently visible** comments all predate the August snapshot. It cannot establish the exact earlier content bytes, restore deleted comments, or verify the historical state of other input channels.


## Archival reproduction and software citation

The publication-ready release includes a [full offline reproduction guide](REPRODUCE_RELEASE.md),
a [minimal 72-match boundary witness corpus](evidence/rspack65_boundary_witnesses_20261122.json),
and byte-identical, MIT-licensed [original source detector files](code/upstream_pinned/).
All 72 cross-comment cue/quantity matches across 65 Rspack PRs are now independently
re-executable offline using the original rule. The remaining full-current-GitHub
source replay is explicitly a separate online observation. No original private
August 2026 evidence snapshot is claimed or archived.

Run the full public source and security preflight with:

    python3 code/preflight_release.py
    python3 code/replay_rspack65_boundary_witnesses.py --offline

The root [CITATION.cff](CITATION.cff) and [Zenodo metadata](.zenodo.json) identify
this artifact as research software by Moon Hwan Lee, RISU Institute. The
[third-party source notice](THIRD_PARTY_NOTICES.md) separates ClaimScope code
rights from the original study's labels and Rspack's public automated reports.

A DOI is only authoritative after the corresponding GitHub release has been
successfully archived by Zenodo. The source code and reproducibility content
are available without a DOI.
