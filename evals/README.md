# SongRyeon evaluation harness

This package scores normalized, deterministic fixtures. It deliberately does
not ask another LLM to decide whether an answer is correct.

## What it measures

- exact match, precision and recall for code-verified execution facts
- unsupported normalized code claims
- completion
- tool-call count
- latency
- optional scalar metrics such as context characters or rejection counts

`EvaluationCase` contains the expected fixture. `RecordedRun` contains one
system's normalized result. `evaluate_run()` compares them, and
`compare_systems()` aggregates multiple results.

```python
from evals import (
    EvaluationCase,
    ExecutionFact,
    RecordedRun,
    evaluate_run,
)

case = EvaluationCase(
    case_id="read-gates",
    expected_a_facts=(
        ExecutionFact("tool_call.1.name", "read_python_file"),
        ExecutionFact("tool_call.1.path", "runtime/gates.py"),
    ),
    supported_code_claims=("the gate limits rejection routing",),
)
run = RecordedRun(
    case_id="read-gates",
    system_name="songryeon",
    reported_a_facts=case.expected_a_facts,
    code_claims=("the gate limits rejection routing",),
    completed=True,
    tool_call_count=1,
    latency_ms=1200,
)

result = evaluate_run(case, run)
print(result.to_dict())
```

## Boundary of the current harness

The harness does not extract facts or claims from free-form answers. A fixture
builder or a human must normalize them first. That extraction step must be
versioned and disclosed; otherwise a comparison could silently encode the
reviewer's judgment.

No competition result should be published until:

1. the test cases are frozen,
2. all compared systems use the same questions and source fixtures,
3. model tag, model ID and configuration are recorded,
4. raw outputs are preserved,
5. failures are included instead of discarded.
