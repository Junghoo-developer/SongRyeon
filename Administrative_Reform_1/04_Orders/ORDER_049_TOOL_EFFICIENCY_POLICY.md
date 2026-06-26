# ORDER 049: Tool Efficiency Policy

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "능률 도구 사용"  
**목표**: L루프의 도구 사용에 budget, 중복 방지, cache 활용, 조기 중단 규칙을 붙인다.

## 배경

자율 도구 사용을 허용하면 검색이 좋아질 수 있지만, 아무 제한이 없으면 같은 검색어를 반복하거나 긴 문서를 계속 읽는 문제가 생긴다.  
능률 좋은 L루프는 똑똑한 검색뿐 아니라 "그만할 줄 아는 능력"도 가져야 한다.

## 범위

1. `ToolUseBudgetFrame`을 만든다.
2. turn당 최대 tool call, query 후보 수, read_doc 횟수, 최대 입력 문자 수를 제한한다.
3. 이미 실행한 query와 읽은 doc_id를 추적한다.
4. vector index cache 상태를 L루프 판단 입력에 포함한다.
5. 성과가 낮은 반복은 중단한다.

## 원칙

1. budget 초과는 실패가 아니라 통제된 종료 사유다.
2. cache hit/miss는 절대정보로 기록한다.
3. 효율 정책은 LLM prompt에만 맡기지 않고 코드가 강제한다.

## 완료 기준

1. 같은 query를 반복 실행하려 하면 중복 신호가 남는다.
2. 최대 tool call 수를 넘기면 L루프가 중단된다.
3. cache_status가 trace/data에서 확인된다.
4. smoke test에 budget 제한 케이스가 추가된다.
