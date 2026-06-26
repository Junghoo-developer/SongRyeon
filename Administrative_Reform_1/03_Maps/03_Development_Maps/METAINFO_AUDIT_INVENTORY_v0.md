# Metainfo Audit Inventory v0

**상태**: 개발 지도 기준 문서  
**작성일**: 2026-06-22  
**근거 발주서**: `ORDER_066_METAINFO_AUDIT_INVENTORY`  
**목표**: 기존 runtime/schema 출력 필드를 절대정보, 상대정보, 혼합정보로 분류하고 코드가 월권하지 않도록 기준선을 만든다.

## 감사 기준

이 문서는 `SCHEMA_METAINFO_POLICY_v0`를 따른다.

### 정보 등급

- `absolute`: 코드가 실행 중 확인하거나 강제할 수 있는 시스템 기준 정보.
- `relative`: 해석, 판단, 요약, 의도, 의미 설명.
- `mixed`: 상대/의미 판단이 여러 절대정보 source bundle에 근거하거나 특정 하나의 절대정보로 지정하기 불가능/부적절한 것. 출처가 있어도 진실 보장은 아니다.

### 생성자

- `CODE`: 코드가 생성하거나 기록했다.
- `LLM`: LLM이 생성했다.
- `TOOL`: 도구 결과에서 왔다.
- `DOCUMENT`: 문서 원문에서 왔다.
- `USER`: 사용자 입력에서 왔다.
- `UNKNOWN`: 현재 출처가 충분히 분리되어 있지 않다.

### 코드 권한

- `code_write_allowed=yes`: 코드가 새로 써도 된다.
- `code_write_allowed=no`: 코드가 의미문을 새로 쓰면 안 된다.
- `code_copy_allowed=yes`: 코드가 원문을 복사할 수 있다. 단, `copied_from`이 필요하다.
- `code_copy_allowed=no`: 코드가 복사 대상도 아니다.

## 전체 결론

현재 구조에서 가장 위험한 필드는 다음이다.

| 필드 계열 | 현재 문제 | 처리 방향 |
| --- | --- | --- |
| `compression_summary` | 코드가 자연어 압축 설명을 씀 | `evidence_trace_count`, `packet_mode` 같은 절대정보로 격하 |
| `route_reason` | 코드 라우터가 라우팅 이유를 씀 | Node1 LLM 전까지 `route_rule_id`, `matched_keywords`, `policy_flag`로 격하 |
| `macro_goal_reason`, `micro_goal_reason` | L1이 목표 이유를 코드로 씀 | L1 LLM 출력으로 이전 |
| `ToolChoiceFrame.reason`, `expected_use` | 도구 선택 의미를 코드가 설명 | `tool_choice_policy_id`, `selected_tool_name` 중심으로 격하 |
| `ToolUseBudgetFrame.reason` | 예산 상태 설명을 코드가 자연어로 씀 | `stop_reason`, counts, flags 중심으로 격하 |
| `LLoopControlFrame.reason` | controller 판단 이유를 코드가 자연어로 씀 | `decision`, `condition_flags` 중심으로 격하 |
| `L3AchievementFrame.*reason` | L3 달성 판단 이유를 코드가 씀 | L3 LLM 판단으로 이전 |
| `ReportFrame.rendered_markdown` | 현재 최종 보고를 코드가 렌더링 | Node3 LLM 보고문 전까지 `CODE/RENDERER` 명시 |

## 감사 표

