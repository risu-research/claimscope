# Data rights, citations, and source boundaries

## Original study and metric labels

ClaimScope uses the compact `rq3_labels.csv` released by Huiyun Peng, Ricardo
Calvo, Kelechi G. Kalu and James C. Davis in
[PurdueDualityLab/EMSE-perf-pr-study](https://github.com/PurdueDualityLab/EMSE-perf-pr-study).
The exact study revision and source file hashes are recorded in `SOURCE.md`.
The original source repository publishes software under the MIT license and its
license is reproduced in `data/UPSTREAM_LICENSE`. The original work must be
credited when using its labels, data and extractor.

The pinned upstream metric extractor files, when copied into the
`code/upstream_pinned/` directory, remain the original authors' work. Their
original Git blob identities must be verified before executing them.

## Public Rspack evidence

The public comment text in `evidence/` and some `results/` files originates
in [web-infra-dev/rspack](https://github.com/web-infra-dev/rspack) issue
discussions, including automated GitHub Actions reports. Source URLs, timestamps,
and content digests accompany retained evidence. Third-party reports are cited
for inspection. The MIT license for ClaimScope's own code does not relicense
those original comments or the source study's dataset.

The minimal temporal ledger retains public IDs and dates without any comment
body text or human-account names. Public source material is used only to support
reproducible analysis; the original August 2026 archive held by the source
authors is not redistributed.

## Provenance and claims

A D6 match is a property of a deterministic metric extractor. Presence of a
concrete automated size report is separately audited. Neither establishes a
performance improvement caused by a pull request.

The historical 2026-08-27 evidence snapshot is inaccessible. A new GitHub
collection is a different observation. Frozen files are identified by checksums
and versioned releases. See `README.md` and `evidence/` for complete methods.
