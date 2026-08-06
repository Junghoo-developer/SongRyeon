# Invalidated pre-registered run

This public freeze was committed before any live output at Git commit
`f6abff39662a12cbbb6e6f40ec0dbbc894605c60`.

All 216 planned local `gemma4:26b` executions were attempted. The raw capture
matrix contained 215 completed rows and one preserved failed row. Before any
score was created or the blind mapping was revealed, the trusted packetizer
rejected the run.

The verifier incorrectly required a completed answer string to occur in
exactly one `node3_answer` record. A valid Node4 retry can create the same text
more than once while `final_delivery` still points to exactly one answer by
its `information_id`. Six rows triggered this instrumentation defect.

No `BLIND_SCORES.json`, `SCORE_LOCK.json`, `REVEAL.json`, `SUMMARY.json`, or
performance claim was produced from this attempt. The raw outputs remain
private. The verifier was changed to follow the recorded final-delivery ID,
covered by a regression test, and the complete experiment is rerun under a
new public freeze.
