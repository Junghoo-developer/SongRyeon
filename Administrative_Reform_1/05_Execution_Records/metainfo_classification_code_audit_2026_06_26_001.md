# Metainfo Classification Code Audit 2026-06-26 001

## 상태

감사 보고서 작성 완료.

이번 작업은 코드 수정이 아니다.
상대정보/혼합정보 정의 정정 이후, 현재 코드가 새 기준과 어긋나는 지점을 찾는 감사만 수행했다.

## 감사 기준

정정된 기준:

```text
절대정보: 코드/시스템/스키마/파일/trace/data record 등으로 존재와 값을 확인할 수 있는 정보.
상대정보: 하나의 절대정보 record 또는 field에 대응하는 의미/판단/해석/요약.
혼합정보: 하나의 절대정보로 못 박기 어렵거나 부적절한 source bundle 기반 의미/판단/해석/요약.
```

핵심:

```text
하나에 대응하면 상대정보.
하나로 못 박기 어렵거나 부적절하면 혼합정보.
```

## 요약 판정

가장 큰 문제는 `MixedInfoRef`와 `MetainfoBoundary.mixed_info`가 과거 정의를 전제로 설계되어 있다는 점이다.
현재 구현은 "출처가 있는 LLM/의미 텍스트"를 `mixed_info`로 모으는 경향이 있으며, 새 기준의 `relative_info`를 실제로 생성하거나 전달하는 경로가 없다.

반면 memory packet과 task ledger는 대체로 안전하다.
0은 좌표/상태/COPIED_FIELDS를 공급하고 `llm_semantic_summary_status=not_run`을 유지한다.
task ledger는 실행 장부이며 상대/혼합 의미 판단을 만들지 않는다.

## 발견 1: `MixedInfoRef`가 one-to-one field claim까지 모두 mixed로 담는 구조

- 파일 위치:
  - `songryeon_core/core/schemas.py:339`
  - `songryeon_core/core/schemas.py:341`
  - `songryeon_core/core/schemas.py:349`
  - `songryeon_core/core/schemas.py:372`
- 현재 분류:
  - `MetainfoBoundary.relative_info`는 빈 `list[dict]` 그릇으로만 존재한다.
  - `MetainfoBoundary.mixed_info`는 `MixedInfoRef`만 받는다.
  - `MixedInfoRef`는 `source_data_id + field_path + text`라는 direct field 구조를 가진다.
- 실제로 맞아 보이는 분류:
  - direct field one-to-one claim은 `relative_info` 또는 `RelativeInfoRef`가 더 적합하다.
  - source bundle 기반 claim만 `mixed_info`로 남겨야 한다.
- 왜 그런지:
  - 새 기준에서 "하나의 절대정보 record/field에 대응하는 의미 텍스트"는 상대정보다.
  - 현재 `MixedInfoRef`는 오히려 one-to-one source field 구조를 강제한다.
  - 이름은 mixed인데 구조는 relative에 가깝다.
- 수정 위험도:
  - 높음.
  - `MetainfoBoundary`, `node_2`, `node_3`, `ReportFrame`, smoke-test가 모두 `mixed_info` 중심으로 얽혀 있다.
- 바로 고쳐도 되는지:
  - 설계 논의 필요.
  - 단순 rename으로 끝내면 source bundle 기반 mixed를 담을 곳이 사라진다.

## 발견 2: node_2 boundary builder가 relative/mixed를 구분하지 않는다

- 파일 위치:
  - `songryeon_core/nodes/node_2_metainfo_boundary.py:324`
  - `songryeon_core/nodes/node_2_metainfo_boundary.py:345`
  - `songryeon_core/nodes/node_2_metainfo_boundary.py:356`
  - `songryeon_core/nodes/node_2_metainfo_boundary.py:367`
  - `songryeon_core/nodes/node_2_metainfo_boundary.py:430`
- 현재 분류:
  - `_build_mixed_info_refs(...)`가 L3 reason, ToolChoice reason, L2 query candidate purpose를 모두 `MixedInfoRef`로 만든다.
