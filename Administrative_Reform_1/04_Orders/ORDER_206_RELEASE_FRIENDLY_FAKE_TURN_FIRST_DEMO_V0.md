# ORDER_206_RELEASE_FRIENDLY_FAKE_TURN_FIRST_DEMO_V0

## 상태

구현 완료.

## 배경

배포 준비 관점에서 `fake-turn`은 Qwen, Ollama, Neo4j 없이도 처음 온 사용자가 송련 Core의 실행 흐름을 맛볼 수 있어야 한다.
하지만 `python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty` 실행에서 runtime 자체는 돌았으나 node_4가 최종 답변을 `needs_revision`으로 막았다.

이는 송련의 안전장치가 작동한 것이지만, 첫 실행 데모로는 "프로젝트가 안 된다"는 인상을 줄 수 있다.

## 목표

Qwen과 Neo4j 없이도 첫 데모 명령이 정직하게 성공하도록 `SongRyeonAllNodesFakeLLMAdapter`의 deterministic 응답을 배포 친화적으로 정리한다.

## 구현 범위

1. "송련이 뭔지 짧게 설명" 같은 자기소개성 fake 질문은 L 문서검색으로 보내지 않고 route=2로 닫는다.
2. 문서/코드/그래프/Neo4j/R/L을 명시적으로 묻는 요청은 기존처럼 L 또는 R 경로가 가능하게 둔다.
3. fake node_3는 자기소개성 질문에서 Qwen 답변인 척하지 않고, `fake-turn` 데모 성격을 밝힌다.
4. node_4 Vessel R material guard가 "read_doc evidence가 아니다" 같은 부정문을 문서 근거 주장으로 오해하지 않게 한다.
5. README의 기존 문서검색 fake-turn 예시는 깨지지 않게 유지한다.

## 금지

- Qwen live route를 바꾸지 않는다.
- 실제 node_1 의미 라우팅을 code fallback으로 대체하지 않는다.
- Vessel/Neo4j schema나 R traversal 정책을 바꾸지 않는다.
- node_4 guard를 약화해 잘못된 성공 주장을 통과시키지 않는다.

## 완료 조건

- `python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty`가 `FINAL_BLOCKED_BY_GATEKEEPER` 없이 통과한다.
- 기존 문서검색형 fake-turn은 L route를 유지한다.
- 부정문 경계 테스트가 통과한다.
- `python -m compileall songryeon_core main.py`
- 관련 pytest 통과.
