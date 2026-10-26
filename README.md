# Calibra Eval

Calibra Eval is a small, auditable evaluation harness for stateful compliance agents. It tests
whether an agent verifies identity, checks authorization, limits disclosure scope, resists prompt
injection, and escalates safely. It combines executable grading with a separately evaluated LLM
judge; current judge-reference agreement is not human calibration.

> **Project status:** engineering study implemented; auditable trajectory-level human annotation pending. The repository contains
> 20 automatically QA-validated task definitions across development, revealed holdout, judge-calibration and final
> test splits; 120 repeated local-model trajectories; a frozen Qwen3 4B judge study; and an executed
> Harbor/Terminal-Bench 2 smoke. All current reference labels are programmatic or synthetic and are
> explicitly **not** presented as human–judge agreement.
>
> **Observation intake (2026-10-26):** an owner-supplied A-01 narrative records 9 PASS and 2 UNCERTAIN
> category-level decisions. The original and a [methodological review](reports/2026-10-26_annotation-observation-review.md)
> are preserved. Missing decision IDs, source trajectories and independent second labels prevent
> treating it as a matched human-calibration dataset; existing measured scores remain unchanged.

## Why this exists

Agent evaluation can fail at several layers: the model, prompt, tool environment, hidden oracle,
programmatic grader, human annotation, or LLM judge. A single pass rate hides those distinctions.
This project preserves full trajectories and reports disagreement and failure slices so that a
researcher can locate the likely causal layer.

```text
task + private world ──> agent ──> tool trajectory ──> terminal state
                              │             │                │
                              └─────────────┴──────> programmatic grader
                                            │
                         public rubric + trajectory ──> LLM judge
                                            │
                           blinded reference labels ──> calibration report
```

The LLM agent and judge do not receive the private oracle. Deterministic graders own criteria that
can be checked from state; an LLM judge is reserved for subjective dimensions.

## Current benchmark

The disclosure benchmark covers:

- valid self-service and authorized-delegate requests;
- missing and expired consent;
- minimum-necessary field scope;
- prompt injection framed as a record instruction;
- identity mismatch and ambiguous requester identity.
- revoked consent, recovery from a missing record, and consented-but-unrequested fields.

Each JSON task contains a public prompt, private deterministic world, executable oracle and human-
readable rubric. Every split has positive and seeded-defect replay controls and passes the automated
QA gate. See [benchmark/README.md](benchmark/README.md) and
[benchmark/seeded_defects.md](benchmark/seeded_defects.md).

## Measured results

| Study | Result | Interpretation |
|---|---:|---|
| Three models × 8 tasks × 5 seeds | 0 / 120 pass | distinct, stable tool-integration failures |
| Judge v3 revealed holdout | 42.9% valid accuracy; κ=0 | always-fail bias exposed |
| Judge v4.2 calibration | 8/8 valid and correct; κ=1 | prompt-freeze gate only |
| Judge v4.2 final test | 5/8 valid; 5/5 correct | 62.5% coverage-adjusted accuracy |
| Harbor Terminal-Bench 2 smoke | nop=0; oracle=1 | harness/verifier controls pass |

![Judge quality](reports/assets/judge-quality.svg)

The judge table uses executable grader references, not human labels. Final-test invalid outputs are
counted wrong in coverage-adjusted accuracy. See the
[judge report](reports/2026-09-06_judge-v4.2-final.md) and
[multi-model failure report](reports/2026-09-06_multi-model-variance.md).

## Quick start

Python 3.11+ and the development extra are sufficient for the deterministic suite:

```powershell
uv sync --extra dev
```

```powershell
.\run_all.cmd
```

On Linux or WSL:

```bash
./run_all.sh
```

The command runs unit tests, executes two synthetic replay agents, grades all trajectories, creates
a failure-prevalence summary, and validates the calibration statistics pipeline. Generated files
are written under `artifacts/demo/` and are deliberately excluded from version control.

## Run a real local model

Start Ollama, pull an instruction-following model that fits the available hardware, then run:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m calibra_eval run-ollama --model YOUR_MODEL_NAME --limit 2 --max-steps 6
```

The adapter uses Ollama's native tool-calling support on `/api/chat` and records ordered tool calls, results, final
state, seeds and grades. Model and judge families should differ where practical to reduce shared
bias. A real experiment should run multiple seeds rather than treating temperature zero as fully
deterministic. The default local profile limits context to 4,096 tokens, output to 256 tokens, runs
requests sequentially, and lets Ollama unload the model after 30 seconds of inactivity.

Judge saved trajectories with a different model family:

```powershell
python -m calibra_eval judge-ollama `
  --model YOUR_JUDGE_MODEL `
  --trajectories artifacts/ollama/trajectories.jsonl
```

Judge outputs include the judge model and prompt version. They must be joined to independently
collected reference labels before running calibration.

Start with `--limit 2`; remove the limit only after inspecting the smoke trajectories. The runner
is serial and `--max-steps` caps runaway tool loops.

For a repeated-run study:

```powershell
python -m calibra_eval run-ollama --model YOUR_MODEL_NAME `
  --runs-per-task 5 --start-seed 101 --temperature 0.2 --max-steps 6
python -m calibra_eval variance --grades artifacts/ollama/grades.jsonl `
  --output artifacts/ollama/variance.json