- 실제로 맞아 보이는 분류:
  - `source_data_id + field_path` 하나에 직접 대응하는 claim은 상대정보 후보로 봐야 한다.
  - L2 query candidate purpose처럼 생성 근거가 L1/budget/catalog/LLM call 등 source bundle일 수 있는 경우는 설계상 mixed일 수 있다.
  - 그러나 그 경우에도 `source_mode=source_bundle`, `claim_alignment=not_line_mapped` 같은 표시가 필요하다.
- 왜 그런지:
  - 현재 코드는 "field 위치가 있다"와 "source bundle 판단이다"를 구분하지 않는다.
  - 새 정책은 `source_mode: direct_field`와 `source_mode: source_bundle`을 구분하라고 요구한다.
- 수정 위험도:
  - 높음.
  - node_2 boundary가 메타정보 분류의 중심이다.
- 바로 고쳐도 되는지:
  - 설계 논의 필요.
  - 먼저 `RelativeInfoRef`와 `MixedInfoRef` 또는 통합 `SemanticInfoRef(info_class, source_mode)` 구조를 정해야 한다.

## 발견 3: node_3 handoff/report가 mixed_info만 소비한다

- 파일 위치:
  - `songryeon_core/nodes/node_2_handoff.py:209`
  - `songryeon_core/nodes/node_2_handoff.py:215`
  - `songryeon_core/core/schemas.py:550`
  - `songryeon_core/nodes/node_3_reporter.py:40`
  - `songryeon_core/nodes/node_3_reporter.py:51`
  - `songryeon_core/nodes/node_3_reporter.py:159`
- 현재 분류:
  - `Node3InputBriefFrame.allowed_claims`는 `boundary.mixed_info`에서만 만들어진다.
  - `ReportFrame`에는 `allowed_mixed_info_ids`만 있고 `allowed_relative_info_ids`가 없다.
  - fallback report도 `Mixed Info` 섹션만 렌더링한다.
- 실제로 맞아 보이는 분류:
  - node_3는 상대정보와 혼합정보를 둘 다 받을 수 있어야 한다.
  - 단일 field claim은 `allowed_relative_claims`, source bundle claim은 `allowed_mixed_claims`처럼 구분하는 것이 더 맞다.
- 왜 그런지:
  - 새 기준을 적용하면 기존 `mixed_info` 중 일부가 `relative_info`로 내려갈 수 있다.
  - 그런데 현재 downstream은 mixed만 읽으므로, relative를 제대로 만들면 node_3에 전달되지 않을 위험이 있다.
- 수정 위험도:
  - 중간~높음.
  - brief/report schema와 smoke-test를 함께 바꿔야 한다.
- 바로 고쳐도 되는지:
  - 설계 논의 필요.
  - 상대/혼합 claim의 user-facing 표시 문법을 먼저 정하는 것이 안전하다.

## 발견 4: L3AchievementFrame 주석이 CODE 운영 체크를 혼합정보처럼 설명한다

- 파일 위치:
  - `songryeon_core/core/schemas.py:2889`
  - `songryeon_core/core/schemas.py:2891`
  - `songryeon_core/core/schemas.py:2910`
  - `songryeon_core/core/schemas.py:2920`
  - `songryeon_core/core/schemas.py:2935`
- 현재 분류:
  - `achievement_status`, `reason`, `controller_decision`, `macro_achievement_status`, `goal_match_status` 등이 주석상 혼합정보로 설명된다.
- 실제로 맞아 보이는 분류:
  - `llm_semantic_judgement_status=not_run`이고 `achievement_generation_source=CODE:OPERATION_CHECK`인 현재 기본 경로에서는 절대/운영 상태 라벨이다.
  - LLM L3가 source bundle을 보고 목표 달성 의미판단을 한 경우에는 혼합정보가 될 수 있다.
- 왜 그런지:
  - 현재 L3 기본 경로는 후보 수, controller status, count guard 같은 코드가 확인 가능한 운영 조건을 바탕으로 `CODE_STATUS:*` 라벨을 쓴다.
  - 이는 semantic truth claim이 아니라 운영 상태다.
  - terminal은 이미 `llm_semantic_judgement_status`가 `ran`일 때만 mixed로 표시하고, 기본 경로는 `absolute_operation_label`로 표시한다.
