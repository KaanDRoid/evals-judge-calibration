# Agent benchmark comparison notes

## Calibra Eval

Strength: deterministic state, authorization checks, exact disclosure scope, prompt injection, and
causal failure labels are first-class. Limitation: the world is intentionally compact, synthetic,
single-session, and currently only 20 task definitions.

## Terminal-Bench 2 / Harbor

Strength: hermetic terminal tasks with executable verifiers and portable container environments.
Limitation: terminal/code completion does not measure conversational authorization or simulated
user interaction; a one-task smoke validates the harness, not model capability. Harbor is the
official harness: https://www.harborframework.com/docs/tutorials/running-terminal-bench

## GAIA

Strength: broad assistant questions requiring reasoning, web browsing, files, images, and code.
Limitation: final-answer matching can underrepresent process quality and safety, while web-dependent
questions are vulnerable to environmental drift and reproducibility issues. Original paper:
https://arxiv.org/abs/2311.12983

## τ-bench

Strength: dynamic user-agent-tool interaction, domain policy, terminal database-state grading, and
pass^k reliability over repeated trials. Limitations: results also depend on the simulated user's
behavior, and the original public task repository now warns that its airline/retail tasks are
outdated in favor of τ³-bench. Paper: https://arxiv.org/abs/2406.12045 - current repository notice:
https://github.com/sierra-research/tau-bench
