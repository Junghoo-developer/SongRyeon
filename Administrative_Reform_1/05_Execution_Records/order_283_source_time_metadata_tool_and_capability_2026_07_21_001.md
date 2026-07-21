# ORDER 283 실행 기록: Source Time Metadata Tool And Capability v0

- 실행일: 2026-07-21
- 결과: 완료
- 발주서: `ORDER_283_SOURCE_TIME_METADATA_TOOL_AND_CAPABILITY_V0.md`

## 1. 구현

새 읽기 전용 도구 `inspect_source_time_metadata`를 추가했다. 도구는 호출자가 지정한
`document|code` scope와 정확한 상대경로 하나만 검사하고 다음 절대정보를 반환한다.

- 검사 상태와 파일 존재 여부
- 정규화 상대경로와 source kind
- 도구 관측 시각 UTC
- 원본 파일 수정 시각 UTC
- 파일 크기
- SHA-256 content hash
- `generated_by=CODE:SOURCE_TIME_METADATA_INSPECTOR`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

경로 검사는 기존 workspace read-only 정책을 재사용한다. 절대경로, root 탈출,
symbolic link, 제외 폴더, 비밀 파일, 허용되지 않은 확장자는 거부한다.

`ToolCatalogItem`과 `ToolSpec`에는 `capabilities` 절대정보를 추가하고 catalog schema를
0.2로 올렸다. 새 도구는 다음 capability를 가진다.

- `temporal_metadata`
- `content_hash`
- `exact_source_path`

기존 7개 도구에도 실제 기능에 맞는 listing/search/original-read capability를 붙였다.
smoke에서 ToolCatalog 도구 수가 8개로 기록되는 것을 확인했다.

## 2. 유지한 경계

- CODE가 최신 파일이나 중요한 파일을 선택하지 않는다.
- 여러 파일을 시간순으로 정렬하지 않는다.
- 수정 시각과 관측 시각 중 어느 쪽이 더 중요한지 판단하지 않는다.
- Git history와 R/Vessel 이력을 조회하지 않는다.
- LToolScope/L2 실행기는 새 도구를 아직 선택하거나 실행하지 않는다.
- L3 및 node_2/node_3 downstream 계약은 변경하지 않았다.

따라서 이번 결과는 시간 절대정보 도구와 catalog 등록 완료이며, L루프 자동 시간 검색
완료가 아니다.

## 3. 검증

```text
python -m compileall songryeon_core main.py
PASS

python -m pytest tests/test_order_283_source_time_metadata_tool_and_capability.py tests/test_order_134_l_tool_scope_budget_partition.py tests/test_order_133_codebase_readonly_inspection.py tests/test_order_267_external_workspace_read_only_boundary.py -q
27 passed, 2 skipped

python -m pytest
537 passed, 2 skipped, 5 deselected

python main.py smoke-test
SMOKE_TEST_OK
tool_catalog_count=8

git diff --check
PASS
```

두 skip은 현재 Windows host에서 테스트용 symbolic link 생성이 허용되지 않아 발생했다.

## 4. 다음 단계

다음 발주는 L1의 `temporal_requirement_status`, ToolCatalog capability, LToolScope와 예산을
L2에 함께 공급해 실제 도구 선택을 열어야 한다. 이때 시간 metadata 후보와 실제
`read_doc|read_code_file` 원문 확보를 별도 장부로 유지해야 한다.
