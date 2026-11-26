# ClaimScope

Version 2.0.0.

A reproducible repository-level reanalysis of artifact-size reporting in agentic pull requests. The study uses the 1,699 PRs in the metric layer of the public label export accompanying Peng et al. ([arXiv:2610.03969v1](https://arxiv.org/abs/2610.03969v1)). It compares the published D6 flags, replays the original detector on public issue comments, and estimates reporting rates from 823 PRs inspected under two measurement definitions.

## Reproduce

Python 3.13.5 was used for the verified run. Python's standard library supplies all dependencies. From this directory, run:

```sh
python3 reproduce.py
```

The command verifies the archived files, recreates the fixed 656-PR sample, recomputes the published-label comparisons and exact population intervals, and runs the comment experiments. Generated tables and the verification report appear in `build/`. The numerical output checks compare eleven generated files with their reference versions. The detector tests compare individual PR counts and source-linked match signatures. The evidence audit independently aggregates all 1,646 PR-level outcomes from the recorded comment decisions and verifies the channel inventories. The source-tool tests exercise the recovery and review interfaces with controlled responses.

To inspect a particular experiment:

```sh
python3 code/replay_detector.py build/detector
python3 code/audit_evidence.py build/evidence
```

For a fresh public-source check of a selected thread, use its recorded IDs and SHA-256 digests:

```sh
python3 code/fetch_sources.py esphome/esphome 14029 --output build/esphome-14029.json
```

This optional command requires GitHub access. An environment variable `GITHUB_TOKEN` can increase the API quota. It records matching, changed, unavailable and additional source records. For the additional five evidence channels, use:

```sh
python3 code/fetch_sources.py web-infra-dev/rspack 13020 --channels --output build/rspack-13020-channels.json
```

Each channel with matching ordered text digests is replayed using the pinned detector. See [REVIEW.md](REVIEW.md) for independent report classification and source recovery.

## Main results

| Comparison | Result |
|---|---:|
| Published D6: agentic vs human-candidate | 115/858 vs 38/841 |
| Published gap | 8.885 pp |
| Published gap without Rspack | 1.339 pp |
| Symmetric repository-composition share | 80.3% |
| Rspack joined detector flags, all / bot only / other only / separate | 83 / 83 / 0 / 18 |
| Order-only changes from negative to positive | 8 |
| Audited PRs | 823 |
| Broad gap, estimated range | 0.37 to 3.70 pp |
| Broad gap, joint 95% interval | −4.29 to 8.70 pp |
| Whole-artifact gap, estimated range | 6.09 to 9.42 pp |
| Whole-artifact gap, joint 95% interval | 2.49 to 12.51 pp |

The estimated ranges account for unresolved report classifications. The confidence intervals additionally account for sampling. See [METHODS.md](METHODS.md) for measurement definitions, sample selection, and uncertainty, and [CLAIMS.md](CLAIMS.md) for the evidence supporting each result.

## Contents

- `data/`: pinned published labels, sampling frame, fixed sample, classifications of all 823 audited PRs, and source-linked match classifications.
- `evidence/`: 2,886 recorded comment identities and classifications, plus 508 preserved bodies for 102 threads used in detector experiments, six-channel inventories for 66 PRs, fresh public-source receipts and a blank review worksheet.
- `code/`: sampling, inference, replay and source-audit scripts; two unchanged original detector files and their Git blob identifiers.
- `reference/`: expected analysis outputs and Next.js source identifiers.
- `SHA256SUMS.json`: file integrity manifest.

## Evidence scope

The issue-thread observations use the August 27, 2026, 22:00 UTC creation and last-edit cutoff. The original study's full archived input snapshot remains access-controlled. Report classifications come from one evaluator; the statistical code recomputes results from those recorded decisions. The preserved detector corpus covers Rspack, the Valkey example, and four Next.js threads. The remaining source bodies can be requested by recorded comment ID and checked against their frozen hashes. Images, inaccessible comments, and earlier versions of edited comments remain unresolved where required by the classification rules. The six-channel inventories record the original coverage status, including one review-count discrepancy. [SOURCE.md](SOURCE.md) describes the fresh public-source check and the limits of channel recovery.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for source rights and evidence retention. The earlier v1.0.0 archive is available at [10.5281/zenodo.24434117](https://doi.org/10.5281/zenodo.24434117).
