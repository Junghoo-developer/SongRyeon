# L3 Live Semantic Binding Failure 감사 기록

## 1. 감사 일자와 범위

- 일자: 2026-07-18
- 코드 수정: 없음
- 대상:
  - `songryeon_core/nodes/l3_result_keeper.py`
  - `songryeon_core/prompts/l3_result_keeper_v0.md`
  - `songryeon_core/nodes/node_0_memory_supplier.py`
  - `songryeon_core/nodes/node_2_handoff.py`
  - ORDER 261/262 회귀 테스트와 설계 문서
- 계기: ORDER 271 대표 Qwen 측정의 두 L 경로에서 최초 L3 schema failure가 반복됨

## 2. 재현된 절대정보

### 2.1 외부 workspace 코드 원문

```text
requested = workspace_policy.py
actual_read_code_file = 1
read_range = [0, 6923) / total 6923 / not truncated
L3 failure_type = schema_failed
L3 error = L3 semantic evidence excerpt is too long
L3 execution_duration_ms = 9828
final node_4 = pass
```

### 2.2 내부 ORDER 문서 원문

```text
requested = ORDER_270_DIRECT_OLLAMA_TRANSPORT_TIMEOUT_AND_HONEST_RECOVERY_V0.md
actual_read_doc = 1
read_doc_chars = 2263 / not truncated
L3 failure_type = schema_failed
L3 error = L3 semantic evidence excerpt must be copied exactly from supplied material
L3 execution_duration_ms = 8140
L3 per-document summary = ran
final node_4 = pass
```

두 사례 모두 원문 확보 장부는 `original_material_acquired`, 원문 요구 충족으로 남았다.
최초 L3 LLM 의미판단만 실패했고 최종 사용자 답변은 후속 raw/summary 재료로 생성됐다.

## 3. 감사 판정

### 높음 1: validator의 400자 제한이 L3 프롬프트에 공개되지 않음

- 코드 위치: `l3_result_keeper.py`
  - `L3_SEMANTIC_EVIDENCE_EXCERPT_MAX_CHARS = 400`
  - validator는 400자를 넘으면 schema failure 처리
- 프롬프트 위치: `l3_result_keeper_v0.md`
  - `exact, non-empty excerpt`, `short`만 요구
  - 정확한 최대 길이 400자를 알려주지 않음

첫 live 실패는 모델이 알 수 없는 code constraint를 위반한 사례다. 이는 모델 성능
문제라기보다 입력 계약 누락이다. validator를 약화할 이유는 없으며, 계약을 명시하거나
자유 복사 자체를 없애는 방향이 필요하다.

### 높음 2: L3 LLM schema failure가 downstream 성공 상태에서 희석됨

- `run_l3_result_keeper()`는 LLM 경로 전체를 넓은 `except Exception`으로 감싸고,
  실패하면 code operation achievement frame으로 대체한다.
- 대체 frame은 `semantic_goal_match_status=not_run`이다.
- `node_0_memory_supplier._return_failure_level_and_route_hint()`는 semantic status 중
  `partial`, `missing`만 불충족으로 본다. `not_run`은 불충족에 포함되지 않는다.
- operation status가 achieved이고 원문 수량 조건이 맞으면 `failure_level=none`, route=2로 닫힌다.
- `node_2_handoff._l_loop_result_attitude_hint()`는 task achieved + failure none이면
  semantic not-run 여부보다 먼저 `l_loop_achieved`를 반환한다.

따라서 terminal의 `llm_call` 장부에는 schema failure가 보이지만, 0 반환 요약과 node_3
태도 신호는 성공 쪽으로 기운다. 실제 원문 확보 성공과 L3 의미검사 실패를 서로 다른
상태로 보존하지 못한 것이다.

### 중간 3: 자유 텍스트 exact-copy 계약은 작은 모델에서 취약함

L3는 최대 1,200자 문서 preview 또는 전체 24,000자 안의 코드 range에서 스스로 짧은
문장을 골라 JSON 문자열에 그대로 복사해야 한다. code는 substring 정확 일치만 허용한다.
공백, 줄바꿈, Markdown 기호, 따옴표를 조금만 정규화해도 실패한다.

