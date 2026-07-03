# ORDER 180: R2 Prompt Example ID Removal v0

## Status

Proposed and approved for immediate implementation after the second ORDER_178/179 live Qwen test on 2026-07-02.

## Trigger

Live result:

```text
failure_stage: R2
failure_type: schema_failed
failure_reason: R2 selected_graph_node_id must be in available_graph_node_ids
failure_payload_summary: {
  'selected_surface_id': 'surface:summary:data:source_leaf_summary:depth:1:info:relative',
  'selected_graph_node_id': 'graph:summary:source_leaf:example',
  'selected_surface_id_in_available': True,
  'selected_graph_node_id_in_available': False,
  'selected_graph_node_id_in_selected_surface': False
}
```

## Diagnosis

R2 copied the prompt's sample `selected_graph_node_id` value instead of copying a runtime candidate record's `graph_node_id`.

This is prompt example leakage, not a graph database read failure.

## Goal

Remove concrete fake graph IDs from the R2 prompt so the model cannot copy a plausible-looking example ID as if it were a real candidate.

## Scope

- Remove the JSON code block with concrete example IDs from `r2_vessel_node_selector_v0.md`.
- Replace it with a key contract written as field requirements.
- Keep the R2 validator strict.
- Add a regression test that the prompt does not contain the leaked example ID.

## Non-Goals

- Do not weaken R2 schema validation.
- Do not make code select a fallback candidate.
- Do not add R2a/R2b two-stage traversal yet.
- Do not change Neo4j data.

