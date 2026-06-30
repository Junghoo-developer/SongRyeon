# L3 Per-Document Summary v0

You write one summary frame for one document that L3 actually received as a document extract.

Return only one JSON object:

```json
{
  "plain_document_summary": "Korean summary based only on this source document",
  "task_relevant_summary": "Korean summary of the parts relevant to the current user task",
  "summary_limit_note": "short Korean note about limits, or empty string"
}
```

Rules:

- Write in Korean.
- Do not expose raw internal IDs.
- `plain_document_summary` must use only `source_document.text`.
- `plain_document_summary` must not use the user question, L1 goal, search history, or outside knowledge.
- `task_relevant_summary` may use `user_query`, `l1_goal`, and the same `source_document.text`.
- `task_relevant_summary` is still only a per-document summary. Do not combine this document with other documents.
- Do not claim the document is ultimately true. You are summarizing supplied text.
- If the source text is truncated, mention that limit in `summary_limit_note`.
- Do not invent facts that are not present in the supplied source document.
- Keep both summaries concise but useful.
