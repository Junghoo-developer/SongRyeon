# ORDER 126: Runtime All Document Extract Display v0

## 목표

터미널 runtime 출력에서 실제 `read_doc` / `read_artifact` tool result가 여러 개 존재할 때, 최신 1개만 보여주는 표시 혼동을 줄인다.

## 배경

ORDER_123과 ORDER_124 이후 장부 기준 count는 다음처럼 분리되었다.

- 실제 `read_doc` 도구 원문 읽기 수
- node_3에 공급된 document context 수
- search candidate 수
- unread candidate 수

하지만 live qwen 테스트에서 `node_0 document material packet`과 `node_3 input brief`는 `actual_read=2`를 보여주는 반면, terminal의 top-level `read_doc [TOOL_RESULT:DOCUMENT_EXTRACT]` 줄은 1개 문서만 보여 사람이 "정말 2개 읽었나?"를 헷갈릴 수 있었다.

## 구현 범위

1. `terminal_view.py`의 runtime 표시가 `tool_result:read_doc`과 `tool_result:read_artifact` record를 모두 나열한다.
2. same-turn L reroute처럼 run-scoped document extract record가 존재할 때는 최신 L run의 extract record를 우선 표시한다.
3. 표시만 바꾼다. count 계산, L loop 검색/읽기 정책, node_3 payload, node_4 guard는 바꾸지 않는다.

## 정보 등급

- 표시되는 document extract record의 존재, `data_id`, `doc_id`, `char_count`는 절대정보다.
- 이 발주서는 문서 의미 요약이나 관련성 판단을 추가하지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- 추가 pytest:
  - runtime view가 여러 document extract tool result를 모두 표시한다.
  - 최신 L run-scoped document extract record가 있으면 과거 run extract를 대표 표시에서 제외한다.

## 금지

- L 검색 전략 변경 금지
- read_doc 예산 변경 금지
- node_3 문서 요약 추가 금지
- node_4 guard 약화 금지
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 금지
