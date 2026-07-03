# ORDER_122 L Revision Unread Candidate Read Path v0

## 목표

L 루프가 검색 후보를 찾고도 `read_doc` 예산을 쓰지 못한 채 `search_docs` revision만 반복하는 문제를 줄인다.

이번 MVP는 예산을 더 늘리는 작업이 아니다. L3가 실패/부분성공이고, 아직 읽지 않은 검색 후보가 있으며, `read_doc` 예산이 남아 있을 때 revision 흐름이 기존 후보 원문을 읽을 수 있게 한다.

## 구현 범위

- L2 revision plan에서만 `read_doc` target을 허용한다.
- 일반 최초 L2 검색은 기존처럼 `search_docs` / `read_artifact` 중심을 유지한다.
- revision L2는 `L2RevisionInputFrame.unread_candidate_doc_ids` 안의 정확한 `doc_id`만 `read_doc`으로 고를 수 있다.
- `remaining_query_attempts=0`이어도 unread candidate와 read budget이 있으면 continuation을 허용한다.
- 이때 revision plan은 `read_doc` 후보만 통과 가능하게 검증한다.
- revision tool 실행기는 `read_doc`을 실행하고, `read_doc` 실행은 `query_count`를 늘리지 않는다.
- `search_docs` 실행만 `executed_queries/query_count`에 기록한다.

## 제외 범위

- 코드가 문서 의미를 대신 판단하지 않는다.
- 어떤 unread candidate가 가장 관련 있는지 code가 고르지 않는다.
- node_3 문서 폭탄 정리/압축은 이번 발주에서 하지 않는다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB, same-turn L reroute 횟수는 건드리지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- 추가 pytest로 다음을 확인한다.
  - revision L2가 unread candidate의 정확한 `doc_id`로 `read_doc` 후보를 만들면 통과한다.
  - 허용 목록 밖 `doc_id`를 `read_doc`으로 고르면 schema/validation 실패한다.
  - query 예산이 0이어도 unread candidate와 read budget이 있으면 continuation이 닫히지 않는다.
  - revision `read_doc` 실행 후 `query_count`는 증가하지 않고 `read_doc_count`만 증가한다.
  - L3 revision result keeper가 새 `read_doc` 결과를 읽은 문서 근거로 반영한다.
