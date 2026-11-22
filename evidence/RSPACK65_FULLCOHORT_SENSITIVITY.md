# D6 boundary sensitivity across 1,699 pull requests

## Source-linked population

The published `rq3_labels.csv` contains 2,081 records. Applying its `in_metric_layer=True` gate selects 1,699 PRs from 440 repositories, with 858 `agentic` and 841 `human_candidate` records. The published D6 flag counts are 115 and 38, respectively.

The preceding Rspack audit identified 65 PRs with an original-rule D6 match spanning two adjacent `github-actions[bot]` issue comments. Their 72 cue/quantity matches carry stable source-comment IDs and separate-comment controls in [`rspack_65_comment_pairs.csv`](../results/rspack_65_comment_pairs.csv). The affected PRs comprise 60 `agentic` and five `human_candidate` records. Every affected PR has a published positive D6 flag and D6 without code-diff evidence.

## Three controlled sensitivity operations

| Scope | Agentic D6 | Human-candidate D6 | Agentic minus human-candidate, pp |
| --- | ---: | ---: | ---: |
| Published, all 1,699 PRs | 115/858 (13.403%) | 38/841 (4.518%) | +8.885 |
| Set the 65 boundary-dependent D6 flags to false | 55/858 (6.410%) | 33/841 (3.924%) | +2.486 |
| Exclude the same 65 PRs from the sample | 55/798 (6.892%) | 33/836 (3.947%) | +2.945 |
| Exclude Rspack's 97 PRs | 39/770 (5.065%) | 31/832 (3.726%) | +1.339 |

The 65-flag intervention reduces the published pooled D6 difference by **6.398 percentage points**, or **72.016% of its original value**. The same 65 records account for 3.826% of the analytic PRs and 42.484% of all 153 published positive D6 flags.

The intervention holds the remaining 1,634 source labels fixed and retains both original group denominators. The exclusion sensitivity removes the 65 PRs and recalculates denominators. The repository exclusion supplies the established sampling-influence comparison.

Within Rspack, the published counts are 76/88 versus 7/9. The 65-flag intervention gives 16/88 versus 2/9. The within-Rspack contrast changes from +8.586 to -4.040 percentage points. All 65 adjusted records share Rspack repository ID `476642602`.

## Repository composition and sampling checks

A symmetric two-stratum Kitagawa accounting calculation splits the pooled contrast between Rspack and the other 439 repositories.

| Accounting component | Published | 65-flag intervention |
| --- | ---: | ---: |
| Repository-composition component | +7.135 pp | +1.452 pp |
| Within-stratum rate component | +1.749 pp | +1.034 pp |
| Sum | +8.885 pp | +2.486 pp |

Each decomposition exactly reproduces its pooled contrast. These are accounting components of observed differences.

Further checks:

- Pooled optimization-pattern standardization: **+8.602 pp → +2.351 pp**.
- Equal-weight difference across 84 repositories represented in both groups: **-0.152 pp → -0.303 pp**.
- Joint repository-cluster bootstrap, 12,000 paired draws and seed `20261122`: published contrast 95% descriptive percentile range **[-1.820, +22.464] pp**; 65-flag intervention **[-2.305, +6.359] pp**.
- The paired bootstrap difference has a 95% percentile range **[-17.549, 0.000] pp**. Draws omitting Rspack yield an unchanged contrast for the two scenarios.

The cluster-resampling distributions describe sensitivity to the observed repository mix. A population probability sample or causal design is outside these calculations.

## Unresolved independent evidence channels

The original extractor also read PR descriptions, review comments, commit messages, CI metadata and code changes. The publicly distributed compact labels omit historical source-by-source D6 matches. Current public issue-comment replays identify the boundary mechanism; the original August 27, 2026 evidence snapshot remains a separate retrieval target.

If any of the 65 boundary-dependent positives also has an independent qualifying match in another source, its D6 flag would remain positive in a full boundary-aware extraction. Let `a` be the number of independently supported positives among the 60 affected `agentic` records and `h` among the five affected `human_candidate` records. Holding the remaining 1,634 original labels fixed, the possible contrasts are

`100 × ((55 + a)/858 - (33 + h)/841)` with `0 <= a <= 60` and `0 <= h <= 5`.

All 366 integer combinations yield a positive observed contrast, ranging from **+1.892 pp** (`a=0, h=5`) to **+9.479 pp** (`a=60, h=0`). This is a conditional arithmetic range for the explicitly restricted 65-record change. It is separate from the repository bootstrap range and from any full-corpus replacement label set.

## Reproduce

The analysis uses the original compact-label CSV, the fixed 72-pair source ledger and the 97-PR comment-boundary audit. The script checks source-file hashes, each affected PR identity and arm, original D6 flags, matching pairs and 97-PR alignment before calculating results.

```bash
python3 code/sensitivity_rspack65.py \
  --labels data/rq3_labels.csv \
  --pairs results/rspack_65_comment_pairs.csv \
  --boundary results/rspack_97_comment_boundary_audit.csv \
  --output build/rspack65_sensitivity.json \
  --table build/rspack65_scenario_table.csv \
  --bootstrap 12000 --seed 20261122
```

Frozen outputs: [`rspack_65_fullcohort_sensitivity.json`](../results/rspack_65_fullcohort_sensitivity.json) and [`rspack_65_fullcohort_scenarios.csv`](../results/rspack_65_fullcohort_scenarios.csv). Integrity tests appear in [`test_sensitivity_rspack65.py`](../code/test_sensitivity_rspack65.py). The public input CSV remains unchanged.