### MemoryPacketPayload

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `packet_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `target` | absolute | CODE | yes | no | not_run | 유지 |
| `mode` | absolute | CODE | yes | no | not_run | 유지 |
| `compression_summary` | mixed-risk | CODE | no | no | not_run | 제거 또는 운영 라벨로 격하 |
| `generated_by` | absolute | CODE | yes | no | not_run | 유지 |
| `llm_semantic_summary_status` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `evidence_trace_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `insufficient_signal_id` | absolute | CODE | yes | no | not_run | 유지 |
| `memory_items[].item_id` | absolute | CODE | yes | no | not_run | 유지 |
| `memory_items[].item_type` | absolute | CODE | yes | no | not_run | 유지 |
| `memory_items[].text` | mixed-risk | CODE | no | conditional | not_run | 코드 생성 설명이면 제거, 원문 복사면 `copied_from` 필요 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### RoutingDecisionFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `frame_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `route` | absolute/mixed-boundary | CODE | yes as enum | no | not_run | Node1 LLM 뒤에는 LLM 선택값을 코드가 검증만 함 |
| `route_reason` | mixed-risk | CODE | no | yes if LLM | not_run currently | Node1 LLM 출력으로 이전 |
| `expected_next_0_mode` | absolute | CODE | yes | no | not_run | 유지 |
| `route_source` | absolute | CODE | yes | no | not_run | 유지 |
| `llm_routing_status` | absolute | CODE | yes | no | not_run | 유지 |
| `required_schema` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### L1GoalFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `frame_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `macro_goal` | mixed-risk | CODE | no | yes if LLM | not_run currently | L1 LLM 출력으로 이전 |
| `macro_goal_reason` | mixed-risk | CODE | no | yes if LLM | not_run currently | L1 LLM 출력으로 이전 |
| `micro_goal` | mixed-risk | CODE | no | yes if LLM | not_run currently | L1 LLM 출력으로 이전 |
| `micro_goal_reason` | mixed-risk | CODE | no | yes if LLM | not_run currently | L1 LLM 출력으로 이전 |
| `goal_source` | absolute | CODE | yes | no | not_run | `LLM:qwen3:14b` 또는 `CODE:FALLBACK` 구분 필요 |
| `target_loop` | absolute | CODE | yes | no | not_run | 유지 |
| `goal_generation_source` | absolute | CODE | yes | no | not_run | 유지 |
| `llm_goal_judgement_status` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### L2QueryPlanFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `frame_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `planner_mode` | absolute | LLM/CODE | yes as label | no | not_run | 유지 |
| `selected_candidate_id` | absolute/mixed-boundary | LLM then CODE validation | no except fallback | yes if LLM | LLM ran if present | LLM 출처 유지 |
| `candidates[].candidate_id` | absolute | LLM/CODE validation | no except fallback | yes if LLM | LLM ran if present | 유지 |
| `candidates[].query_text` | mixed | LLM | no | yes | LLM ran | 유지, `llm_call` 연결 |
| `candidates[].purpose` | mixed | LLM | no | yes | LLM ran | 유지, Node2 혼합정보 후보 |
| `candidates[].expected_signal` | mixed | LLM | no | yes | LLM ran | 유지 |
| `candidates[].priority` | absolute | LLM/CODE validation | no except fallback | yes if LLM | LLM ran if present | 유지 |
| `candidates[].target_tool_name` | absolute | LLM/CODE validation | yes as allowed enum | yes if LLM | not_run | 검증 유지 |
| `candidates[].source_data_ids` | absolute | CODE/LLM | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### ToolChoiceFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `choice_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `chooser_node_id` | absolute | CODE | yes | no | not_run | 유지 |
| `tool_name` | absolute | CODE | yes as enum | no | not_run | 유지 |
| `reason` | mixed-risk | CODE | no | yes if LLM | not_run currently | `tool_choice_policy_id`로 격하 또는 LLM 출력으로 이전 |
| `expected_use` | mixed-risk | CODE | no | yes if LLM | not_run currently | 제거/격하 |
| `catalog_id` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### ToolUseBudgetFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `budget_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `loop_id` | absolute | CODE | yes | no | not_run | 유지 |
| `sequence_index` | absolute | CODE | yes | no | not_run | 유지 |
| `max_tool_calls`, `max_query_candidates`, `max_read_doc_calls`, `max_input_chars` | absolute | CODE | yes | no | not_run | 유지 |
| `tool_call_count`, `query_count`, `read_doc_count`, `input_chars_used` | absolute | CODE | yes | no | not_run | 유지 |
| `executed_queries` | absolute/mixed-source | CODE copies query | no if LLM query | yes | not_run | query 출처를 함께 표시 |
| `read_doc_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `cache_statuses` | absolute | TOOL/CODE | yes | no | not_run | 유지 |
| `duplicate_query_count`, `duplicate_doc_count` | absolute | CODE | yes | no | not_run | 유지 |
| `stop_reason` | absolute status label | CODE | yes | no | not_run | 유지 |
| `reason` | mixed-risk | CODE | no | no | not_run | `condition_flags`로 격하 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### LLoopControlFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `control_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `loop_id` | absolute | CODE | yes | no | not_run | 유지 |
| `iteration_index` | absolute | CODE | yes | no | not_run | 유지 |
| `decision` | absolute status label | CODE | yes as enum | no | not_run | 유지 |
| `reason` | mixed-risk | CODE | no | no | not_run | `decision_condition_flags`로 격하 |
| `max_iterations`, `max_tool_calls`, `tool_call_count` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `selected_tool_name` | absolute | CODE | yes as enum | no | not_run | 유지 |
| `query_text` | mixed if LLM query | LLM/CODE fallback | no except fallback | yes | LLM ran if planned | 출처 표시 필요 |
| `doc_id` | absolute | TOOL/CODE | yes | no | not_run | 유지 |
| `failure_signal_id` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### L3AchievementFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `frame_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `achievement_status` | mixed-risk | CODE | no | yes if LLM | not_run currently | L3 LLM 출력으로 이전 |
| `reason` | mixed-risk | CODE | no | yes if LLM | not_run currently | L3 LLM 출력으로 이전 |
| `target_goal_data_id` | absolute | CODE | yes | no | not_run | 유지 |
| `preserved_info_frame_id` | absolute | CODE | yes | no | not_run | 유지 |
| `candidate_count` | absolute | CODE | yes | no | not_run | 유지 |
| `evidence_trace_ids`, `evidence_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `final_control_data_id` | absolute | CODE | yes | no | not_run | 유지 |
| `controller_decision` | absolute status label | CODE | yes | no | not_run | 유지 |
| `achievement_generation_source` | absolute | CODE | yes | no | not_run | 유지 |
| `llm_semantic_judgement_status` | absolute | CODE | yes | no | not_run | 유지 |
| `target_macro_goal`, `target_micro_goal` | mixed if LLM goal | CODE currently | no | yes | not_run currently | L1 LLM 뒤 출처 표시 |
| `macro_achievement_status`, `micro_achievement_status` | mixed-risk | CODE | no | yes if LLM | not_run currently | L3 LLM 출력으로 이전 |
| `macro_achievement_reason`, `micro_achievement_reason` | mixed-risk | CODE | no | yes if LLM | not_run currently | L3 LLM 출력으로 이전 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### MetainfoBoundary

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `absolute_info` | absolute | CODE | yes | no | not_run | 유지 |
| `relative_info` | relative | currently empty | no | yes if LLM/USER/DOCUMENT | not_run currently | Node2 LLM에서 사용 |
| `mixed_info` | mixed | CODE selects from records | no for semantic text | yes from approved source | not_run currently | Node2 LLM 분류 뒤 강화 |

### MixedInfoRef

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `info_id` | absolute | CODE | yes | no | not_run | 유지 |
| `source_data_id` | absolute | CODE | yes | no | not_run | 유지 |
| `field_path` | absolute | CODE | yes | no | not_run | 유지 |
| `info_kind` | absolute label | CODE | yes | no | not_run | 유지 |
| `text` | mixed | LLM/CODE risk/DOCUMENT | no | yes with provenance | depends on source | 코드 생성 자연어는 기본 제외 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

### ReportFrame

| 필드 | 등급 | 현재 생성자 | 코드 새 작성 | 코드 복사 | 의미판단 | 조치 |
| --- | --- | --- | --- | --- | --- | --- |
| `report_id` | absolute | CODE | yes | no | not_run | 유지 |
| `turn_id` | absolute | CODE | yes | no | not_run | 유지 |
| `rendered_markdown` | mixed/report | CODE currently | no after Node3 LLM | yes if LLM/DOCUMENT | not_run currently | Node3 LLM 출력으로 이전 |
| `allowed_info_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `allowed_mixed_info_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `source_trace_ids`, `source_data_ids` | absolute | CODE | yes | no | not_run | 유지 |
| `schema_name`, `schema_version` | absolute | CODE | yes | no | not_run | 유지 |

## 코드가 새로 쓰면 안 되는 필드 목록

다음 필드는 코드가 자연어 의미문을 새로 쓰면 안 된다.

- `MemoryPacketPayload.compression_summary`
- `MemoryItem.text`
- `RoutingDecisionFrame.route_reason`
- `L1GoalFrame.macro_goal`
- `L1GoalFrame.macro_goal_reason`
- `L1GoalFrame.micro_goal`
- `L1GoalFrame.micro_goal_reason`
- `L2QueryPlanCandidate.query_text`
- `L2QueryPlanCandidate.purpose`
- `L2QueryPlanCandidate.expected_signal`
- `ToolChoiceFrame.reason`
- `ToolChoiceFrame.expected_use`
- `ToolUseBudgetFrame.reason`
- `LLoopControlFrame.reason`
- `L3AchievementFrame.achievement_status`
- `L3AchievementFrame.reason`
- `L3AchievementFrame.macro_achievement_status`
- `L3AchievementFrame.macro_achievement_reason`
- `L3AchievementFrame.micro_achievement_status`
- `L3AchievementFrame.micro_achievement_reason`
- `MixedInfoRef.text`
- `ReportFrame.rendered_markdown`

예외:

1. 코드 fallback 상태를 기록할 때는 enum/status label만 쓴다.
2. 코드가 원문을 복사할 때는 `copied_from`, `selection_method`, `truncated`를 기록한다.
3. 테스트용 fake LLM 출력은 실제 LLM이 아니므로 `fake_adapter`임을 표시한다.

## 다음 발주서에 주는 제약

### ORDER 067

코드가 쓰는 자연어를 제거하거나 status label로 낮춘다.  
이 문서의 "코드가 새로 쓰면 안 되는 필드 목록"을 우선순위 목록으로 사용한다.

### ORDER 069

`route_reason`은 Node1 LLM이 작성해야 한다.  
코드는 `route`, `source_data_ids`, schema status만 검증한다.

### ORDER 070

L1 목표와 목표 이유는 LLM이 작성해야 한다.  
코드는 fallback일 때만 운영 라벨을 쓴다.

### ORDER 071

L3 달성 여부와 이유는 LLM이 작성해야 한다.  
코드는 후보 수, 도구 종료 상태, controller decision만 기록한다.

### ORDER 072

Node2는 코드 생성 자연어를 기본 혼합정보 후보에서 제외한다.  
LLM, 문서, 사용자 입력, 도구 발췌에서 온 자연어를 우선 후보로 삼는다.

### ORDER 073

최종 보고문은 Node3 LLM 출력이어야 한다.  
코드 렌더러는 LLM reporter가 `not_run`일 때만 임시 출력으로 허용한다.

### ORDER 074

Node4는 위반 필드를 잡는 gatekeeper가 된다.  
특히 코드 생성 자연어가 LLM 출력처럼 보이면 reject해야 한다.
