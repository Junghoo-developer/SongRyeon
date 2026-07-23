# ORDER 285 실행 기록

- 발주: `ORDER_285_L_TEMPORAL_EVIDENCE_DOWNSTREAM_AND_CONTEXT_EXPOSURE_HONESTY_V0`
- 실행일: 2026-07-23
- 상태: 구현 및 검증 완료

## 1. 구현 결과

`inspect_source_time_metadata` 결과를 문서 원문 extract와 다른 절대근거로
취급하고 다음 경로로 전달했다.

`L tool result -> L3AchievementFrame -> LLoopReturnSummaryFrame
-> node_2 boundary -> Node3InputBriefFrame -> node_3 payload/grounding`

다음 세 count는 서로 섞이지 않는다.

1. 실제 `read_doc/read_code_file` 원문 읽기
2. 별도 document context pack을 통한 원문 공급
3. 시간 메타데이터 전용 검사

node_3 payload에는 raw DataStore ID 대신 안전한 시간 material 번호와
검증된 path, 관측 시각, 수정 시각, 크기, hash가 들어간다.

## 2. 권한 경계

- CODE: 시간 도구 성공 여부, count, path와 result 대응, 절대 필드 복사
- L1 LLM: 시간 근거 필요 여부와 원문 요구 여부 판단
- L3 LLM: 확보된 시간 근거가 사용자 목표에 의미상 맞는지 판단
- node_3 LLM: 시간 값을 사용자에게 설명

CODE가 사용자 문장의 시간 관련 단어를 의미 분류하는 휴리스틱은 추가하지 않았다.

## 3. 자동 검증

```text
python -m compileall songryeon_core main.py
통과

python -m pytest
548 passed, 2 skipped, 5 deselected in 197.18s

python main.py smoke-test
SMOKE_TEST_OK

python -m pytest tests/test_order_285_l_temporal_evidence_downstream.py
3 passed
```

skip 2개는 Windows 환경의 symlink 지원 여부에 따른 기존 환경 skip이다.

## 4. live 검증

입력:

```text
Administrative_Reform_1/04_Orders/ORDER_284_L2_TEMPORAL_METADATA_SELECTION_AND_EXECUTION_V0.md
파일의 수정 시각을 확인해줘. 파일 원문을 읽었는지와 시간 메타데이터만
검사했는지를 구분해서 말해줘.
```

첫 live 재현:

- 상태: `ok`
- 실제 `read_doc`: 0
- node_3 공급 문서 context: 1
- 시간 메타데이터 검사: 1
- 시간 메타데이터 성공: 1
- 수정 시각: `2026-07-21T09:39:20.753959+00:00`
- node_4: `pass`

따라서 ORDER 284에서 발생했던 “도구는 시간을 확인했지만 node_3가 값을 받지
못하는 문제”는 재현되지 않았다.

후속 live 재실행:

- 상태: `ok`
- 시간 근거 요구: `required`
- 시간 근거 상태: `satisfied`
- 시간 검사: 1 / 성공 1
- 최종 L 상태: `achieved`
- node_4: `pass`
- L1 출력: `minimum_read_documents=0`,
  `artifact_requirement_mode=exact_one`
- revision 추가 원문 읽기: `read_doc=1`

후속 실행은 수정 시각을 정확히 보고했고 원문 읽기와 시간 검사를 구분했다.
다만 L1이 원문 최소 읽기 0과 명시 문서 원문 요구 `exact_one`을 함께 선택해
불필요한 revision 읽기가 발생했다.

## 5. 남은 위험

ORDER 285의 시간 근거 downstream 전달 문제는 닫혔다. 남은 문제는 전달관이
아니라 L1 계약의 내부 정합성이다. prompt 안내만으로는
`minimum_read_documents=0`과 `artifact_requirement_mode=exact_one`의 모순을
항상 막지 못했다.

후속 작업에서는 사용자 문장 키워드 휴리스틱이나 silent clamp가 아니라,
L1이 스스로 낸 구조 필드 사이의 모순을 검증하고 실패를 정직하게 기록하는
작은 계약 validator를 별도 발주로 검토한다.
