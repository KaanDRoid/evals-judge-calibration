# Harbor 0.22.0 / Terminal-Bench 2 smoke

## Executed result

On 2026-09-06, Harbor 0.22.0 ran one registered
`terminal-bench/terminal-bench-2` task (`make-mips-interpreter`) locally with Docker:

| Control | Trials | Exceptions | Mean reward | Runtime |
|---|---:|---:|---:|---:|
| `nop` | 1 | 0 | 0.000 | 1m 29s |
| `oracle` | 1 | 0 | 1.000 | 22s |

Both runs used concurrency 1, a one-CPU limit, and a 2 GB memory limit. Results are retained under
`artifacts/harbor/`. This verifies dataset resolution, container setup, agent execution, verifier
execution, reward collection, and artifact persistence. It is not a model benchmark score.

## What Harbor does well

- A task packages instruction, sandbox environment, tests, and optional reference solution.
- `nop`/`oracle` controls make verifier and task QA concrete before an expensive model run.
- Trial and job artifacts preserve config, logs, verifier outputs, reward, and trajectory.
- Resource enforcement and concurrency controls make local-to-distributed scaling explicit.
- The dataset registry and adapter structure give benchmark extensions a repeatable packaging path.

## Where it falls short for this project

- Installation pulled a broad 90-package stack; first-run latency was materially larger than this
  repository's dependency-free deterministic harness.
- Harbor solves sandboxed task execution, not human-reference collection or LLM-judge calibration;
  those still require a separate protocol.
- A terminal coding agent is not the same interaction contract as this stateful disclosure agent.
- Local Ollama is not a drop-in Harbor agent in this setup; a custom external agent or compatible
  installed CLI integration would be needed for a fair model run.

Harbor's official docs describe it as the official Terminal-Bench 2 harness and recommend first
running oracle solutions: https://www.harborframework.com/docs/tutorials/running-terminal-bench
