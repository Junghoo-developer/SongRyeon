# ORDER 284 L2 시간 메타데이터 선택·실행 기록

- 실행일: 2026-07-21
- 발주서: `ORDER_284_L2_TEMPORAL_METADATA_SELECTION_AND_EXECUTION_V0.md`
- 결과: 구현 및 검증 완료

## 1. 구현 결과

1. `temporal_metadata` capability를 가진 읽기 전용 도구는 LToolScope의 문서/코드 group
   필터 뒤에도 L2에게 보존된다.
2. CODE는 현재 사용자 입력에 문자 그대로 등장하고 workspace에 실제 존재하는 문서/코드
   상대경로만 `available_temporal_source_paths`로 만든다.
3. L2는 L1의 `temporal_requirement_status=required`와 위 좌표 목록을 함께 입력받는다.
4. L2가 `inspect_source_time_metadata`를 고르면 `source_scope`와 정확한 상대경로를
   `L2QueryPlanCandidate`, `L2QueryFrame`, tool result에 보존한다.
5. 목록 밖 경로, scope 불일치, L1 not_required 상태의 시간 도구 선택은 schema_failed로
   닫힌다.
6. L2 planner 실패 시 CODE fallback은 시간 의미를 대신 판단하지 않고 시간 도구를 자동
   선택하지 않는다.
7. 시간 도구 결과는 `tool_result:inspect_source_time_metadata`로 별도 기록되며,
   `read_doc`, `read_artifact`, `read_code_file` 원문 근거 count에는 포함되지 않는다.
8. terminal view에는 시간 도구의 상태, scope/path, 관측 시각, 수정 시각, 원문 읽기와의
   분리 사실을 표시한다.

## 2. 메타정보 경계

- L1 시간 필요 판단: LLM 상대정보
- L2 시간 도구 사용 선택과 목적: LLM 판단 및 계획
- 사용자 입력에 정확한 경로가 있었는지와 실제 파일 존재 여부: CODE 절대정보
- 파일 관측 시각, 수정 시각, 크기, hash: CODE 절대정보
- 시간 메타데이터가 질문에 충분한지: 이번 발주에서 판단하지 않음

## 3. 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 282~284 및 LToolScope 표적 pytest: `29 passed, 1 skipped`
- 전체 pytest: `545 passed, 2 skipped, 5 deselected`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

Windows 환경에서 symbolic link 생성이 불가능한 기존 보안 테스트 2개는 skip되었다.

## 4. 남은 한계

- 사용자가 정확한 파일 경로를 쓰지 않으면 시간 도구 후보 좌표가 생기지 않는다.
- 여러 파일의 수정 시각을 비교해 최신 파일을 선택하지 않는다.
- revision L2에서 시간 메타데이터를 연속 검사하지 않는다.
- L3가 시간 근거의 의미 충분성을 별도 평가하는 계약은 아직 없다.
- node_2/node_3 최종 답변에 시간 근거를 전용 material로 전달하는 계약은 아직 없다.