- 수정 위험도:
  - 중간.
  - 동작보다 schema 주석/문서 라벨 정정에 가깝지만, L3 LLM 경로와 CODE guard 경로를 한 schema 안에서 분기해 설명해야 한다.
- 바로 고쳐도 되는지:
  - 작은 주석 수정은 가능.
  - 단, L3 LLM 산출을 relative/mixed 중 어디에 둘지 source bundle 기준으로 별도 문구를 정한 뒤 하는 것이 안전하다.

## 발견 5: terminal_view의 display-only `info_class="mixed"`가 너무 넓다

- 파일 위치:
  - `songryeon_core/runtime/terminal_view.py:170`
  - `songryeon_core/runtime/terminal_view.py:215`
  - `songryeon_core/runtime/terminal_view.py:249`
  - `songryeon_core/runtime/terminal_view.py:531`
  - `songryeon_core/runtime/terminal_view.py:617`
  - `songryeon_core/runtime/terminal_view.py:655`
  - `songryeon_core/runtime/terminal_view.py:681`
  - `songryeon_core/runtime/terminal_view.py:732`
  - `songryeon_core/runtime/terminal_view.py:801`
- 현재 분류:
  - LLM이 ran이면 대체로 `info_class="mixed"`로 표시한다.
  - node_3 input brief는 `mixed_brief_from_absolute_sources`로 표시한다.
  - LLM report/final answer도 `mixed`로 표시한다.
- 실제로 맞아 보이는 분류:
  - source bundle 기반 LLM report, node_2 review, node_4 gate review는 mixed가 대체로 맞다.
  - node_3 input brief는 code-assembled view/brief이며 의미판단 `not_run`이므로 mixed보다 `absolute_brief_from_sources` 또는 `code_assembled_view`가 더 정확해 보인다.
  - LLM route/L1/L2/L3는 source가 하나인지 bundle인지에 따라 relative/mixed가 갈릴 수 있으므로 단순 "LLM ran -> mixed"는 새 기준에 맞지 않는다.
- 왜 그런지:
  - 새 기준은 생성자(LLM/CODE)가 아니라 grounding shape로 relative/mixed를 가른다.
  - terminal 라벨이 사용자의 메타정보 이해에 직접 영향을 주므로 표시 정직성 차원에서 정리 필요.
- 수정 위험도:
  - 중간.
  - DataStore schema 변경 없이 terminal 표시만 고칠 수 있지만, 정확한 source_mode 계산 없이 바꾸면 또 다른 오분류가 생긴다.
- 바로 고쳐도 되는지:
  - 일부는 바로 가능: node_3 input brief의 mixed 라벨 제거.
  - LLM 산출 라벨 전반은 설계 논의 필요.

## 발견 6: L1GoalFrame / LLoopBudgetPlanFrame / ToolChoiceFrame 주석이 생성 경로별 분류를 표현하지 못한다

- 파일 위치:
  - `songryeon_core/core/schemas.py:1161`
  - `songryeon_core/core/schemas.py:1165`
  - `songryeon_core/core/schemas.py:1179`
  - `songryeon_core/core/schemas.py:1290`
  - `songryeon_core/core/schemas.py:1300`
  - `songryeon_core/core/schemas.py:1923`
  - `songryeon_core/core/schemas.py:1925`
- 현재 분류:
  - L1 목표, 예산 요청, ToolChoice reason/expected_use가 주석상 혼합정보로 적혀 있다.
  - 하지만 실제 기본 경로는 `RULE_STUB` 또는 `CODE_STATUS:*` 라벨도 섞여 있다.
- 실제로 맞아 보이는 분류:
  - CODE/RULE_STUB가 만든 운영 라벨은 절대/운영 상태 또는 stub label이다.
  - LLM이 여러 입력을 보고 만든 목표/예산/선택 이유는 source bundle 기반 mixed일 가능성이 높다.
  - 단일 record/field에 대한 해석이라면 relative가 될 수 있다.
- 왜 그런지:
  - 같은 field라도 생성 경로가 CODE stub인지 LLM semantic judgement인지에 따라 정보 등급이 달라진다.
  - 현재 주석은 field 단위로 고정 분류를 붙여서 경로별 차이를 표현하지 못한다.
