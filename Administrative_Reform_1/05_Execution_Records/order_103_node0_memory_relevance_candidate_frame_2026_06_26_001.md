# ORDER_103 Node0 Memory Relevance Candidate Frame 실행 기록

## 작업 일시

2026-06-26

## 목표

장기기억 DB나 관련성 selector를 열기 전에, 최근 raw conversation + `TurnStateCapsule` alignment를 나중의 관련성 판단 후보 frame으로 `memory_packet`에 보존한다.

이번 작업의 경계는 다음이다.

```text
0은 관련성 판단을 하지 않는다.
0은 나중에 판단자가 볼 수 있는 후보 좌표만 남긴다.
```

## 변경 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/smoke_test.py`
- `songryeon_core/runtime/terminal_view.py`
- `Administrative_Reform_1/04_Orders/ORDER_103_NODE0_MEMORY_RELEVANCE_CANDIDATE_FRAME_V0.md`

## 구현 내용

### 1. MemoryRelevanceCandidateFrame 추가

`MemoryPacketPayload`에 `relevance_candidate_frames`를 추가했다.

각 frame은 다음 필드를 가진다.

```text
frame_id
turn_id
candidate_turn_id
source_memory_item_id
source_trace_ids
source_data_ids
judgement_status=not_run
judged_by=None
relevance_label=None
relevance_reason=None
info_class=None
schema_name=MemoryRelevanceCandidateFrame
schema_version=0.1
```

`MemoryPacketPayload.schema_version`은 새 구조화 필드 추가를 반영해 `0.2`로 올렸다.

### 2. not_run guard

`validate_memory_relevance_candidate_frame()`을 추가했다.

현재 v0에서는 `judgement_status=not_run`만 허용한다.
또한 `not_run` 상태에서 다음 필드가 채워지면 validation 실패가 난다.

```text
judged_by
relevance_label
relevance_reason
info_class
```

이는 0이 관련성 판단을 한 것처럼 보이는 일을 막기 위한 guard다.

### 3. 후보 생성 기준

`build_recent_memory_relevance_candidate_frames()`를 추가했다.

후보 생성 기준은 ORDER_101 alignment와 동일하다.

```text
recent_raw_conversation entry.turn_id == TurnStateCapsule.turn_id
```

turn_id가 맞지 않으면 candidate frame을 만들지 않는다.
순서, 키워드, 문자열 유사도, embedding 점수 같은 fallback은 넣지 않았다.

### 4. pre_route_report 배선

`run_dry_turn()`의 `memory_packet:node_1:pre_route_report`에 candidate frame을 붙였다.

기존 item은 유지된다.

```text
trace_evidence
previous_turn_capsule_index
recent_raw_conversation_capsule_alignment
```

candidate frame은 alignment item을 대체하지 않고, `source_memory_item_id`로 alignment item을 가리킨다.

### 5. runtime 표시

`terminal_view.py`에서 memory packet 줄에 `relevance_candidates N개`를 표시하게 했다.

## Smoke 확인값

`python main.py smoke-test` 결과에 다음 값이 추가됐다.

```text
recent_memory_relevance_candidate_window=8
recent_memory_relevance_candidate_count=8
recent_memory_relevance_candidate_judgement=not_run
recent_memory_relevance_candidate_skips_mismatch=true
```

기존 ORDER_100/101 확인값도 유지된다.

```text
recent_capsule_read_window=3
recent_capsules_read_count=3
recent_raw_conversation_alignment_window=8
recent_raw_conversation_alignment_count=8
recent_raw_conversation_alignment_skips_mismatch=true
recent_raw_conversation_alignment_llm_summary_status=not_run
```

## 검증

```powershell
python -m compileall .\songryeon_core .\main.py
```

통과.

```powershell
python .\main.py smoke-test
```

통과.

최종 상태:

```text
SMOKE_TEST_OK
```

## 비범위 유지

이번 작업에서 다음은 하지 않았다.

- 관련성 판단
- 관련성 점수화
- 관련성 이유 작성
- 이전 턴 의미 요약
- 장기기억 DB
- vector DB
- memory graph
- scheduler
- W/R loop
- node_4 요약 승인 루프

## 남은 위험

후보 frame은 아직 판단자가 소비하지 않는다.
다음 단계에서 LLM selector를 열 경우, selector의 판단 결과는 `judged_by`, `relevance_label`, `relevance_reason`, `info_class`를 채우되, 그 판단이 상대정보인지 혼합정보인지 별도 설계가 필요하다.
