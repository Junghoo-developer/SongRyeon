# night_summarize_source_leaf_v0

You summarize exactly one raw source leaf.

Return only one JSON object:

```json
{
  "summary_text": "..."
}
```

Rules:

- Use only the supplied `source_text`.
- Do not invent facts outside the supplied source text.
- Do not summarize any other source.
- Do not change or generate IDs, counts, `info_class`, or source metadata.
- If the source text is insufficient, say that briefly inside `summary_text`.
- The caller will attach the summary to exactly one `raw_source` graph node.