- 수정 위험도:
  - 중간.
  - 현재 runtime은 generated_by/status를 드러내므로 즉시 동작 위험은 낮지만, 문서/주석이 학습자를 오도할 수 있다.
- 바로 고쳐도 되는지:
  - 주석 정정은 가능.
  - schema 차원의 `info_class` 필드 추가는 설계 논의 필요.

## 발견 7: L2 query plan purpose의 분류는 설계 논의가 필요하다

- 파일 위치:
  - `songryeon_core/core/schemas.py:1481`
  - `songryeon_core/core/schemas.py:1501`
  - `songryeon_core/nodes/l2_query_setter.py:445`
  - `songryeon_core/nodes/l2_query_setter.py:455`
  - `songryeon_core/nodes/l2_query_setter.py:464`
  - `songryeon_core/nodes/l2_query_setter.py:468`
  - `songryeon_core/nodes/node_2_metainfo_boundary.py:398`
- 현재 분류:
  - L2 candidate `purpose`는 `MixedInfoRef`로 승격될 수 있다.
  - smoke-test도 "L2 query plan purpose did not become mixed_info"를 기대한다.
- 실제로 맞아 보이는 분류:
  - 생성 근거가 L1 goal, budget, tool catalog, memory packet 등 source bundle이면 mixed가 맞다.
  - 하지만 "L2QueryPlanFrame.candidates[index].purpose라는 단일 field에 저장된 LLM 텍스트"라는 direct-field 관점에서는 relative로 볼 여지도 있다.
  - 새 정책의 의도상 생성 근거 bundle을 우선하면 mixed로 유지하되, `source_mode=source_bundle`이 필요하다.
- 왜 그런지:
  - 이 항목은 "저장 위치는 one field"와 "판단 생성 근거는 여러 입력"이 충돌한다.
  - 단순히 mixed를 relative로 바꾸면 L2 planner가 여러 입력을 종합했다는 사실을 잃을 수 있다.
- 수정 위험도:
  - 중간~높음.
  - smoke-test와 boundary/report 구조에 영향이 있다.
- 바로 고쳐도 되는지:
  - 설계 논의 필요.
  - 이 항목은 ORDER로 따로 잘라야 한다.

## 발견 8: ToolResultDistillationFrame의 text_preview/limits 주석도 과거 기준 흔적이 있다

- 파일 위치:
  - `songryeon_core/core/schemas.py:1990`
  - `songryeon_core/core/schemas.py:1998`
  - `songryeon_core/core/schemas.py:2016`
- 현재 분류:
  - `text_preview`와 `limits`가 주석상 혼합정보로 되어 있다.
- 실제로 맞아 보이는 분류:
  - `text_preview`가 원본 tool result field에서 복사/절단된 미리보기라면 절대/복사 텍스트 또는 document/tool extract에 가깝다.
  - `limits`가 `truncated`, `max_chars` 같은 코드 상태 설명이면 절대/운영 라벨이다.
  - LLM이 여러 tool result를 요약한 경우라면 mixed가 될 수 있지만 현재 distillation은 코드 축약/복사에 가깝다.
- 왜 그런지:
  - 복사/절단은 의미 판단이 아니다.
  - 출처가 붙었다는 이유로 mixed가 되는 것은 새 기준에서 틀리다.
- 수정 위험도:
  - 낮음~중간.
  - 주석 정정 중심으로 시작 가능하다.
- 바로 고쳐도 되는지:
  - 바로 고쳐도 되는 편.
  - 단, distillation 출력이 실제로 어떤 문자열을 만드는지 한 번 더 좁혀 보는 것이 안전하다.

## 발견 9: smoke-test가 과거 mixed 중심 기대를 고정한다

- 파일 위치:
  - `songryeon_core/runtime/smoke_test.py:1857`
  - `songryeon_core/runtime/smoke_test.py:1888`
  - `songryeon_core/runtime/smoke_test.py:2717`
  - `songryeon_core/runtime/smoke_test.py:4184`
- 현재 분류:
  - smoke-test가 `mixed_info` 존재와 `allowed_mixed_info_ids` 일치를 검사한다.
  - L2 query plan purpose가 mixed_info가 되어야 한다고 강제한다.