```

Prepare a blinded, deterministically shuffled human-annotation sheet without exposing model
identity, task identity, private oracles, or programmatic grades:

```powershell
python -m calibra_eval make-annotation-batch `
  --tasks benchmark/holdout_tasks `
  --trajectories artifacts/heldout/mixed-reference/trajectories.jsonl `
  --output artifacts/annotation/decisions.csv `
  --key artifacts/annotation/private-key.jsonl
```

The key is intentionally separate and must remain hidden until labels are frozen.

The sheet accepts `pass`, `fail` or `uncertain`, plus confidence (1–5), rationale and an
`uncertainty_reason` for abstentions. Binary agreement excludes pairs with an abstention and reports
paired coverage explicitly. Every uncertain case enters adjudication, even if both annotators abstain;
its confidence and evidence notes are retained. Legacy binary CSVs remain supported. See the
[annotation rules](calibration/protocol.md#annotation-decision-contract-and-abstentions).

After two annotators independently fill copies, measure agreement and create the adjudication queue:

```powershell
python -m calibra_eval annotation-agreement `
  --annotator-a artifacts/annotation/reviewer-a.csv `
  --annotator-b artifacts/annotation/reviewer-b.csv `
  --output artifacts/annotation/human-human-agreement.json `
  --disagreements artifacts/annotation/adjudication-queue.csv
```

## Calibration

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m calibra_eval calibrate data/demo_calibration.csv
```

The report includes:

- confusion matrix and class prevalence;
- per-class precision, recall and F1;
- accuracy and balanced accuracy;
- Cohen's kappa and MCC;
- bootstrap 95% interval for kappa;
- lowest-agreement task categories ("drift zones").

Cohen's kappa adjusts for chance agreement but does not solve class imbalance. For the real study,
reference labels will be collected blind from two annotators, inter-annotator agreement will be
reported before adjudication, and model identity will be hidden. The complete procedure is in
[calibration/protocol.md](calibration/protocol.md).

## Reproducibility and artifacts

Every result is keyed by task, model and run identifier. Raw trajectories and criterion-level grades
are retained as JSONL. The weekly workflow runs the deterministic regression suite; it does not
claim to call Ollama on a hosted runner.

```bash
docker build -t calibra-eval .
docker run --rm calibra-eval
```

## Deliverable status

| Deliverable | Status |
|---|---|
| 10–20 tasks with prompt/environment/rubric/grader/QA | Complete: 20 tasks |
| Three local models, five seeds per task | Complete: 120 trajectories |
| Variance, confidence interval and accuracy-vs-κ demonstration | Complete |
| Judge prompt iterations, frozen calibration and final test | Complete |
| Failure taxonomy, prevalence and causal recommendations | Complete |
| Blinded sampling and two-annotator adjudication tooling | Complete |
| Real independent human labels | Pending external annotators; never fabricated |
| Harbor standard benchmark smoke and limitations | Complete |
| One-command tests, Docker and weekly CI | Complete |

## Role alignment

- End-to-end eval pipeline: task loading → agent → stateful tools → trajectory → executable grader.
- Judge calibration: per-class P/R/F1, balanced accuracy, κ, MCC, bootstrap interval, drift slices,
  output coverage, blinded annotation and adjudication.
- Benchmark extension: happy paths, edge cases, adversarial tasks, private oracle, replays and QA.
- Failure analysis: model, adapter, prompt, judge, environment and benchmark layers are separated.
- Recurring workflow: deterministic CI runs on push, pull request and a weekly schedule.
- Framework experience: Harbor 0.22.0 executed against registered Terminal-Bench 2 with positive and
  negative controls; opinions are documented in [harbor/run_notes.md](harbor/run_notes.md).

## Repository map

```text
benchmark/tasks/        versioned task definitions and private oracles
benchmark/holdout_tasks/ revealed holdout tasks; frozen after first judge evaluation
benchmark/calibration_tasks/ balanced prompt-development tasks
benchmark/final_test_tasks/ frozen final judge test
src/calibra_eval/       environment, runner, graders, statistics and adapters
examples/replays/       deterministic positive/negative smoke fixtures
examples/holdout_replays/ balanced held-out reference/defect fixtures
examples/calibration_replays/ judge-development controls
examples/final_test_replays/ final-test controls
calibration/            annotation and judge-calibration protocol
failure_analysis/       causal failure taxonomy
harbor/                  executed framework notes
setup/                   low-resource local stack instructions
reports/                dated, explicitly scoped experiment reports
tests/                  deterministic unit and end-to-end tests
artifacts/               generated run outputs (gitignored)
```

## Known limitations

- Twenty task definitions and eight-decision judge splits are not statistically powered.
- Demo labels and agents are synthetic fixtures.
- Judge references are executable grades, not adjudicated human labels.
- Bootstrap intervals quantify sampling uncertainty only; they do not repair biased labels or task
  selection.
- The environment is intentionally compact and does not yet model concurrent or multi-session state.

The first real local agent and same-model judge smoke tests are documented in
[reports/2026-09-06_llama3.2-3b-smoke.md](reports/2026-09-06_llama3.2-3b-smoke.md).
The balanced frozen-prompt judge failure is documented in
[reports/2026-09-06_qwen3-4b-heldout.md](reports/2026-09-06_qwen3-4b-heldout.md).
The criterion-level judge and repeated-model conclusions are documented in
[reports/2026-09-06_judge-v4.2-final.md](reports/2026-09-06_judge-v4.2-final.md) and
[reports/2026-09-06_multi-model-variance.md](reports/2026-09-06_multi-model-variance.md).
