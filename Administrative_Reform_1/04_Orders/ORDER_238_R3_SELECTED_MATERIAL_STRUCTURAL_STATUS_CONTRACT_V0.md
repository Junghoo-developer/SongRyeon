# ORDER 238: R3 Selected Material Structural Status Contract v0

## 상태

- Status: implemented and regression verified; follow-up completed through ORDER_242
- Date: 2026-07-10
- Scope: R3 selected-material absolute facts / narrowed status contract / one repair

## 배경

ORDER 237 완전 통합 시험에서 R은 ORDER_090의 RawSource까지 6단계로 내려갔고,
R3 input에는 3,722자의 원문이 실제로 포함되었다. 그러나 Qwen은 이 재료를
두 번 모두 `low_summary`라고 부르고, 자식 후보가 0개인데도 `deeper`를 요청했다.
기존 validator는 이 모순을 정직하게 차단했지만, code가 이미 확정한 재료 구조를
LLM status 선택표에 충분히 반영하지 못했다.

## 목표

- code가 선택 재료의 구조 사실을 별도 absolute fact card로 공급한다.
- 원문이 있는 RawSource면 R3의 현재 정보 농도 선택지는 `raw`만 허용한다.
- 자식 후보가 0개면 다음 행동 선택지에서 `deeper`를 제거한다.
- repair에서도 같은 좁은 선택표를 유지한다.

## 구현 경계

- code가 확정하는 것은 node kind, 원문 존재 여부/문자 수, 자식 후보 수뿐이다.
- 원문이 사용자 질문에 충분한지는 R3가 판단한다.
- code는 `sufficient`를 강제하거나 문서 의미를 요약하지 않는다.
- 기존 validator는 유지하고, code-supplied 좁은 상태표도 검증한다.

## 하지 않는 것

- 키워드 기반 성공 휴리스틱을 추가하지 않는다.
- RawSource를 읽었다는 이유만으로 목표 달성을 강제하지 않는다.
- 자식이 없는 실패를 조용히 성공이나 stop으로 바꾸지 않는다.
- R1/R2/Node2/Node3/Node4의 의미 판단 책임을 이동하지 않는다.

## 완료 조건

- 원문이 있는 RawSource의 allowed granularity는 `raw` 하나다.
- 자식 0개 재료의 allowed action에는 `deeper`가 없다.
- schema repair table도 이 좁은 계약을 보존한다.
- pytest, quick-smoke, 완전 통합 qwen-turn을 실행한다.