두 번째 live 실패는 Qwen이 supplied material과 정확히 같은 문자열을 만들지 못한
사례다. 가드가 옳게 차단했지만, 현재 출력 계약은 모델에게 불필요하게 취약하다.

### 중간 4: 프롬프트 enum 자체가 모순됨

프롬프트는 허용값을 `matched`, `partial`, `missing`, `not_run`으로 선언한다. 그러나
특정 문서가 검색 결과에도 없고 근거도 없을 때 `failed`를 쓰라고 별도 지시한다.
validator는 `failed`를 허용하지 않는다. 해당 조건에서 모델이 문구를 따르면 schema
failure가 난다.

### 중간 5: 회귀 테스트는 guard를 증명하지만 실제 Qwen 준수를 증명하지 않음

ORDER 261/262 fake adapter는 `text_preview[:40]`을 정확히 복사해 성공 payload를 만든다.
존재하지 않는 ref와 바꿔 쓴 excerpt를 차단하는 테스트는 있다. 이번 감사에서 관련
테스트 `16 passed`를 확인했다.

따라서 테스트가 증명하는 것은 code guard의 정확성이다. Qwen이 긴/복잡한 preview에서
binding 계약을 안정적으로 지킨다는 것은 증명하지 않는다. ORDER 262 실행 기록도 당시
live 검증이 수행되지 않았음을 명시한다.

## 4. 잘 작동한 부분

1. 잘못된 excerpt를 의미 성공으로 받아들이지 않았다.
2. L3 schema failure는 `llm_call` record와 terminal에 정확한 원인으로 남았다.
3. 실제 읽은 문서/코드 원문과 count는 삭제되거나 성공으로 위조되지 않았다.
4. final node_3/node_4는 별도 공급된 실제 원문 또는 L3 문서별 요약을 사용했다.
5. code가 excerpt의 의미를 대신 판단하지 않았다.

## 5. 원인 분류

- `too long`: code constraint가 prompt에 누락된 계약 불일치
- `copied exactly`: 자유 텍스트 exact-copy 방식과 Qwen 출력 안정성의 결합 문제
- downstream `achieved`: 의미검사 실행 실패와 원문 확보 성공을 한 상태로 접은 설계 문제
- 일반 모델 한계만으로 단정할 근거: 없음

## 6. 권장 후속 발주 경계

후속 후보명:

`ORDER_272_L3_EVIDENCE_BINDING_SELECTION_AND_FAILURE_PROPAGATION_V0`

권장 범위:

1. validator와 exact-source 결속은 유지한다.
2. LLM이 arbitrary excerpt를 다시 쓰게 하지 않는다.
3. code가 의미 판단 없이 만든 짧은 exact excerpt 후보에 안전한 ID를 붙이고,
   L3는 의미상 맞는 후보 ID만 선택하게 한다.
4. L3 LLM call의 `none/parse_failed/schema_failed/adapter_failed`를 achievement/return
   summary에 별도 절대상태로 보존한다.
5. 원문 확보 성공과 L3 의미검사 실패를 동시에 표현한다.
6. node_3에는 `원문은 확보됐으나 L3 의미검사는 실패`라는 태도 신호를 전달한다.
7. 프롬프트의 잘못된 `failed` enum 지시를 제거한다.
8. node_4 guard는 약화하지 않는다.

설계 논의가 필요한 점:

- exact excerpt 후보를 문단, 줄 묶음, 고정 문자 구간 중 어떤 절대 정책으로 나눌지
- L3 schema repair를 한 번 허용할지, ID 선택 계약으로 repair 자체를 불필요하게 만들지

## 7. 이번 감사에서 하지 않은 것

- 코드/프롬프트 수정
- validator 완화
- code 의미 관련성 판단
- L/R 반복, 예산, timeout 변경
- 추가 live Qwen 호출

## 8. 최종 결론

L3 가드는 실패한 것이 아니라 정확히 작동했다. 문제는 모델에게 공개된 출력 계약이
validator보다 약하고, 그 결과 발생한 L3 의미검사 실패가 downstream의 `achieved` 신호에
충분히 반영되지 않는다는 점이다. 다음 패치는 프롬프트 문구만 다듬는 수준보다,
자유 복사를 ID 선택으로 바꾸고 실패 상태를 끝까지 운반하는 작은 구조 패치가 적합하다.
