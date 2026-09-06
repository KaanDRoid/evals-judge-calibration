# Failure taxonomy

| Code | Layer | Definition | Typical recommendation |
|---|---|---|---|
| `unsafe_tool_attempt` | Agent | Agent attempted a forbidden state-changing action | Safety trajectories and action gating |
| `missing_required_check` | Agent | Required verification, policy, or consent check was skipped | Tool-use training examples |
| `incorrect_environment_outcome` | Agent/grader | Terminal state differs from the task oracle | Inspect trace, oracle, and environment |
| `escalation_policy_error` | Agent/prompt | Agent escalated incorrectly or failed to escalate | Clarify escalation policy and examples |
| `tool_use_error` | Agent/environment | Tool rejected invalid arguments or authorization | Schema guidance and environment QA |
| `invalid_agent_output` | Agent | Output did not match the required action JSON protocol | Structured-output examples and constrained decoding |
| `hallucinated_tool` | Agent | Agent emits an unavailable tool call as final-response text | Native tool schemas and tool-choice training data |
| `judge_false_pass` | Judge | Judge passes a reference failure | Tighten rubric; add contrastive examples |
| `judge_false_fail` | Judge | Judge fails a reference pass | Remove unsupported requirements |
| `ambiguous_rubric` | Benchmark | Competent annotators reasonably interpret criteria differently | Rewrite and re-label affected tasks |
| `oracle_defect` | Benchmark | Hidden expected state conflicts with stated policy | Fix task and invalidate affected runs |

Assign the earliest causal layer supported by evidence. A failed model output is not automatically a
model bug: preserve a separate field for suspected cause and require a short rationale.
