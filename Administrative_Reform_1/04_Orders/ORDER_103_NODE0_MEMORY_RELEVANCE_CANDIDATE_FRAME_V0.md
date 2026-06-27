# ORDER 103: Node0 Memory Relevance Candidate Frame v0

## 상태

구현 및 검증 완료.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_103_node0_memory_relevance_candidate_frame_2026_06_26_001.md`

이 발주서는 ORDER_100/101 다음 단계다.
장기기억 DB나 관련성 selector를 만들기 전에, 최근 원문 대화와 capsule 대응 좌표를 나중의 관련성 판단 후보 frame으로 보존한다.

## 목표

0 기억공급관이 최근 8턴 raw conversation + `TurnStateCapsule` alignment를 보고, 관련성 판단을 직접 하지 않은 상태의 후보 frame을 `memory_packet`에 넣는다.

핵심 문장:

```text
0은 관련성을 판단하지 않는다.
0은 "나중에 관련성 판단자가 볼 수 있는 후보 좌표"만 만든다.
```

이 제한은 이번 MVP의 일시적 경계다.
송련이 장기적으로 관련성 판단을 하면 안 된다는 뜻이 아니다.

## 현재 코드 사실

- ORDER_100에서 최근 3턴 `previous_turn_capsule_index` memory item이 생겼다.
- ORDER_101에서 최근 8턴 `recent_raw_conversation_capsule_alignment` memory item이 생겼다.
- alignment 기준은 오직 `recent_raw_conversation entry.turn_id == TurnStateCapsule.turn_id`다.
- 현재 0의 `llm_semantic_summary_status`는 `not_run`이다.
- 관련성 선택, 요약, 장기 DB, vector DB는 아직 열지 않았다.

## 문제

최근 대화와 capsule의 좌표는 생겼지만, 나중에 LLM selector가 관련성 판단을 남길 구조화 슬롯은 아직 없다.

이 슬롯 없이 바로 selector를 붙이면 다음 위험이 생긴다.

```text
0이 관련성 판단을 한 것처럼 보일 수 있다.
판단 결과가 어떤 raw/capsule 좌표에서 나왔는지 흐려질 수 있다.
상대정보/혼합정보 분류를 나중에 붙이기 어려워진다.
```

## 구현 범위

### 1. Candidate frame schema

다음 필드를 가진 frame을 둔다.

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

`not_run` 상태에서는 `judged_by`, `relevance_label`, `relevance_reason`, `info_class`가 반드시 비어 있어야 한다.

### 2. 생성 기준

candidate frame은 `recent_raw_conversation_capsule_alignment` item과 같은 기준으로 만든다.

```text
recent_raw_conversation entry.turn_id == TurnStateCapsule.turn_id
```

turn_id가 맞지 않으면 후보를 만들지 않는다.
순서, 키워드, 문자열 유사도, embedding 점수로 억지 연결하지 않는다.

### 3. memory packet 위치

`memory_packet:node_1:pre_route_report` payload에 다음 리스트를 추가한다.

```text
relevance_candidate_frames=[...]
```

기존 `memory_items`는 유지한다.
candidate frame은 alignment item을 대체하지 않는다.

## 비범위

이번 발주에서 하지 않는 것:

```text
관련성 판단
관련성 점수화
관련성 이유 작성
이전 턴 요약
장기기억 DB
vector DB
memory graph
scheduler
W/R loop
node_4 요약 승인 루프
```

## Smoke-test 요구

다음 검사를 추가한다.

```text
1. 최근 raw conversation 9턴과 capsule 9턴을 주입하면 최근 8턴만 candidate frame이 된다.
2. candidate frame은 alignment item을 source_memory_item_id로 가리킨다.
3. judgement_status는 not_run이다.
4. judged_by, relevance_label, relevance_reason, info_class는 None이다.
5. source_trace_ids는 capsule 안에 실제 존재하는 user/final trace anchor만 담는다.
6. source_data_ids는 []다.
7. turn_id mismatch raw/capsule은 candidate frame이 되지 않는다.
8. llm_semantic_summary_status=not_run이 유지된다.
```

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- candidate frame을 어디에 저장했는지.
- 후보 생성 기준이 무엇인지.
- 관련성 판단을 하지 않았음을 어떻게 보장했는지.
- 기존 ORDER_100/101 memory item이 유지되는지.
- compileall / smoke-test 결과.
