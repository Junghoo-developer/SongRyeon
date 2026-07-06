# ORDER_206 Release-Friendly Fake Turn First Demo - Execution Record

## 실행 일시

2026-07-06

## 목적

배포용 첫 실행 명령인 `fake-turn`이 Qwen/Neo4j 없이도 안전하게 성공하는지 확인하고, 첫인상용 질문에서 불필요한 L 검색과 node_4 반려가 발생하지 않게 정리했다.

## 원인

- `SongRyeonAllNodesFakeLLMAdapter`가 "송련"이라는 단어가 들어간 자기소개성 질문을 L 문서검색으로 보냈다.
- fake node_3의 Vessel R 경계 문장이 node_4의 문자열 guard에서 문서 근거 주장처럼 해석될 수 있었다.

## 변경 파일

- `songryeon_core/llm/fake.py`
- `songryeon_core/nodes/node_4_gatekeeper.py`
- `tests/test_order_206_release_friendly_fake_turn.py`
- `README.md`
- `README.ko.md`
- `Administrative_Reform_1/04_Orders/ORDER_206_RELEASE_FRIENDLY_FAKE_TURN_FIRST_DEMO_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## 변경 내용

- 자기소개성 fake 질문은 route=2로 닫히게 했다.
- 문서/코드/그래프/Neo4j/R/L을 명시한 질문은 기존 검색/탐색 경로를 유지한다.
- fake node_3가 `fake-turn`은 실제 Qwen 답변이 아니라 배포용 deterministic demo임을 밝힌다.
- node_4 Vessel R material guard가 부정문을 근거 주장으로 오해하지 않게 했다.
- README/README.ko의 첫 fake-turn 예시를 자기소개성 성공 데모로 바꿨다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_206_release_friendly_fake_turn.py -q`: 3 passed
- `python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py tests/test_order_206_release_friendly_fake_turn.py -q`: 8 passed
- `python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty`: `node_4 gatekeeper: pass`, `FINAL_BLOCKED_BY_GATEKEEPER` 없음
- `python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇인지 알려줘" --pretty`: L route 유지, `node_4 gatekeeper: pass`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

## 하지 않은 것

- Qwen live route 변경 없음.
- 실제 R/L route 정책 변경 없음.
- Vessel/Neo4j schema 변경 없음.
- node_4 guard 제거 없음.
