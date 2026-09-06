#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:src"

run_py() {
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
  else
    python "$@"
  fi
}

run_py -m pytest -q -p no:cacheprovider
run_py -m calibra_eval demo
run_py -m calibra_eval qa-benchmark --tasks benchmark/tasks --positive-replay examples/replays/scripted_cautious.json --negative-replay examples/replays/scripted_buggy.json --output artifacts/qa/development.json
run_py -m calibra_eval qa-benchmark --tasks benchmark/holdout_tasks --positive-replay examples/holdout_replays/reference_positive.json --negative-replay examples/holdout_replays/seeded_defects.json --output artifacts/qa/revealed-holdout.json
run_py -m calibra_eval qa-benchmark --tasks benchmark/calibration_tasks --positive-replay examples/calibration_replays/reference_positive.json --negative-replay examples/calibration_replays/seeded_defects.json --output artifacts/qa/calibration.json
run_py -m calibra_eval qa-benchmark --tasks benchmark/final_test_tasks --positive-replay examples/final_test_replays/reference_positive.json --negative-replay examples/final_test_replays/seeded_defects.json --output artifacts/qa/final-test.json
run_py -m calibra_eval annotation-agreement --annotator-a data/demo_annotator_a.csv --annotator-b data/demo_annotator_b.csv --output artifacts/demo/human-human-agreement.json --disagreements artifacts/demo/adjudication-queue.csv
