# Independent report review

The review unit is a PR's issue-thread discussion. The two definitions and cutoff are in [METHODS.md](METHODS.md). The archived outcomes came from one evaluator; this procedure lets another evaluator record decisions independently of those outcomes.

## Prepare

```sh
python3 code/review_reports.py prepare --output build/review
```

The command creates `review_sources.json`, `decisions.csv` and `coverage.json`. The worksheet contains all 823 PR identities and blank outcome fields, without the published D6 flag, the group label or the original report decisions. The source packet lists comment URLs, creation and update times, eligibility, expected hashes and available bodies. The archive includes 507 exact bodies and one detector-equivalent redacted body. The remaining 2,342 eligible bodies require source recovery. Thirty-six records fall outside the cutoff.

Use the source links and fetch the recorded thread locally when additional bodies are needed:

```sh
python3 code/fetch_sources.py esphome/esphome 14029 --output build/thread-14029.json
python3 code/review_reports.py prepare --source build/thread-14029.json --output build/review-expanded
```

Repeat `--source` for multiple recovered threads, or pass an inventory-shaped JSON array containing `repo`, `number`, and `comments` with `comment_id` and `body`. A source body must match its archived SHA-256 digest to appear as verified. The fetch command identifies changed bodies, missing IDs, additional IDs and timestamp differences separately. Earlier versions of edited or deleted comments may remain inaccessible. Keep downloaded text in the local review directory.

## Classify

Read the eligible source material before opening the recorded outcomes. Assign `positive`, `no_observed_report` or `unknown` for each definition. Record supporting eligible comment IDs separated by semicolons for a positive decision and a short reason in `review_note`. A qualifying Whole-artifact report also qualifies for Broad. When a relevant source remains inaccessible, use `unknown` unless another qualifying report establishes a positive. Treat a redacted replay body as a separate source status; recover its original text for independent semantic review. A negative decision requires sufficient coverage of the eligible material. A new source record or changed text belongs to a separate observation, outside this frozen review.

## Compare

After saving the worksheet, run:

```sh
python3 code/review_reports.py compare build/review-expanded/decisions.csv --output build/review-comparison.json
```

The comparison joins decisions by PR identity, checks the nested definitions and eligible witness IDs, and reports the completed count, the decision cross-tabulation and disagreements. Blank rows remain unreviewed. The command checks the decision file's structure; the reviewer determines whether the cited material supports each judgment. The comparison can be run on a partially completed worksheet. A fully independent repeat requires a separate evaluator and sufficient source coverage for every decision. The included tests use controlled examples to verify the workflow, with no claim of measured inter-evaluator agreement.
