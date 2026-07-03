# ORDER 199 R Vessel Answer Demo Route Implementation

Date: 2026-07-03

## Summary

ORDER 199 is implemented.

SongRyeon Core now has a narrow manual CLI route that runs:

```text
user question
-> node_0 Vessel R start handoff
-> Vessel R traverse
-> R Vessel activity ledger
-> node_0 R return packet
-> node_2 handoff / boundary / answer-basis
-> node_3 input brief and report
-> node_4 gatekeeper
-> final demo renderer
```

Elementary explanation:

```text
R finds graph-memory material.
0 labels what happened.
3 writes a demo answer using the R material.
4 checks that the answer does not lie about the material.
```

This is a manual demo route only. It does not enable default `route=R` in live chat.

## Code Changes

- `songryeon_core/runtime/r_loop_vessel_answer_demo.py`
  - Added `run_local_r_loop_vessel_answer_demo(...)`.
  - Added `render_r_loop_vessel_answer_demo_text(...)`.
  - Records read packet, start handoff, traverse result, activity ledger, return packet, raw-capsule activity link, node_2 handoff, node_3 brief/report, and node_4 gatekeeper frame.
  - Provides safe blocking output if node_4 does not pass.
  - Optional `--write-trace-cache` stores trace/data JSON under `.songryeon_core_cache/vessel_r_answer_demo/`.

- `main.py`
  - Added CLI:

```powershell
python main.py vessel-r-answer-demo "질문" --database neo4j --llm-mode fake --format text
python main.py vessel-r-answer-demo "질문" --database neo4j --llm-mode qwen --timeout 180 --format text
```

- `songryeon_core/llm/fake.py`
  - The deterministic fake node_3 reporter now recognizes `vessel_r_material`.
  - It describes the material as graph-memory material, not as document/read tool evidence.
  - Failed R material is reported as limited state, not as completed traversal.

- `songryeon_core/nodes/node_3_reporter.py`
  - Adjusted the Vessel R failed-material limit wording so node_4's conservative success-claim guard does not misread a negated success phrase.

- `tests/test_order_199_r_vessel_answer_demo_route.py`
  - Added fake success demo route test.
  - Added failed R traversal partial/safe answer test.
  - Added return-packet-to-node_3 material source test.
  - Added node_4 overclaim guard test.

## Boundaries Preserved

- Default live chat does not automatically route through R.
- node_1 router policy was not changed.
- The demo route does not write new Vessel graph nodes.
- No scheduler or autonomous background R was added.
- No semantic search over graph nodes was added.
- Existing `vessel-r-traverse` remains available.
- node_4 guard was not weakened.

## Verification

Passed:

```powershell
python -m pytest tests/test_order_199_r_vessel_answer_demo_route.py -q
python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py tests/test_order_194_r_vessel_start_handoff.py tests/test_order_195_r_vessel_activity_ledger.py tests/test_order_196_r_vessel_activity_raw_capsule_link.py tests/test_order_197_r_vessel_continuation_checkpoint.py tests/test_order_198_r_vessel_return_packet.py tests/test_order_199_r_vessel_answer_demo_route.py -q
python -m compileall songryeon_core main.py
git diff --check
python main.py smoke-test
python -m pytest -q
python -m pytest tests/test_import_baseline.py tests/test_order_199_r_vessel_answer_demo_route.py -q
```

Observed result:

```text
ORDER 199 focused: 4 passed
ORDER 193-199 related: 25 passed
compileall: passed
git diff --check: passed
smoke-test final rerun: SMOKE_TEST_OK
full pytest rerun: 304 passed in 708.29s (0:11:48)
post-import-baseline focused rerun: 5 passed
```

Observed transient issues:

```text
full pytest first attempt: timeout after about 10 minutes with no final result
smoke-test first attempt: transient KeyError in document_memory_index for a newly present philosophy doc
smoke-test rerun: passed without code changes
```

The smoke failure did not reproduce. A direct snapshot/list audit showed the new philosophy document was present in both document listing and snapshot hash data. The final smoke run included `document_memory_index_docs=453` and passed.

## Remaining Work

ORDER 199 proves the narrow manual answer path:

```text
Vessel R material
-> node_0 return packet
-> node_3 brief/report
-> node_4 guard
```

It still does not connect R to normal `qwen-chat` routing. That should remain a later order after more live audits.
