# TMP ORDER 022: Turn Outcome Frame

## 목표

한 턴의 성패와 종료 상태를 DataStore payload로 저장한다.

## 배경

사용자는 1이 2에게 라우팅할 때 0이 성패 판단 권한을 갖게 하자고 설계했다.  
현재는 턴 성패 payload가 없다.

## 범위

1. `TurnOutcomeFrame` 스키마를 만든다.
2. `turn_id`, `status`, `decided_by`, `source_trace_ids`, `source_data_ids`, `failure_signal_ids`를 둔다.
3. MVP에서는 `status="completed_without_llm_judgement"` 같은 보수적 상태를 사용한다.
4. 0의 final trace 공급 이후 outcome frame을 저장한다.

## 완료 기준

- DataStore에 turn outcome payload가 저장된다.
- 최종 report source data에 outcome frame을 연결할 수 있다.

## 제외

- 실제 성공/실패 의미 판단.
- 복잡한 평가 점수.