- 실제로 맞아 보이는 분류:
  - 새 기준에서는 relative와 mixed를 나눠 검사해야 한다.
  - `semantic_info_count`, `relative_info_count`, `mixed_info_count` 또는 direct/source_bundle별 smoke가 필요하다.
- 왜 그런지:
  - 테스트가 과거 용어를 고정하면 코드 정정을 막는다.
- 수정 위험도:
  - 중간.
  - schema 전환과 함께 smoke를 바꿔야 한다.
- 바로 고쳐도 되는지:
  - 설계 이후 구현.
  - 먼저 새 스키마/명명 결정을 해야 한다.

## 통과/큰 문제 없음: memory packet

- 파일 위치:
  - `songryeon_core/nodes/node_0_memory_supplier.py:270`
  - `songryeon_core/nodes/node_0_memory_supplier.py:271`
- 현재 분류:
  - `generated_by="CODE:RULE_STUB"`
  - `llm_semantic_summary_status="not_run"`
  - memory item은 trace evidence, capsule index, raw-capsule alignment 같은 좌표/COPIED_FIELDS 중심이다.
- 실제로 맞아 보이는 분류:
  - 절대정보/운영 좌표.
- 왜 그런지:
  - 0이 요약이나 관련성 판단을 하지 않는다.
  - ORDER_100/101 경로도 source coordinate만 복사한다.
- 수정 위험도:
  - 낮음.
- 바로 고쳐도 되는지:
  - 수정 필요 없음.

## 통과/큰 문제 없음: task ledger

- 파일 위치:
  - `songryeon_core/core/schemas.py:77`
  - `songryeon_core/core/schemas.py:117`
  - `songryeon_core/runtime/task_ledger.py:20`
- 현재 분류:
  - TaskFrame/TaskResultFrame은 실행 순서, 입력/출력 trace/data ID, worker/policy/status를 장부화한다.
- 실제로 맞아 보이는 분류:
  - 절대정보/운영 장부.
- 왜 그런지:
  - 의미 판단/요약을 만들지 않는다.
  - `sequential_v0`, `local_sync_worker`, completed/failed 같은 상태 라벨만 기록한다.
- 수정 위험도:
  - 낮음.
- 바로 고쳐도 되는지:
  - 수정 필요 없음.

## 권장 다음 행동

### 1. 바로 코드 수정하지 말고 ORDER 작성

추천 발주:

```text
ORDER_102_METAINFO_RELATIVE_MIXED_SCHEMA_SPLIT_V0
```

목표:

```text
MetainfoBoundary가 relative_info와 mixed_info를 실제로 구분할 수 있게 한다.
```

### 2. 설계 후보

후보 A:

```text
RelativeInfoRef
MixedInfoRef
```

후보 B:

```text
SemanticInfoRef
- info_class: relative | mixed
- source_mode: direct_field | source_bundle
- source_data_id / field_path
- source_data_ids
- source_trace_ids
- claim_alignment
```

현재 정책 문서의 예시는 후보 B에 가깝다.

### 3. 우선 정리 대상

먼저 node_2 boundary부터 정리한다.

```text
node_2_metainfo_boundary.py
core/schemas.py MetainfoBoundary
node_2_handoff.py allowed_claims
ReportFrame allowed_*_info_ids
smoke_test mixed_info checks
```

### 4. 나중에 정리해도 되는 대상

schema 주석과 terminal display label은 중요하지만, node_2 boundary 구조보다 후순위다.

```text
L1GoalFrame comments
L3AchievementFrame comments
ToolChoiceFrame comments
ToolResultDistillationFrame comments
terminal_view display-only info_class labels
```

## 최종 결론

현재 코드가 LLM 의미판단을 코드가 몰래 생성하는 큰 사고는 보이지 않는다.

하지만 메타정보 분류 구조는 과거 정의의 흔적이 강하다.
특히 `MixedInfoRef`가 one-to-one field claim과 source-bundle claim을 모두 "mixed"라는 이름 아래로 보낼 수 있어, 새 기준에서는 정정이 필요하다.

다음 구현은 기능 확장이 아니라 metainfo schema 정렬 작업이어야 한다.
