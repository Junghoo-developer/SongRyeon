# ORDER 252: R1 Evidence Contract And Code-Enforced Stop v0

## 1. 목표

R1이 그래프 깊이와 노드 열람 수를 동시에 추측하던 구조를 단순화한다.

새 R1은 다음 의미 계약만 작성한다.

1. 무엇을 찾을 것인가
2. 어떤 수준의 근거가 필요한가
3. 그 근거가 최소 몇 개 필요한가

코드는 실제로 확보한 그래프 재료와 안전 상한을 세어 R3의 종료 요청을 승인하거나
거부한다.

## 2. 문제

현재 R1은 다음 값을 함께 생성한다.

- `required_information_granularity`
- `min_traversal_depth`
- `min_node_reads`
- `min_terminal_material_count`

이 값들은 서로 겹치며 그래프 모양에 의존한다. 특히 원문을 요구했어도 토큰 묶음
요약 하나가 `terminal material`로 집계되면 R3의 `stop_sufficient`가 받아들여질 수
있다. 그래프에 다른 축이나 중간 계층이 추가되면 같은 원문까지의 깊이도 달라지므로,
깊이를 의미 요구의 대용물로 사용하는 방식은 장기적으로 취약하다.

## 3. 새 R1 근거 계약

새 R1 LLM 출력은 다음 필드를 중심으로 한다.

```json
{
  "graph_search_goal": "ORDER 090의 제안과 안전장치를 확인한다.",
  "user_question_anchor_id": "code가 공급한 anchor를 그대로 복사",
  "required_material_level": "raw_original",
  "required_material_count": 1
}
```

`required_material_level`은 세 값으로 고정한다.

- `overview`: 글이 있는 상위 요약 또는 그보다 자세한 재료
- `source_summary`: 특정 원본 하나에 대응하는 `source_leaf_summary` 또는 그보다 자세한 원문
- `raw_original`: 실제 원문 text가 포함된 RawSource 또는 RawCapsule

`required_material_count`는 최소 필요 재료의 개수다. 같은 그래프 노드를 여러 번
방문해도 한 개로만 센다.

## 4. 권한 분리

### R1

- 사용자 질문을 해석한다.
- 검색 목표를 만든다.
- 필요한 재료 수준과 최소 개수를 정한다.
- 노드 ID, 실제 경로, 실제 확보 개수를 만들지 않는다.

### R2

- code가 공급한 현재 공식 후보 중 다음에 읽을 노드를 선택한다.
- R1 계약을 참고할 수 있지만, 존재하지 않는 ID를 만들 수 없다.

### R3

- 선택된 재료가 질문에 의미상 충분한지 판단한다.
- 정보 농도와 가지 문제, 다음 행동을 제안한다.
- 근거 계약이 충족되지 않았는데 최종 종료를 강제할 수 없다.

### code

- 최대 탐색 깊이, 최대 노드 열람, 최대 컨텍스트, 원문 최대 5개를 유지한다.
- 선택된 record의 구조 필드와 실제 text 존재 여부로 재료 수준을 판정한다.
- 고유한 계약 충족 재료 ID와 개수를 집계한다.
- R1 계약 충족 여부를 절대정보로 기록한다.
- 관련성, 답변 충분성, 가지 선택을 대신 판단하지 않는다.

## 5. 종료 규칙

1. R3가 `stop_sufficient`를 요청하고 계약도 충족했으면 정상 종료할 수 있다.
2. R3가 `stop_sufficient`를 요청했지만 계약이 미충족이고 하위 후보와 예산이 남으면
   code가 `continue_deeper`로 바꾼다.
3. 계약이 미충족인데 하위 후보가 없으면 `partial / stop_no_actionable_path`로 닫는다.
4. 계약이 미충족인데 안전 예산이 끝나면 `partial / stop_budget_exhausted`로 닫는다.
5. RawSource 노드를 선택했어도 실제 원문 text가 없으면 `raw_original` 확보로 세지 않는다.
6. 계약 충족은 R3의 의미상 충분성 판단을 대신하지 않는다. 계약과 R3 판단이 모두
   충족돼야 `sufficient`가 된다.

## 6. 기존 필드 호환

- `min_traversal_depth`, `min_node_reads`, `min_terminal_material_count`는 기존 실행 기록과
  테스트를 읽기 위한 호환 필드로 당장 삭제하지 않는다.
- 새 R1 프롬프트에서는 세 필드를 출력하지 않는다.
- 새 계약을 사용한 실행에서 옛 최소 숫자는 종료 의미를 소유하지 않는다.
- 과거 형식 payload는 명시적인 `legacy_minimum_budget_compatibility` 경로로만 허용한다.
- 호환 경로를 새 정책인 것처럼 숨기지 않는다.

## 7. 표시와 추적

runtime에는 다음 절대정보를 표시한다.

- R1이 요구한 재료 수준
- 요구 개수
- 실제 확보한 고유 재료 개수
- 계약 상태: `satisfied | unmet | not_applicable`
- 계약 때문에 조기 종료가 차단된 횟수

## 8. 테스트

1. 새 R1 payload에는 세 개의 옛 최소 예산 출력 필드가 없어야 한다.
2. `raw_original=1`인데 토큰 요약에서 R3가 충분하다고 해도 더 내려가야 한다.
3. source leaf summary는 `source_summary` 계약을 충족해야 한다.
4. 실제 text가 있는 RawSource만 `raw_original` 계약을 충족해야 한다.
5. 같은 재료를 반복 방문해도 계약 개수가 증가하지 않아야 한다.
6. 계약 미충족 상태에서 길이나 예산이 끝나면 `sufficient`가 아니라 `partial`이어야 한다.
7. 기존 legacy adapter와 테스트는 명시적 호환 경계 안에서 유지돼야 한다.

기본 검증:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

## 9. 금지

- 사용자 문구의 특정 단어를 code가 짜깁기해 재료 수준을 고르는 휴리스틱 금지
- code가 R2의 관련 노드를 대신 선택하는 기능 금지
- code가 R3의 의미상 충분성을 대신 판단하는 기능 금지
- 최대 원문 열람 5회 증가 금지
- R/L 라우팅, W loop, scheduler, 외부 DB 구조 변경 금지
- 기존 발주서와 실행 기록의 과거 값을 소급 변경하는 작업 금지
