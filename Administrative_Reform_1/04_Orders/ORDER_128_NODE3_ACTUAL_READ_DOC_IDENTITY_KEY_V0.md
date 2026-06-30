# ORDER 128: Node3 Actual Read Doc Identity Key v0

## 목표

node_3 input brief의 `actual_tool_read_doc_count`가 파일명 중복 때문에 줄어들지 않게 한다.

## 배경

ORDER_127 이후 L return summary와 node_0 material packet은 revision document extract record를 병합하여 `actual_read=7`까지 맞췄다.

하지만 live qwen 테스트에서 node_3 input brief는 `actual_read_doc=6`으로 줄었다.

원인은 서로 다른 문서가 같은 파일명을 가질 수 있기 때문이다.

- `04_Orders/README.md`
- `05_Execution_Records/README.md`

둘은 서로 다른 `doc_id`지만, 사람이 보기 좋은 이름만 뽑으면 둘 다 `README.md`가 된다. node_3 brief helper가 파일명 기준으로 중복 제거하면 절대 count가 틀어진다.

## 구현 범위

1. node_3 actual read document 목록을 만들 때 중복 제거 기준을 파일명(`document_name`)이 아니라 `doc_id` / document extract identity로 둔다.
2. 표시용 label은 사람이 읽기 좋게 유지한다.
   - 파일명이 유일하면 `A.md`처럼 짧게 표시한다.
   - 같은 파일명이 여러 `doc_id`에 있으면 `04_Orders/README.md`처럼 경로를 포함해 표시한다.
3. node_3 LLM prompt, node_4 guard, L 검색 전략은 바꾸지 않는다.

## 정보 등급

- `doc_id`, `data_id`, document extract record 존재 여부, text 존재 여부는 절대정보다.
- 이 발주서는 문서 의미 판단이나 요약을 추가하지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- 추가 pytest:
  - `04_Orders/README.md`와 `05_Execution_Records/README.md`가 서로 다른 실제 read_doc 문서로 2개 count 된다.

## 금지

- node_3 LLM 출력 통제 강화 금지
- grounding block 정책 변경 금지
- L 검색 전략 변경 금지
- read_doc 예산 변경 금지
- node_4 guard 약화 금지
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 금지
