# ORDER 283: Source Time Metadata Tool And Capability v0

- 상태: 구현 완료
- 작성일: 2026-07-21
- 선행 발주: `ORDER_282_L1_TEMPORAL_REQUIREMENT_CONTRACT_V0.md`

## 1. 목표

L1의 시간 근거 필요 판단 다음 단계로, CODE가 정확한 한 파일의 시간·hash 절대정보를
읽기 전용으로 공급할 수 있게 한다. ToolCatalog에는 도구 capability를 명시한다.

이번 발주는 L2 자동 선택, 최신 파일 정렬, 시간 요구 충족 판정까지 열지 않는다.

## 2. 도구 계약

새 도구 이름은 `inspect_source_time_metadata`로 한다.

입력:

- `source_scope=document|code`
- `source_path`: 선택된 root 아래의 정확한 상대경로

출력:

- 입력 scope/path와 실제 정규화 상대경로
- `inspection_status`
- 파일 존재 여부
- CODE 관측 시각 UTC
- 원본 파일 수정 시각 UTC
- 파일 크기
- SHA-256 content hash
- source kind
- `generated_by=CODE:SOURCE_TIME_METADATA_INSPECTOR`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

절대경로, root 탈출, symbolic link, 제외 폴더, secret 파일, 허용되지 않은 확장자는 기존
workspace read-only 정책으로 거부한다.

## 3. ToolCatalog capability

`ToolCatalogItem`과 `ToolSpec`에 `capabilities: list[str]` 절대정보를 추가한다.
catalog schema는 0.2로 올린다.

새 도구 capability:

- `temporal_metadata`
- `content_hash`
- `exact_source_path`

기존 도구에도 현재 실제 기능에 맞는 capability를 명시한다. capability는 도구 기능
표지이며 질문 의미나 도구 선택 결과가 아니다.

## 4. 경계

- 어떤 파일이 중요한지 CODE가 판단하지 않는다.
- 여러 파일을 최신순으로 정렬하지 않는다.
- 수정 시각과 관측 시각 중 무엇이 사용자 요구에 더 중요한지 결정하지 않는다.
- Git history, R/Vessel 이력, 외부 DB를 읽지 않는다.
- LToolScope와 L2가 새 도구를 선택하는 배선은 다음 발주로 미룬다.
- L3와 node_2/node_3 downstream 계약은 변경하지 않는다.

## 5. 테스트

1. 정확한 문서/코드 상대경로에서 시각·크기·hash를 반환한다.
2. 관측 시각은 도구 실행 시각이며 파일 수정 시각과 별도 필드다.
3. absolute/outside/symlink/secret/unsupported 경로를 거부한다.
4. ToolCatalog가 새 도구와 capability를 보존한다.
5. capability가 빈 값 또는 중복이면 schema 검증이 실패한다.
6. 기존 문서·코드 도구 동작은 유지한다.

## 6. 완료 조건

- compileall 통과
- 표적 pytest 통과
- 전체 pytest 통과
- smoke-test 통과
- 실행 기록 작성
