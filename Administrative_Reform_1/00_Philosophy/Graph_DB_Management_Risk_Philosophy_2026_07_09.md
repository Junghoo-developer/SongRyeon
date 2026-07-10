# Graph DB Management Risk Philosophy

Date: 2026-07-09

## Status

This is a philosophy note.

It is not an implementation order. It exists so future Vessel graph DB work does
not accidentally turn old summaries, missing provenance, or mixed hierarchy into
trusted memory.

## Core Warning

The graph DB is not safe merely because it stores many nodes.

It becomes safe only when every node can answer these questions:

1. What source did this come from?
2. When was the source observed?
3. When was this node or summary generated?
4. Which run generated it?
5. Is the source still current?
6. Is the summary still active?
7. Is this node raw/original material, a one-source relative summary, or a
   multi-source mixed summary?

If one of these answers is missing, the node should not be silently trusted as
fresh evidence.

## Dangerous Elements

### 1. Legacy summaries without run provenance

Old summary nodes may not directly record fields such as:

- `summary_run_id`
- `night_turn_id`
- `night_batch_id`
- `summary_created_at`

This does not mean they are false or invalid. It means the exact night run that
created them is not directly visible from the summary payload.

Risk:

- R traversal may read an old summary as if it were fully current.
- invalidation logic may not know whether a summary belongs to a specific night
  run.

Rule:

- Do not invalidate legacy summaries merely because run provenance is missing.
- Mark or audit them separately as legacy provenance cases.
- If source links exist, use source lineage rather than run provenance alone.

### 2. Source links missing or ambiguous

A summary is safer when it records:

- `target_graph_node_id`
- `source_graph_node_ids`
- `source_data_ids`
- `source_trace_ids`
- `content_sha1` for raw source summaries

Risk:

- If source links are missing, code cannot know which source change should
  invalidate the summary.
- R loop may treat a source-less summary as normal graph memory.

Rule:

- Missing source links should become an audit status, not silent trust.
- Do not fabricate source links after the fact unless the trace/DataStore path
  proves them.

### 3. Provenance absence confused with invalidity

No provenance is not the same as false information.

Risk:

- A cleanup pass could destroy useful historical summaries just because they
  were created before newer schema fields existed.

Rule:

- Separate `validity_status` from `run_provenance_status`.
- `legacy_not_recorded` should mean "old format," not "bad summary."
- Only source change, explicit rejection, or schema-grounded invalidation should
  change semantic validity.

### 4. Stale active summaries

A summary can remain marked `active` even after its source changed if the source
lineage or invalidation ledger did not connect the change to that summary.

Risk:

- R traversal may use stale summary text as answer material.

Rule:

- Source version lineage and summary invalidation ledger must be checked before
  treating summaries as current.
- R read packets should prefer `validity_status=active` and expose when validity
  is unknown or legacy.

### 5. Mixed child layers treated as clean hierarchy

A child layer can contain different data kinds or different summary roles.

Risk:

- R2/R3 may see a mixed layer and choose based on a noisy surface.
- A prompt-time cap or sample would hide this problem instead of fixing it.

Rule:

- Do not randomly trim mixed layers.
- Report `needs_more_hierarchy` when summary children are structurally mixed.
- Build intermediate summary layers rather than pretending a subset represents
  the whole layer.

### 6. Raw/original material leaked as summary material

Raw nodes and summary nodes have different authority.

Risk:

- R3 may think it inspected original material when it only saw a summary preview.
- Final answers may overclaim evidence strength.

Rule:

- Keep raw/original reads behind explicit raw read policy.
- Child summary previews are navigation evidence, not raw evidence.
- Runtime and final answer material should distinguish raw, relative summary,
  and mixed summary.

### 7. DataStore and Neo4j drift

The local DataStore and Neo4j Vessel can disagree if writes fail, are partial, or
use an older export packet.

Risk:

- Code may believe the graph contains records that Neo4j does not have.
- Neo4j may contain old records that the current DataStore run did not inspect.

Rule:

- Vessel write results and readback results are absolute evidence.
- A graph read should report which database, namespace, export packet, and
  readback status it used.
- Do not assume Neo4j is current without readback or inspect evidence.

### 8. Deterministic ID collision or reuse with changed payload

Deterministic IDs are useful, but dangerous if the payload behind an ID changes
without versioning.

Risk:

- A node ID can appear stable while its meaning changed.

Rule:

- If content changes, create a new version node or lineage record.
- Do not overwrite historical payloads silently.
- Same ID with different payload should be treated as a collision unless a
  versioning rule explicitly allows it.

### 9. Review status confused with validity

`review_status=not_reviewed` does not mean invalid.

Risk:

- Human review and source validity can be mixed together.

Rule:

- `validity_status` answers whether the source relationship is still current.
- `review_status` answers whether a human or reviewer accepted the summary.
- These must remain separate.

### 10. Relative and mixed summaries collapsed into one memory type

Source leaf summaries are usually one-source relative information.
Higher bundle summaries are usually mixed information.

Risk:

- R traversal may use a mixed summary as if it were one-source evidence.
- Final answers may hide uncertainty.

Rule:

- Preserve `info_class`.
- Preserve `source_mode` or equivalent source-bundle fields.
- Do not promote mixed summaries to absolute facts.

## Safe Handling of Existing Graph Records

Existing graph records should be handled conservatively:

1. Do not delete them.
2. Do not bulk-invalidate them.
3. Do not silently rewrite their payloads.
4. Audit their provenance and source links.
5. If recoverable from trace/DataStore, mark them as backfill candidates.
6. If not recoverable, keep them as legacy records with lower trust or explicit
   unknown provenance.

## Future Audit Categories

Future graph maintenance should classify summaries into categories like:

- `provenance_recorded`
- `legacy_not_recorded`
- `backfill_possible_from_trace`
- `source_links_present`
- `source_links_missing`
- `active_source_lineage_confirmed`
- `invalidated_by_source_change`
- `needs_more_hierarchy`
- `raw_layer_requires_explicit_read`

These are operational status labels. They should not become semantic claims
about whether a summary is "true."

## Implementation Direction

A safe implementation sequence is:

1. Add explicit run provenance fields to new summary frames.
2. Add a legacy provenance audit ledger for old summaries.
3. Add graph hierarchy audit that reports mixed child layers.
4. Add intermediate hierarchy creation only after the audit shows where it is
   needed.
5. Make R read packets prefer active, source-linked, clean-layer summaries.

Do not start by deleting or invalidating old graph nodes.
