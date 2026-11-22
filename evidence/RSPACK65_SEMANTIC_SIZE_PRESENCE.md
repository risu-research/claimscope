# Semantic artifact-size reporting among 65 boundary-dependent Rspack PRs

## Question and decision rule

Does each PR contain a genuine reported measurement of an artifact's size, regardless of whether the original D6 extractor detects that measurement when comment boundaries are preserved?

We fixed a short, source-specific rule before the full audit. A positive requires (1) a GitHub Actions report attached to the PR before the August 27, 2026 reference snapshot, (2) an identified binary or bundler output, (3) an observed numerical byte-unit size and (4) a completed measurement. Size increases, decreases, and unchanged observations qualify. A numeric size budget, memory usage, prospective estimate, or benchmark percentage alone does not qualify. We separately record whether the comparison references the PR's current head commit or one of its listed commits. Results describe *report presence*, with no inference of improvement or causal attribution.

The audit uses the documented `Binary Size-limit` report format and independently checks `Rsdoctor Bundle Diff Analysis` size tables. The rule does not invoke Peng et al.'s D6 extractor. This is a deterministic, inspectable source audit with direct review of exceptions, not blinded human adjudication. The run validates comment timestamps and records source URLs and SHA-256 body digests.

## Results

| Observation | Result |
| --- | ---: |
| PRs with a concrete artifact-size measurement | **65 / 65** |
| Original sample arm: `agentic` | 60 / 60 |
| Original sample arm: `human_candidate` | 5 / 5 |
| Binary-size report source commit matching the PR's current head | **65 / 65** |
| Rsdoctor project-size table also present | 65 / 65 |
| Binary size increased | 37 |
| Binary size decreased | 23 |
| Binary size unchanged | 5 |
| Cases requiring an unresolved or negative semantic verdict | **0** |

Two reports use literal `288bytes` and `416bytes` change units. Their source lines were inspected directly and `bytes` was added to the explicit byte-unit parser, together with regression tests. Both carry before/after binary sizes in MB and are anchored to their PR heads. The recorded direction is `increased` in both cases, despite the displayed rounded MB values being equal.

## Representative original source records

- [Rspack #13010 binary report](https://github.com/web-infra-dev/rspack/pull/13010#issuecomment-3871932287): 48.65 MB to 48.61 MB, reported decrease of 48.00 KB.
- [Rspack #13581 binary report](https://github.com/web-infra-dev/rspack/pull/13581#issuecomment-4174659933): a reported increase of 288 bytes, with rounded before/after sizes of 49.09 MB.
- [Rspack #13647 binary report](https://github.com/web-infra-dev/rspack/pull/13647#issuecomment-4205915704): a reported increase of 416 bytes, with rounded before/after sizes of 49.35 MB.
- [Rspack #13787 binary report](https://github.com/web-infra-dev/rspack/pull/13787#issuecomment-4294059573): unchanged at 62.85 MB.

The [65-row CSV](../results/rspack65_semantic_size_audit.csv) preserves a direct source URL, observed value, direction, report type, commit relation, timestamps, and content digest per PR. The [detailed JSON](../results/rspack65_semantic_size_audit.json) records each qualifying size report and source identity.

## Interpretation for ClaimScope

The original source D6 extractor marks the 65 Rspack PRs positive when issue comments are concatenated. Preserving issue-comment boundaries causes all 65 to lose D6 under its original 12-token matching rule. In the companion [other-channel replay](RSPACK65_OTHER_SOURCE_RETENTION.md), none of these 65 receives a D6 hit from the other currently available source channels.

The semantic audit reaches **65/65 concrete size reports**, using each PR's binary-size comment. These findings are compatible: comment-boundary sensitivity concerns *detection by one rule*, whereas the present audit measures *observable reporting*. The +8.885 to +2.486 percentage-point shift therefore describes a detector-specific counterfactual; it is not a corrected estimate of true artifact-size reporting. Broader semantic prevalence across the remaining 1,634 PRs is not measured here.

The GitHub evidence was recollected on November 22, 2026 UTC. The original author's August 2026 private evidence snapshot remains unavailable. The audit verifies that each cited comment's creation and last-update timestamps precede the original reference cutoff, and that each binary report's first compared SHA matches the currently returned PR head. Head matches and GitHub comments are evidence of PR-linked reporting, not independent build reproduction or causal change attribution.

## Reproduction

```bash
python3 -m unittest discover -s code -p 'test_semantic_rspack65_size.py' -v
python3 code/semantic_rspack65_size.py --max-workers 5
bash run_checks.sh
```

The live collection requires GitHub API access. `GITHUB_TOKEN` increases the request allowance. The stored source-ledger CSV and JSON support offline inspection and cross-checking against the 65-PR witness set and the independent source-channel audit.
