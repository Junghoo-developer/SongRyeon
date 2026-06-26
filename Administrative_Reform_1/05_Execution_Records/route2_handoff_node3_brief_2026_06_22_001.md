# Route2 Handoff Node3 Brief 2026-06-22 001

## 실행 요약

ORDER 076~079의 1차 구현을 수행했다.

이번 작업의 핵심은 `1 -> 2 -> 3` 구간에서 코드와 LLM의 권한을 분리하는 것이다. 2가 전체 내부 장부를 그대로 3에게 넘기지 않고, 0/code가 `route=2` 진입 조건을 먼저 검사한 뒤 2가 최종 답변용 브리프를 따로 만들어 3에게 넘기도록 바꿨다.

## 구현 내용

1. `Node2HandoffFrame`을 추가했다.
   - `route=2` 진입 시 필수 데이터가 있는지 코드가 검사한다.
   - L루프 실행 여부, L1/L2/L3 산출물 존재 여부, search/read_doc 결과 수를 기록한다.
   - 이 판단은 의미 판단이 아니라 절대정보 기반 조건 검사다.

2. `Node3InputBriefFrame`을 추가했다.
   - 3에게 줄 문서 추출과 허용 claim만 따로 구성한다.
   - 내부 추적용 식별자나 장부용 필드명은 LLM payload/prompt에 넣지 않도록 정리했다.
   - 3은 이 브리프만 보고 최종 답변을 만든다.

3. node_4 gatekeeper를 brief-grounded 검사로 바꿨다.
   - 4는 전체 boundary가 아니라 3이 실제로 받은 브리프와 최종 답변을 대조한다.
   - `unsupported_claims`, `contradictions`를 스키마에 추가했다.

4. pretty runtime에 다음 항목을 추가했다.
   - `route=2 handoff`
   - `node_3 input brief`
   - `node_4 gatekeeper`의 checked/unsupported/contradictions 수

## 검증

- `python -m compileall songryeon_core main.py` 통과.
- `python main.py smoke-test` 통과.
- 캡처 테스트 기준으로 final reporter와 node_4의 prompt+payload 문자열에 다음 내부 용어명이 남지 않음을 확인했다.
  - `source_data_ids`
  - `boundary_id`
  - `trace_id`
  - `data_id`
  - `frame_id`
- `python main.py qwen-turn "너는 누구니?" --timeout 120 --pretty` 통과.

## 남은 문제

Qwen 실행에서 L2 검색어와 검색 결과가 아직 흔들린다. 예를 들어 `너는 누구니?` 질문이 정체성 문서 대신 실행 기록 문서를 읽는 경우가 있었다.

이번 작업은 3에게 내부 장부를 그대로 먹이지 않는 권한 경계 정리에 집중했다. 다음 단계는 L2가 내부 문서 종류와 질문 의도를 더 안정적으로 연결하게 만드는 검색 품질 개선이다.
