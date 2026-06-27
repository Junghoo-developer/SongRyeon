# Memory Window Compression Philosophy 2026-06-26 001

## 요청

사용자가 최근 원문 기억 창과 향후 압축 기억 구상을 철학 문서에 남겨 달라고 요청했다.

핵심 구상:

- 최근 원문 대화는 최대 8턴까지 보장한다.
- 최근 원문 대화는 최소 3턴은 남긴다.
- 원문 창이 9턴이 되면 최신 5턴을 남기고 오래된 4턴을 압축 후보로 분리한다.
- 0은 의미 요약을 만들지 않고 좌표만 찍는다.
- 5 기억 압축기가 LLM으로 source bundle 기반 압축 요약을 만든다.
- 4가 압축 요약을 검사하고 승인하기 전까지 active memory로 승격하지 않는다.

## 변경

- `Administrative_Reform_1/00_Philosophy/Raw_Memory_Window_And_Node5_Compression_Philosophy_2026_06_26.md` 추가.
- `Administrative_Reform_1/00_Philosophy/README.md`에 새 철학 문서 링크 추가.

## 메타정보 원칙

- 최근 원문 대화 좌표, TurnStateCapsule 좌표, 압축 후보 좌표는 코드가 확정 가능한 절대정보로 본다.
- 5가 여러 턴 원문과 trace/data record를 근거로 만드는 압축 요약은 혼합정보로 본다.
- 4 승인 전 압축 요약은 `pending_memory_summary` 또는 `compression_candidate`이며 active memory가 아니다.

## 검증

문서 변경만 수행했다.

코드 실행, schema 변경, smoke-test는 수행하지 않았다.
