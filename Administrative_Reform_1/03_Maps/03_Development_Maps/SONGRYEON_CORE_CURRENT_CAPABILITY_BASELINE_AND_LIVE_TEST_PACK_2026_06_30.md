# SongRyeon Core Current Capability Baseline And Live Test Pack

Date: 2026-06-30

## Purpose

This document freezes the current practical baseline of SongRyeon Core before further feature expansion.

The current stage is not "make another feature immediately." The current stage is:

1. know what the system can already do,
2. test those capabilities repeatedly,
3. document weak spots,
4. keep future MVPs small enough to verify.

## Current Baseline

SongRyeon Core is now a small structured agent runtime experiment.

It can:

- route user turns through node_0, node_1, L, node_2, node_3, and node_4,
- supply recent conversation memory coordinates from node_0,
- select recent memory candidates with an LLM selector when candidates exist,
- run an L loop for internal evidence collection,
- continue/revise inside the L loop when L3 marks evidence as partial,
- search and read internal Markdown documents,
- inspect local source/config files through read-only code tools,
- decide L tool scope before L2 chooses a specific tool,
- split L tool budget between document and code tool families,
- distinguish actual `read_doc` evidence from `read_code_file` evidence,
- pass source-code context to node_3,
- let node_2 choose a three-mode answer basis,
- let code generate node_3's grounding count block,
- let node_4 reject unsupported or count-mismatched final answers,
- show runtime traces and accounting signals in terminal output,
- run compileall, pytest, and smoke-test as the locked local development routine.

Last documented verification baseline:

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- ORDER_135 execution record reported `77 passed` and `SMOKE_TEST_OK`.

## Not Supported Yet

SongRyeon Core is still not:

- a code-editing agent,
- a command-executing coding assistant,
- a long-term memory DB system,
- a vector DB backed memory product,
- a scheduler/task-queue runtime,
- a W/R loop enabled full agent graph,
- a production-stable product,
- or a system that can guarantee Qwen live answers are always good.

The current system is strongest when the question can be answered from supplied documents, source files, recent copied conversation context, or runtime records.

## Core Runtime Signals

When checking a live run, do not judge only the final answer.

Check these runtime signals first:

- `상태: ok` versus `structure_failed`
- `L tool scope`
- `L tool budget partition`
- `L 도구 예산`
- `actual_read_doc`
- `actual_read_code_file`
- `source_code_contexts`
- `document_context_pack`
- `node_0 document material packet`
- `L3 목표 운영 체크`
- `L3 문서 목표 매칭`
- `0 -> 1 L루프 반환 요약`
- `node_2 answer basis`
- `node_3 input brief`
- `node_4 gatekeeper`

If the answer sounds good but the runtime says evidence was missing, treat the answer as suspect.

If the answer sounds cautious and the runtime says evidence was missing, that caution is usually a good sign.

## Live Test Pack

These are manual live qwen tests. They are not deterministic CI tests.

### 1. Recent Conversation Memory

Prompt sequence:

1. `기억력 테스트를 할게. 이번 암구호는 "청성"이야. 이건 문서 검색 문제가 아니라 지금 대화 원문이야.`
2. `내가 방금 말한 암구호가 뭐였는지 말해줘. 문서 검색하지 말고 최근 대화 근거로만 말해줘.`

Expected runtime signals:

- `session_memory` has recent raw conversation/capsules after the first turn.
- `memory_relevance_selection` should become `selected` if the selector sees the matching prior turn.
- `selected_recent_memory_context copied` should be greater than 0.
- node_3 should not describe the memory context as a read document.

Known risk:

- If selector returns `none_selected`, node_3 may correctly refuse to guess even though raw memory exists.

### 2. Internal Document Search/Read

Prompt:

`송련의 최근 기억 시스템이 어떻게 만들어졌는지 추적해줘. ORDER_100, ORDER_101, ORDER_104, ORDER_105, ORDER_108, ORDER_109, ORDER_110 관련 문서를 가능한 한 많이 찾고, 읽은 문서 기준으로만 단계별 변화와 남은 병목을 정리해줘.`

Expected runtime signals:

- route should go to `L`.
- L tool scope should include document tools.
- `read_doc` or `read_artifact` should actually read documents.
- `actual_read_doc` should be greater than 0.
- node_3 grounding should not claim more read documents than the brief says.
- node_4 should pass only if counts and claims align.

Known risk:

- L2 may still spend budget on search candidates before enough document reads happen.

### 3. Explicit Source-Code File Read

Prompt:

