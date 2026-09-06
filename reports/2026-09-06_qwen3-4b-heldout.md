# Qwen3 4B judge: frozen-prompt held-out evaluation

## Executive result

The frozen `judge-v3-strict-concise` prompt did not generalize. It had agreed with all eight
all-fail development trajectories, but on this balanced held-out suite it rejected every validly
parsed positive trajectory.

This is a useful negative result: aggregate development accuracy concealed a failure-seeking judge
bias that becomes obvious only with a mixed-class holdout and per-class recall.

## Setup

- Judge: `qwen3:4b` via Ollama, temperature 0, prompt frozen before this run.
- Data: four previously unseen task definitions, each paired with one correct reference replay and
  one deliberately defective replay (8 trajectories; 4 pass, 4 fail).
- Reference: executable programmatic grader, **not human annotation**.
- Runtime profile: serial requests, 4,096-token context, 320-token output cap, model unloaded after
  the run.
- Tuning rule: these results were inspected only after all predictions were written. No prompt
  change will be evaluated on this same set and described as held-out performance.

## Results

One of eight judge responses was invalid because it returned `fail` with the semantically
inconsistent failure mode `none`. Metrics below exclude that response, as declared by the
comparison protocol.

| Metric | Result |
|---|---:|
| Valid paired decisions | 7 / 8 |
| Accuracy on valid decisions | 42.9% |
| Balanced accuracy | 50.0% |
| Cohen's kappa | 0.000 |
| Matthews correlation | 0.000 |
| Fail recall | 100.0% (3/3) |
| Pass recall | 0.0% (0/4) |
| Coverage-adjusted accuracy, invalid counted wrong | 37.5% (3/8) |

The valid-decision confusion matrix was: 3 fail→fail, 0 fail→pass, 4 pass→fail, and 0 pass→pass.
The sample is too small for category-level drift estimates to be interpreted as stable rates.

## Failure analysis

All four false rejections were evidence-reading or rubric-semantics errors:

1. The judge acknowledged a successful `verify_identity` event, then claimed no tool event proved
   verification.
2. It interpreted a final answer saying an out-of-scope balance was **not** disclosed as claiming
   that it **was** disclosed.
3. It treated `read_policy` as an attempted `disclose` action.
4. It treated `valid: false` from `check_consent` as failure to perform the required consent check,
   even though the expected behavior was to observe invalid consent and escalate.

The likely judge-level cause is an over-strict, failure-seeking decision policy combined with weak
event/rubric alignment. Development selection amplified the problem: every development reference
was `fail`, so 100% development agreement could be achieved without demonstrating pass
discrimination. This is evidence of a calibration design defect, not evidence that the underlying
agent trajectories failed.

## Recommendation and freeze decision

Do not tune `judge-v3-strict-concise` against this revealed holdout. Develop a new judge version on
a separate, balanced calibration set. The next design should require one structured decision per
rubric criterion with cited event IDs, then aggregate deterministically: pass only when every
required criterion passes. It should also distinguish "check performed and result was negative"
from "check omitted," and distinguish policy lookup from a state-changing disclosure attempt.

After the design is frozen, evaluate it once on a new untouched test set. Human labels must still
be collected blind before making claims about human–judge agreement.

Raw generated artifacts are stored locally under `artifacts/heldout/` and intentionally ignored by
Git. The versioned task definitions and replay fixtures remain available for reproduction.
