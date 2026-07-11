# ORDER 232: Node2 Role Info Class And Vessel Status Guard v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: node_2 answer-basis contract / node_4 Vessel R status-name guard

## 배경

RTX 5080 고정 후 실시한 live Vessel R 통합 테스트에서 두 개의 좁은 문제가 확인됐다.

1. node_2는 답변 모드와 source ID를 올바르게 골랐지만 `role_reason_info_class=absolute`를 반환해 schema fallback으로 닫혔다.
2. node_3는 `task_status가 sufficient가 아니므로 부분적이다`라고 정직하게 썼지만, node_4 code guard가 자연어 조사를 상태 대입으로 읽어 `sufficient` 주장으로 오탐했다.

## 목표

- evidence role의 의미 판단 분류는 `relative|mixed`만 가능하다고 LLM 입력과 schema에 명시한다.
- node_4 code guard는 명시적인 구조형 상태 대입만 비교하고 자연어 의미 판정은 node_4 LLM 책임으로 남긴다.

## 변경

- node_2 input payload에 `role_reason_info_class_values=[relative,mixed]`를 넣는다.
- node_2 prompt에 source의 info class와 role reason의 info class가 다름을 명시한다.
- `Node2EvidenceRole.role_reason_info_class` validator를 `relative|mixed`로 좁힌다.
- node_4 status-name code guard는 `=`, `:`, `->`로 명시된 상태 대입만 읽는다.
- live에서 나온 한국어 부정문을 회귀 테스트로 고정한다.

## 하지 않는 것

- node_2 실패 fallback을 약화하지 않는다.
- `absolute`를 허용해 schema를 느슨하게 만들지 않는다.
- 한국어 부정 표현 휴리스틱을 계속 추가하지 않는다.
- R 탐색 전략, 예산, Neo4j 구조를 변경하지 않는다.

## 완료 조건

- node_2 LLM 입력에 role reason 허용값이 보인다.
- `absolute|absolute_status` evidence role reason은 계속 schema 실패한다.
- `task_status가 sufficient가 아니다`는 상태명 불일치로 오탐되지 않는다.
- 명시적인 잘못된 `task_status=insufficient`는 계속 차단된다.
- compileall, 관련 pytest, quick-smoke가 통과한다.
