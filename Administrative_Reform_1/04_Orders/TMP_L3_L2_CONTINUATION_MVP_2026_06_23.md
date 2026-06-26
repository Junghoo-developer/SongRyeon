# TMP L3-L2 Continuation MVP 2026-06-23

## 상태

이 문서는 임시 발주서다.

확실한 것만 적는다.

아직 바로 구현 명령이 아니다.

## 목표

L3가 L1/L2/L루프 결과를 비판한 뒤, 가벼운 검색 실패를 최대 3회까지 L2 수정 검색으로 이어갈 수 있는 최소 구조를 만든다.

## 확정 원칙

1. L3는 비판할 수 있다.
2. L3는 직접 라우팅하지 않는다.
3. L3가 L1 목표 자체가 틀렸다고 판단한 경우에는 가벼운 L2 재검색으로 처리하지 않는다.
4. L1 목표 자체가 틀린 경우는 나중에 `L3 -> 0 -> 1 -> 0 -> L1` 계열의 무거운 경로로 다룬다.
5. L1 목표는 대체로 맞고 L2 검색/읽기만 부족한 경우에는 가벼운 재검색 후보가 된다.
6. MVP에서는 `L3 -> 0 -> L2`를 만들지 않는다.
7. MVP에서는 코드 controller가 L3 스키마에서 필요한 필드만 읽어 L2 수정 검색을 허용한다.
8. 코드 controller는 의미 판단을 하지 않는다.
9. 코드 controller는 L3의 추천과 시도 횟수 같은 절대 조건만 집행한다.
10. L2 수정 검색은 최대 3회로 막는다.

## 필요한 L3 스키마 후보

이 필드는 아직 확정 구현이 아니라 후보 이름이다.

```text
l1_goal_validity: valid | weak | invalid | unjudged
l1_goal_critique_reason: str
l2_search_revision_needed: bool
l2_search_revision_reason: str
recommended_next_step: stop_success | report_partial | retry_l2 | return_to_1
l2_revision_attempt_count: int
max_l2_revision_attempts: int
```

## MVP에서 할 일

```text
1. L3 achievement schema/prompt에 L1 목표 비판과 L2 재검색 추천 필드를 추가한다.
2. L루프 controller가 L3의 `retry_l2` 추천과 attempt_count를 읽을 수 있게 한다.
3. attempt_count가 3 미만일 때만 L2 수정 검색을 허용한다.
4. 3회 실패하면 더 돌리지 않고 1 또는 2로 넘길 수 있는 상태를 남긴다.
```

## MVP에서 하지 않을 일

```text
1. W loop를 만들지 않는다.
2. C loop를 만들지 않는다.
3. L3에게 직접 라우팅 권한을 주지 않는다.
4. 0을 L3와 L2 사이에 새로 끼우지 않는다.
5. 장기기억 DB나 그래프 DB를 건드리지 않는다.
6. 자동 무한 재검색을 만들지 않는다.
```

## 완료 기준 후보

```text
1. 특정 문서를 요구했는데 1위 후보가 README인 경우, L3가 곧바로 achieved로 끝내지 않는다.
2. L3가 retry_l2를 추천하면 L2가 다른 검색어 또는 더 좁은 검색어를 만든다.
3. L2 수정 검색이 최대 3회를 넘지 않는다.
4. pretty runtime에 L3 비판, retry_l2 여부, attempt_count가 보인다.
```

## 다음 판단

이 임시 발주서는 다음 개발 목표 후보 중 하나다.

하지만 오늘 첫 MVP로 바로 선택할지는 아직 별도 목표 지정에서 결정한다.
