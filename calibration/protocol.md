# Judge calibration protocol

This protocol separates three questions that are often conflated: whether the agent reached the
correct environment state, whether a human considers the response acceptable, and whether an LLM
judge reproduces that human decision.

## 1. Freeze the evaluation unit

The unit is one complete trajectory: task prompt, ordered tool calls and results, final response,
and terminal environment state. Record the task version, model identifier, decoding parameters,
seed, run identifier, and code revision. Never silently overwrite a trajectory.

## 2. Draw a stratified sample

Sample across task category, model, programmatic pass/fail result, and run seed. The initial target
is at least 150 decisions, with deliberate oversampling of rare failures. Report both the sampled
class prevalence and the full-run prevalence. Do not tune the judge on the held-out calibration
split.

## 3. Collect blinded reference labels

Use two independent annotators when possible. Hide model identity and the other annotator's label.
Each annotator assigns `pass` or `fail`, a rubric criterion, a failure-mode code, and a short
rationale. Measure inter-annotator agreement before adjudication. Resolve disagreements through a
documented adjudication pass and preserve all original labels.

If only one annotator is available, call the result an `expert_reference_label`, not ground truth,
and list this as a study limitation. Labels in `data/demo_calibration.csv` are synthetic smoke-test
fixtures and must never be reported as human judgments.

Generate a shuffled sheet and a separate identity key with:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m calibra_eval make-annotation-batch `
  --tasks benchmark/holdout_tasks `
  --trajectories artifacts/heldout/mixed-reference/trajectories.jsonl `
  --output artifacts/annotation/decisions.csv `
  --key artifacts/annotation/private-key.jsonl `
  --seed 17
```

The CSV excludes task, model and run identifiers, private worlds, executable oracles, and
programmatic grades. Keep the key from annotators until labels are frozen. Duplicate the blank
sheet for independent annotators rather than allowing them to share a live label column.

The completed study candidate is `artifacts/annotation/frozen-150.csv`: it contains 150 decisions
selected across category, model, and programmatic outcome strata from a 160-trajectory pool. All
20 available programmatic passes and 130 failures were selected; these strata are sampling
metadata, not human ground truth, and neither labels nor model identities appear in the CSV.

## 4. Run judges without leakage

The judge receives the public prompt, rubric, trajectory and tool results. It does not receive the
private task oracle or programmatic grade. Use a different model family from the model under test
where practical. Record judge prompt version, model version, temperature and seed.

## 5. Report agreement

Report the confusion matrix, per-class precision/recall/F1, balanced accuracy, Cohen's kappa, MCC,
class prevalence, and a bootstrap 95% confidence interval. Kappa adjusts for chance agreement but
does not "solve" imbalance and can behave unexpectedly under extreme prevalence.

## 6. Locate drift

Slice disagreement by task category, model, outcome, trajectory length, failure mode, and judge
prompt version. Do not publish small slices without their sample size. Inspect the lowest-agreement
slices and classify whether the likely cause is the model, rubric, judge, programmatic grader, task,
or annotation process.

## 7. Re-run and compare

Use a frozen holdout whenever the judge prompt changes. Treat judge changes like model changes:
publish paired deltas with confidence intervals and retain previous artifacts.

Once holdout labels or predictions have been inspected, that set is no longer available for prompt
development. Create a separate calibration set and a new untouched final test set instead of
iterating against the revealed examples.
