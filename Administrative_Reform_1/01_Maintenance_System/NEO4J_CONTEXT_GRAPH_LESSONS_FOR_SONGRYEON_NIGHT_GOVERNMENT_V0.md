# Neo4j Context Graph Lessons For SongRyeon Night Government v0

## 1. Source Basis

This document records lessons from the user's requested study material:

- YouTube: `AI를 위한 지식그래프, Context Graph와 에이전트 메모리 이해하기 | Neo4j Agent Memory`
  - https://youtu.be/tcVK3ufL36E
- Neo4j Agent Memory official page
  - https://neo4j.com/labs/agent-memory/
- Neo4j developer article on context graphs and agent memory
  - https://neo4j.com/blog/developer/meet-lennys-memory-building-context-graphs-for-ai-agents/
- Neo4j context graph article
  - https://neo4j.com/blog/agentic-ai/context-graph-ai-agent-memory/
- Neo4j context graph video page
  - https://neo4j.com/videos/building-context-graphs-for-ai-agents-will-lyon-neo4j/

The video transcript was not fully imported. This document is therefore a design-learning note based on the public title/description and official Neo4j materials, not a verbatim lecture record.

## 2. Core Lesson

Context graph memory is not just a pile of documents, vectors, or summaries.

For SongRyeon Core, the important lesson is:

```text
Night Government is not a summarizer first.
Night Government is a controlled procedure that promotes short-term, long-term, and reasoning memory into a provenance-preserving context graph.
```

This aligns with SongRyeon Core's existing rule:

```text
absolute information -> relative/mixed information must preserve source coordinates.
```

## 3. Three Memory Layers

Neo4j Agent Memory frames agent memory as three connected layers:

```text
short-term memory
long-term memory
reasoning memory
```

SongRyeon mapping:

```text
short-term memory
  = recent raw conversation
  = TurnStateCapsule
  = raw_capsule graph nodes

long-term memory
  = raw_source graph nodes
  = source_kind_bundle
  = later entity/fact/preference/summary nodes

reasoning memory
  = trace/data records
  = L loop activity ledger
  = R graph access ledger
  = node_2 answer basis
  = node_4 gatekeeper results
  = future Night Government summary/review decisions
```

The most important warning is that reasoning memory must not be treated as an optional add-on.

Without reasoning memory, SongRyeon could remember "what was said" or "what entity exists" but fail to explain:

- why a node selected a route
- why L/R searched a path
- why a summary was approved or rejected
- whether a past reasoning pattern worked
- which evidence bundle supported a final answer

## 4. SongRyeon-Specific Design Rule

SongRyeon must be stricter than a generic agent memory library.

Every semantic memory node must preserve:

- generated_at
- generated_by
- model_id
- prompt_ref
- source_graph_node_ids
- source_data_ids
- source_trace_ids
- source_bundle_hash
- info_class
- source_mode
- claim_alignment
- semantic_judgement_status
- review_status

For example:

```text
raw_source/raw_capsule
  -> summary node
       generated_at=...
       generated_by=LLM:...
       info_class=relative or mixed
       source_bundle_hash=...
       review_status=not_reviewed/node4_passed/rejected
```

The summary node must never look like raw source truth.

## 5. What To Borrow

Borrow these patterns:

- context graph as memory substrate
- short-term / long-term / reasoning memory separation
- graph traversal plus semantic search
- provenance from question to answer
- multi-session persistence
- entity/fact extraction as a later layer
- reasoning trace as first-class graph material

## 6. What Not To Borrow Blindly

Do not blindly import:

- automatic entity extraction before provenance policy is stable
- LLM-generated summaries without node_4 review
- memory API calls that hide source record creation
- vector-first recall without graph source accounting
- facts/preferences that are not tied to raw source snapshots

## 7. Current SongRyeon Status

Already aligned:

- `raw_capsule`
- `raw_source`
- `source_kind_bundle`
- `source_ingest_time_bundle`
- `observed_at`
- `ingested_at`
- `content_sha1`
- `source_last_modified_at`
- L/R activity ledger foundation
- graph integrity audit
- source-kind separated manifest ingest

Still missing:

- external graph DB adapter
- export packet for graph records
- entity/fact extraction node
- Night Government summary node
- node_4 review/approval for memory promotion
- hybrid graph/vector retrieval
- R loop traversal over source ingest bundles

## 8. Next Design Implication

The next safe step is not to let an LLM freely summarize the entire project.

The safer sequence is:

```text
1. build export packet from existing DataStore graph records
2. define external graph DB adapter boundary
3. write source provenance and idempotency tests
4. only then add Night Government semantic summary workers
5. require node_4 review before promoted semantic memory becomes trusted
```

This keeps SongRyeon Core's philosophy intact:

```text
raw source first
coordinates first
review before trust
reasoning memory included from day one
```
