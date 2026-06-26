# ORDER 060: Turn Capsule Compression v2

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 다음 턴의 0이 읽기 좋은 trace capsule 필요  
**목표**: 한 턴의 trace를 다음 턴 0이 읽기 좋게 압축하되, 원본 trace 추적성을 유지한다.

## 배경

현재 `TurnStateCapsule`은 node movement와 trace ID를 담는다.  
하지만 LLM과 자율 L루프가 들어오면 한 턴의 trace가 길어져 다음 턴 0이 원본 전체를 읽기 어려워진다.

## 범위

1. capsule v2에 `route_summary`, `tool_summary`, `llm_summary`, `outcome_summary`, `limits`를 둔다.
2. summary 문장마다 원본 trace/data ID를 연결한다.
3. 압축은 원본 삭제가 아니라 색인과 요약이다.
4. capsule v2는 ZeroState read window의 주요 입력이 된다.
5. replay에서는 capsule summary에서 원본 trace로 이동할 수 있어야 한다.

## 원칙

1. capsule은 기억의 원본이 아니라 다음 턴용 색인이다.
2. 요약은 혼합 정보이므로 근거 ID를 가져야 한다.
3. 압축 실패 시 원본 trace ID 목록은 보존한다.

## 완료 기준

1. 턴 종료 시 capsule v2 payload가 저장된다.
2. capsule summary가 route, tool, L3 achievement를 포함한다.
3. summary 항목마다 source ID가 있다.
4. 다음 턴 0이 capsule v2를 읽을 수 있다.
