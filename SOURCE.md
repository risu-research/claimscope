# Source and provenance

Source study: Huiyun Peng, Ricardo Calvo, Kelechi G. Kalu, and James C. Davis, *How Do Coding Agents Optimize Software and Report Performance Validation?*, 2026. [arXiv:2610.03969](https://arxiv.org/abs/2610.03969).

Public source repository: [PurdueDualityLab/EMSE-perf-pr-study](https://github.com/PurdueDualityLab/EMSE-perf-pr-study).

Pinned commit: `64432e0b6ed7791bbfa929c6c183fc76c75b5d58`.

Source file: [`analysis/classification_labels/rq3_labels.csv`](https://github.com/PurdueDualityLab/EMSE-perf-pr-study/blob/64432e0b6ed7791bbfa929c6c183fc76c75b5d58/analysis/classification_labels/rq3_labels.csv).

| Integrity field | Expected value |
| --- | --- |
| Source bytes | 649030 |
| CSV rows | 2081 |
| In-metric-layer rows | 1699 |
| Git blob SHA-1 | `136a2cf5bf1a9a71f06f2a7c6c9932194865c854` |
| File SHA-256 | `c31616088cac4ea8d2369b942b78f08e39356250a0b452aba5c9402e05e070b9` |

Primary row filter: `in_metric_layer == True`.

Primary key: `(repo_id, number)`. Study arm: `sample_arm`. Artifact-size flag: `D6`. Code-diff exclusion variant: `D6_nodiff`. Category: `pattern`.

Rspack repository ID: `476642602`, corresponding to `web-infra-dev/rspack`.

The original source repository carries an MIT license. Its license text is preserved in [`data/UPSTREAM_LICENSE`](data/UPSTREAM_LICENSE). Cite the Peng et al. study when reusing the label export.

The source dataset's `human_candidate` label records a comparison cohort. `D6` is an extracted reporting signal. The original PR-level source-match spans, `dim_sources`, and `dims_from_bot_comments` were excluded from the compact CSV distribution.
