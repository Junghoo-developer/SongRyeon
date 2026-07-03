# ORDER 184: R Vessel Multi-Step Traversal MVP v0

## Status

Approved by the user on 2026-07-02 for overnight implementation.

## Trigger

ORDER_182 and ORDER_183 prepared the pieces:

- ORDER_182: R2 first view starts from CoreEgo's entry layer instead of leaf summary 폭탄.
- ORDER_183: after R3 inspection, code can build a direct child candidate surface.

The remaining gap is that the child candidate surface is not yet fed back into R2. R still performs only one selection step.

## Goal

Implement a standalone R Vessel multi-step traversal MVP:

```text
R1 goal once
-> R2 selects from current candidate surface
-> R3 inspects selected node
-> code builds child candidate surface
-> if R3 recommends deeper and budget remains, feed that surface back to R2
-> stop on sufficient / budget exhausted / no actionable path / failure
```

## CLI Target

Add a new command:

```powershell
python main.py vessel-r-traverse "질문" --database neo4j --llm-mode fake --format text
```

## Metadata Boundary

- Code may build candidate surfaces, copy graph IDs, enforce budgets, and record path frames.
- Code must not semantically choose the best child candidate.
- R2 remains responsible for semantic node selection among code-supplied official refs.
- R3 remains responsible for sufficiency/granularity/branch judgment.
- Traversal result frame is code-generated absolute information summarizing recorded frames and statuses.

## Non-Goals

- Do not connect R route to node_1 yet.
- Do not inject R result into node_0 memory packets yet.
- Do not connect R result to node_3 final answer yet.
- Do not add R2a/R2b or A/B selection formats.
- Do not mutate Neo4j graph structure.
- Do not weaken R2 official ref validation.

## Initial Policy

Use explicit fixed budgets for this MVP:

- `max_traversal_depth=4`
- `max_node_reads=4`
- `max_branch_switches=0`
- `max_context_tokens=8000`

These are policy constants, not hidden heuristics.

## Verification Targets

- Fake traversal can descend across at least two R2/R3 steps.
- Each step records R2, R3, continuation, and candidate surface frames.
- The traversal path is preserved in a code-generated result frame.
- The command renders step path and final status in text mode.
- Graph fast-test includes the new traversal tests.
