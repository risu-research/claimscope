# Sampling, report definitions, and inference

## Population

Select the 1,699 rows with `in_metric_layer=True` in the pinned 2,081-row `rq3_labels.csv`. The key is `(repo_id, number)`. The published groups are `agentic` (858) and `human_candidate` (841). D6 is the artifact-size extraction flag. GitHub account type distinguishes bot accounts in the replay; individual PR authorship remains unverified.

## Fixed sample

Inspect all 153 published D6 positives, the remaining 14 Rspack PRs, and 656 non-Rspack published negatives. The negative frame contains 1,532 PRs. Within each group, repository evidence history gives three strata:

| Stratum | Agentic n/N | Human-candidate n/N |
|---|---:|---:|
| Previously verified structured report | 6/6 | 10/10 |
| Other repository with a D6 positive | 120/167 | 120/176 |
| Repository without a D6 positive | 200/558 | 200/615 |

The 31 source-linked structured witnesses identify eight repositories before negative-sample collection. A fixed 256-bit seed and SHA-256 ranking select 640 PRs from four random strata; the two small strata receive full inspection. `freeze.py` preserves the original hash-ranking domain separator for byte-identical reproduction. All selected IDs remain in the analysis. The census and sample yield 183 fully selected and 640 randomly selected PRs.

## Report classification

A qualifying report gives a measured size or measured relative size change of a software artifact associated with the PR or comparison baseline. The measurement and its object appear together within one issue-thread comment. Creation and latest update must fall at or before 2026-08-27 22:00 UTC. Increases, decreases, measured unchanged values, and measured current-only artifact sizes qualify.

- **Whole-artifact:** complete output artifact or separately distributed component file, including measured compressed file size or measured relative size change.
- **Broad:** includes Whole-artifact and measured storage footprints, such as compiled static Flash usage and allocated storage of a generated artifact. For example, the Sanity TypeDoc workflow reports `du -h` allocated disk usage of the generated JSON; its measured allocated storage qualifies for Broad.
- **Excluded quantities:** runtime memory, input or workload sizes, buffer limits, estimates, size thresholds, advertisements, and unrelated dependency quantities.

At PR level, a qualifying eligible report establishes a positive. An incomplete retrieval or unresolved relevant measurement leaves the outcome unknown in the absence of a qualifying report. Fully inspected eligible material without a qualifying report receives `no_observed_report`. Comments created after the cutoff are excluded. Relevant comments edited after the cutoff receive an unresolved status when earlier text is unavailable. The two definitions were distinguished during the first fully inspected negative stratum; later statistical comparisons retain the fixed sample.

`evidence/comment_classifications.csv` records source IDs, body hashes, measurement objects and values, available comparison references, decisions, and source-specific notes. `data/audited_prs.csv` retains the final PR-level outcomes. The audit aggregates all 823 PR outcomes for both definitions from the recorded comment classifications and retrieval status. A positive takes precedence over unresolved material; absent a positive, incomplete retrieval or unresolved relevant evidence yields an unknown. Unavailable images and ambiguous reports remain unknown. One evaluator performed the classification with the published labels visible. Independent agreement between evaluators is unmeasured. [REVIEW.md](REVIEW.md) describes a separate review procedure that withholds the original classifications from the generated worksheet.

## Estimation

For stratum size N, sample size n, observed positive count k, and unknown count u, use the Horvitz–Thompson count estimates N*k/n and N*(k+u)/n. Divide by the original group size to obtain the estimated rate range. The group contrast is agentic minus human-candidate, using opposite ends of the two rate ranges.

For each random stratum invert the exact hypergeometric tails. Use k for the lower bound and k+u for the upper bound. The single-definition analysis uses a tail probability of 0.05/8; the joint two-definition analysis uses 0.05/16. The joint analysis was added after classification. It gives at least 95% simultaneous coverage under simple random sampling without replacement within each random stratum and correct observed classifications. Census count bounds are [k, k+u]. For repository exclusions, standardization, and decomposition, the code optimizes each linear contrast over the same admissible counts and observed labels. Logical bounds allow any outcomes for unsampled and unknown PRs. All contrasts describe the fixed population.

The original D6 repository-cluster bootstrap draws 440 repositories with replacement, retaining their paired group counts, in each of 12,000 repetitions with seed 20261125. Its percentile range describes sensitivity to repository representation. The semantic interval addresses sampling within the fixed population. The sensitivity script also calculates the three-definition-family interval for the Broad-only contrast and hypothetical adverse changes to observed classifications.
