# ClaimScope

Reproducible repository-level reanalysis of artifact-size reporting in agentic pull requests.

The study reanalyzes the public D6 labels released by Peng et al., *How Do Coding Agents Optimize Software and Report Performance Validation?* The primary sample contains 1,699 pull requests across 440 repositories, drawn from the original compact RQ3 label export. The source study reports this metric under journal RQ4.

## Reproduce

Python 3.10+ and Bash. The analysis uses the Python standard library.

```bash
bash run_checks.sh
DEEP=1 bash run_checks.sh
```

The first command checks the source hash, replays the D6 counts, runs 39 tests, and regenerates the Stage 5 and Stage 6 results. The second command adds the ten-metric repository influence scan and Stage 8 decomposition with fixed-seed repository resampling. Generated files appear in `build/`.

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
- `results/`: frozen baseline JSON outputs
- `evidence/`: selected public PR-comment checks dated October 10, 2026

## Scope

The included CSV supports exact recomputation of the released labels and repository comparisons. Source-text spans and the historical comment snapshots used by Peng et al. remain outside the compact export. The comment checks in `evidence/` capture a separate inspection of selected public PR discussions.

Source identity, hashes, field definitions, and attribution are recorded in [`SOURCE.md`](SOURCE.md).

Artifact status: active research revision. Versioned archival release and DOI will follow the final experiments.
