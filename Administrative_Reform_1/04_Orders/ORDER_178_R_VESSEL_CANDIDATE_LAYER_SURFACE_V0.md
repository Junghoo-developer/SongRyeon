# ORDER 178: R Vessel Candidate Layer Surface v0

## Status

Proposed and approved for immediate implementation on 2026-07-02.

## Problem

ORDER 177 removed candidate text from R1, so R1 now behaves like a goal setter instead of reading the whole candidate board.

The next live test showed a remaining bottleneck: R2 still receives a flat candidate list. If the first 50 active summaries are dominated by one kind of node, R2 can pick an unrelated first-looking candidate even when the user asks about another layer.

This is not a semantic-routing problem for code to solve. It is a candidate presentation problem.

## Goal

Build a code-generated absolute "candidate layer surface" for Vessel-backed R one-step traversal.

R2 should first see a shelf/table-of-contents view of candidate groups, then select one candidate inside a chosen shelf.

## Scope

- Add a candidate layer surface frame built only from existing packet fields.
- Group candidates by explicit absolute fields:
  - entry candidate kind
  - summary data kind
  - summary depth
  - info class
- Update R2 input so it receives:
  - available surface IDs
  - surface records with counts
  - candidate records grouped by surface
- Require R2 to output:
  - selected_surface_id
  - selected_graph_node_id
- Validate that:
  - selected_surface_id exists
  - selected_graph_node_id belongs to the selected surface
- Adjust the Vessel read packet candidate limit policy so active summary candidates are selected across data-kind/depth groups instead of taking the first flat 50.

## Non-Goals

- Do not make code decide which surface is semantically relevant.
- Do not add a multi-step R loop.
- Do not add meaning-axis CoreEgo links.
- Do not change Neo4j schema shape.
- Do not weaken R1/R2/R3 schema validation.
- Do not connect R route to live node_1/node_2/node_3 flow.

## Metadata Boundary

The candidate layer surface is absolute information:

- generated_by: `CODE:R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_BUILDER`
- info_class: `absolute`
- semantic_judgement_status: `not_run`

R2's surface and node choice remains LLM semantic judgment:

- generated_by: `LLM:*:R2_vessel_node_selector`
- info_class: `mixed`
- semantic_judgement_status: `ran`

## Completion Criteria

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py -q`
- `python main.py fast-test --profile graph`
- `python main.py smoke-test`

## Expected Tests

- Candidate surface groups packet candidates by explicit absolute fields.
- Surface frame does not contain summary text.
- R2 payload is grouped by surface and no longer exposes flat `summary_candidate_records`.
- R2 fails if it selects a graph node outside the selected surface.
- Read packet limiting keeps multiple summary kinds/depths visible when one kind has many records.

