# ORDER 284: L2 Temporal Metadata Selection And Execution v0

- 상태: 구현 완료
- 작성일: 2026-07-21
- 선행 발주: `ORDER_282_L1_TEMPORAL_REQUIREMENT_CONTRACT_V0.md`, `ORDER_283_SOURCE_TIME_METADATA_TOOL_AND_CAPABILITY_V0.md`

## 1. 목표

L1이 시간 근거 필요 여부를 상대정보로 판단한 뒤, L2가 ToolCatalog와 정확한 파일
좌표를 보고 `inspect_source_time_metadata` 사용 여부를 선택할 수 있게 한다. 선택된 도구는
L루프 안에서 실제 실행하고, 결과를 원문 읽기와 구분된 절대정보로 보존한다.

이번 발주는 여러 파일 중 최신 파일을 CODE가 고르거나 정렬하는 기능이 아니다.

## 2. 선택 계약

- `temporal_metadata` capability를 가진 도구는 LToolScope의 문서/코드 group 선택과 별도로
  L2에게 보존해 보여준다. capability 보존은 도구 가시성 정책이며 도구 사용 결정이 아니다.
- CODE는 현재 사용자 입력에 정확한 workspace 상대경로가 문자 그대로 있고 실제 파일이
  존재할 때만 `available_temporal_source_paths`를 만든다.
- 각 좌표는 `source_scope=document|code`, `source_path`만 가진다.
- L2 LLM은 L1의 `temporal_requirement_status=required`이고 위 목록에 정확한 좌표가 있을 때
  `inspect_source_time_metadata`를 선택할 수 있다.
- L2가 목록 밖 scope/path를 만들면 schema 경계에서 실패한다.
- L2 실패 fallback은 시간 의미를 대신 판단하지 않으며 시간 도구를 자동 선택하지 않는다.

## 3. 실행·기록 계약

- 선택된 `source_scope`, `source_path`를 `L2QueryPlanCandidate`와 `L2QueryFrame`에 보존한다.
- ToolRunner가 `inspect_source_time_metadata`를 한 번 실행한다.
- 결과 record는 `tool_result:inspect_source_time_metadata`로 남는다.
- 시간 메타데이터 결과는 `read_doc` 또는 `read_code_file` 원문 근거 count를 늘리지 않는다.
- 성공 여부는 `inspection_status=ok`라는 CODE 절대정보로만 닫는다.
- 시간 메타데이터가 사용자 질문을 충분히 해결했는지는 이번 발주에서 판정하지 않는다.

## 4. 금지

- 키워드 휴리스틱으로 시간 필요 여부를 다시 판단하지 않는다.
- CODE가 여러 파일을 최신순으로 정렬하거나 중요 파일을 고르지 않는다.
- Git history, R/Vessel, 외부 DB를 열지 않는다.
- revision L2 시간 재검사, L3 시간 충분성 판단, node_2/node_3 최종 답변 계약은 바꾸지 않는다.
- 시간 메타데이터를 원문 읽기 성공으로 가장하지 않는다.

## 5. 테스트

1. `temporal_metadata` capability 도구가 LToolScope 필터 뒤에도 보존된다.
2. L1 required + 허용된 정확 좌표를 고른 L2 plan은 통과한다.
3. 허용 목록 밖 path/scope와 L1 not_required 시간 도구 선택은 실패한다.
4. L2 실패 fallback은 시간 도구를 CODE가 자동 선택하지 않는다.
5. 시간 도구 실행 결과는 별도 tool result로 남고 원문 읽기 count는 0을 유지한다.
6. 기존 문서·코드 L2 선택과 L루프 동작은 유지된다.

## 6. 완료 조건

- `python -m compileall songryeon_core main.py`
- 표적 pytest 통과
- 전체 pytest 통과
- `python main.py smoke-test` 통과
- 실행 기록 작성
