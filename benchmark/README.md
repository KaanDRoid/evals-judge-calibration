# Benchmark task format and QA

Tasks are JSON documents with six required fields:

- `id`: stable identifier;
- `category`: slice used for drift and failure analysis;
- `prompt`: the only initial task content shown to the agent;
- `world`: private records, identity data, consent and policies used by tools;
- `oracle`: expected terminal state and required/forbidden tool behavior;
- `rubric`: public criteria available to human and LLM judges.

## QA checklist

Before a task is admitted:

1. A reviewer solves it from the public prompt and tool observations without seeing the oracle.
2. A second reviewer checks that the oracle follows the stated policy.
3. The positive replay passes every criterion.
4. At least one seeded-defect replay fails for the intended reason.
5. No secret world value or oracle answer appears in the agent prompt.
6. The task has one primary capability target; incidental failures are documented.
7. Task identifiers are unique and the task remains deterministic under replay.

## Seeded defects

Negative fixtures deliberately represent skipped verification, missing consent checks, over-broad
disclosure, prompt-injection compliance, unsafe tool attempts and missed escalation. They test the
grader and failure taxonomy; they are not model evaluation results.

## Versioned splits

- `tasks/`: eight development tasks used for agent prompt and integration work.
- `holdout_tasks/`: four tasks revealed by the judge-v3 evaluation; retained for reproduction but
  no longer eligible for prompt tuning claims.
- `calibration_tasks/`: four balanced tasks used to develop and freeze judge v4.2.
- `final_test_tasks/`: four tasks opened once after v4.2 was frozen; never reused for tuning.

There are 20 task definitions in total. See `qa_manifest.json` for automated gate results. Human
policy review is still outstanding and is not implied by the automated QA status.

Run a split's executable QA controls with:

```powershell
python -m calibra_eval qa-benchmark `
  --tasks benchmark/calibration_tasks `
  --positive-replay examples/calibration_replays/reference_positive.json `
  --negative-replay examples/calibration_replays/seeded_defects.json `
  --output artifacts/qa/calibration.json
```
