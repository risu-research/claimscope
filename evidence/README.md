# Rspack PR source inventory

The November 22, 2026 UTC inventory joins 97 `web-infra-dev/rspack` pull requests to Peng et al.'s pinned public RQ3 labels. Each row links the PR, its creator account, the published D6 flag, and the first `github-actions[bot]` `Binary Size-limit` comment when present.

| Observed item | PRs |
| --- | ---: |
| Rspack analytic sample | 97 |
| Published D6-positive | 83 |
| Published D6-negative | 14 |
| Binary-size bot comment present | 94 |
| Bot comment and D6-positive | 83 |
| Bot comment and D6-negative | 11 |
| Published D6-negative with no matching bot comment | 3 |
| Rsdoctor bundle-diff bot comment present | 91 |

The GitHub API inventory covers issue-thread comments and inline review comments. `bot_binary_size_present` identifies a comment posted by a GitHub bot account containing `Binary Size-limit`. `published_D6` reproduces the original public-label field. These are separate observations.

The original RQ3 extractor also processed PR descriptions, commit messages, workflow-run names, and file patches. Its archived source-specific matches and `dims_from_bot_comments` require a separate replay against the historical evidence collection. Current GitHub API records form a dated public-observation layer.

All 97 retrieved PRs had valid GitHub metadata. The collected issue-thread and inline review comments had creation and update timestamps on or before August 27, 2026. This timestamp check covers the records currently returned by GitHub.

Run `python3 code/rspack_source_inventory.py --output build/rspack_source_inventory.csv` from the repository root to collect a fresh source inventory. Set `GITHUB_TOKEN` for the GitHub API request quota. The script validates the source CSV hash before fetching PRs. `--max-prs 5` supports a quick API check.

Source attribution and input integrity are recorded in [`../SOURCE.md`](../SOURCE.md).

## Exact-source replay

The [full Rspack D6 audit](RSPACK_D6_EVIDENCE_AUDIT.md) records the pinned original extractor, 11-case controlled text changes, 97-PR comment-boundary sensitivity, and reproducible result files. The original-rule audit reads current GitHub issue comments and keeps each PR's published D6 label fixed.