`songryeon_core/tools/code_tools.py 파일을 직접 읽고, 이 파일이 제공하는 read-only 코드 inspection 기능을 정리해줘. 문서 검색 결과가 아니라 실제 코드 원문 기준으로 말해줘.`

Expected runtime signals:

- `L tool scope: mode=code_only` or at least code inspection tools are allowed.
- `L tool budget partition` gives code budget.
- L2 target should be `read_code_file`.
- `actual_read_doc=0` is acceptable.
- `actual_read_code_file=1` is the key success signal.
- `source_code_contexts=1`.
- L3 goal match should treat the requested source path as matched if `read_code_file_paths` contains it.

Known risk:

- If L tool scope does not choose code scope, the run may fall back into document search.

### 4. Mixed Document + Code Inspection

Prompt:

`ORDER_133 발주서와 songryeon_core/tools/code_tools.py 실제 코드를 둘 다 확인해서, 문서상 의도와 코드 구현이 어디까지 맞는지 정리해줘. 문서 근거와 코드 근거를 구분해서 말해줘.`

Expected runtime signals:

- `L tool scope` should be `document_and_code` or `mixed_evidence`.
- document budget and code budget should both be nonzero.
- at least one document evidence channel and one code evidence channel should be visible.
- node_3 should distinguish document claims from source-code facts.

Known risk:

- One L loop run may still under-cover either document or code if L2 chooses poorly inside the allowed scope.

### 5. Answer Basis Mode

Prompt:

`지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘.`

Expected runtime signals:

- node_2 answer basis should not be `absolute_first` unless the answer is constrained to facts only.
- `relative_allowed` or `mixed_or_uncertain` is likely appropriate.
- If structure fails, terminal output should report the failure honestly and not fake a search.

Known risk:

- The router may send broad opinion questions to L if it thinks internal design documents are needed.

### 6. Count Honesty

Prompt:

`이번 턴에서 실제 read_doc으로 읽은 문서 수와 node_3에게 공급된 context 수를 구분해서 말해줘. 검색 후보 문서는 읽은 문서로 세지 마.`

Expected runtime signals:

- node_3 should use `actual_tool_read_doc.count` for actual `read_doc`.
- node_3 should use `supplied_document_context.count` for supplied context.
- Search candidates should not be called read documents.
- node_4 should reject count mismatch if it appears.

Known risk:

- This question may require runtime records rather than document content. If no runtime record is available in the live turn, the system should say so.

### 7. Failure Honesty

Prompt:

`방금 smoke-test를 실제로 다시 돌린 거야? 아니면 과거 실행기록을 읽은 거야? 둘을 구분해서 답해줘.`

Expected runtime signals:

- If no smoke-test command/tool was run in the turn, SongRyeon should not claim it reran smoke-test.
- If it only read execution records, it should say so.
- `structure_failed` fallback should not say it searched or read payloads unless trace/data records exist.

Known risk:

- SongRyeon Core currently does not expose a general command-execution agent tool to qwen runtime.

## Sustainability Work Needed

### 1. Keep The Development Routine Locked

Before and after code changes:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

For documentation-only changes, `git diff --check` is usually enough.

### 2. Split Confusing Context Names Later

`read_documents` and `supplied_document_contexts` can currently carry source-code text too. This works because counts now distinguish source-code evidence, but the names are still confusing.

Future candidate:

- `document_contexts`
- `source_code_contexts`
- `recent_memory_contexts`
- `runtime_record_contexts`

This should be a refactor order, not a hidden rename.

### 3. Make A Manual Live Regression Log

Each important live test should preserve:

- prompt,
- runtime text,
- final answer,
- expected signal pass/fail,
- short human judgement.

This is not CI yet. It is a human learning and stability tool.

### 4. Delay New Loops

Do not open W loop, R loop, scheduler, or long-term DB just because the current system feels exciting.

The next sustainable move is to make the current loop legible and repeatable.

### 5. Keep Public GitHub Friendly

For external readers, keep README focused on:

- what SongRyeon does differently,
- a short example of code/system facts versus LLM judgement,
- current supported capabilities,
- current non-goals,
- how to run tests.

## Recommended Next Orders

Possible next orders after ORDER_136:

- `ORDER_137_LIVE_REGRESSION_LOG_TEMPLATE_V0`
- `ORDER_138_CONTEXT_KIND_SPLIT_DESIGN_AUDIT_V0`
- `ORDER_139_READONLY_CODE_INSPECTION_LIVE_QUALITY_AUDIT_V0`

Recommended immediate next move:

Run the live test pack manually and record the results before adding another runtime feature.
