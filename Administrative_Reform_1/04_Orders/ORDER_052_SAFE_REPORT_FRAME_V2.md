# ORDER 052: Safe Report Frame v2

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: ORDER 051 후속 보고관 확장  
**목표**: 3 보고관이 2가 허가한 절대정보와 혼합 정보만 사용해 사용자용 보고를 만든다.

## 배경

현재 3은 절대정보 목록을 나열하는 보고서를 만든다.  
이 방식은 안전하지만 사용자가 읽기에는 딱딱하고, L루프가 실제로 무엇을 했는지 파악하기 어렵다.

## 범위

1. `ReportFrame` v2 또는 호환 확장 필드를 만든다.
2. 보고에는 `summary`, `actions_taken`, `findings`, `limits`, `evidence_ids`를 둔다.
3. 3은 `MetainfoBoundary.absolute_info`와 허가된 `mixed_info`만 읽는다.
4. 3은 LLM을 쓸 수 있지만, 출력은 ReportFrame 검증을 통과해야 한다.
5. 기존 dry run report는 fallback으로 유지한다.

## 원칙

1. 보기 좋은 문장은 안전한 경계 위에서만 만든다.
2. 3은 boundary 밖 payload를 직접 읽지 않는다.
3. 보고 문장에는 최소한의 근거 ID가 따라가야 한다.

## 완료 기준

1. 보고서가 ID 나열만이 아니라 사람이 읽는 요약을 포함한다.
2. 보고서가 허가되지 않은 혼합 정보 본문을 말하지 않는다.
3. ReportFrame v2 payload가 DataStore에 저장된다.
4. `python main.py smoke-test`가 통과한다.
