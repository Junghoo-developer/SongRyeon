# TMP ORDER 037: Failure Signal v0.2

## 목표

기억 부족, 스키마 실패, 도구 실패, LLM 실패를 구분하는 실패 신호 체계를 확장한다.

## 배경

현재 FailureSignal은 최소 필드만 있다.  
나중에 0이 반려를 때리거나 1이 재라우팅하려면 실패 신호가 더 구조적이어야 한다.

## 범위

1. `FailureSignalFrame`을 만든다.
2. `failure_id`, `type`, `severity`, `raised_by`, `recoverable`, `source_trace_ids`, `source_data_ids`를 둔다.
3. DataStore에 실패 payload를 저장한다.
4. dry_run에서 일부 실패 케이스를 수동 테스트한다.

## 완료 기준

- 실패 신호가 trace와 DataStore에 함께 남는다.
- recoverable 여부를 1이 나중에 읽을 수 있다.

## 제외

- 자동 복구 루프.
- C루프 구현.
