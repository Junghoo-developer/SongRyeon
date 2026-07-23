# ORDER 285: L Temporal Evidence Downstream And Context Exposure Honesty v0

- 상태: 구현 및 검증 완료
- 작성일: 2026-07-23
- 선행 발주: ORDER 282, ORDER 283, ORDER 284

## 1. 문제

ORDER 284 live 실행에서 L2의 `inspect_source_time_metadata`는 정확한 파일을 검사해
수정 시각, 관측 시각, 크기, hash를 기록했다. 그러나 이 절대정보는 L3와 node_3의
답변 재료로 전달되지 않아 최종 답변이 수정 시각을 확인하지 못했다고 말했다.

같은 실행에서 `read_doc=0`이었지만 `document_context_pack`은 명시 문서 원문을
node_3에게 별도로 공급했다. 따라서 다음 세 사실을 분리해야 한다.

1. `read_doc/read_code_file` 도구로 원문을 읽었는가
2. 별도 context pack을 통해 원문 text가 node_3에게 공급됐는가
3. 시간 메타데이터 전용 도구가 파일을 검사했는가

## 2. 목표

1. 시간 메타데이터 tool result를 원문 extract와 다른 절대근거로 L3에 공급한다.
2. L3는 시간 요구 상태와 원문 요구 상태를 별도 필드로 기록한다.
3. L loop return summary와 Node3InputBriefFrame에 시간 검사 결과를 보존한다.
4. node_3 payload와 CODE grounding block이 시간 검사 count와 값을 받는다.
5. 최종 보고는 `도구 원문 읽기 0`을 `원문 text 노출 0`으로 바꿔 말하지 않는다.

## 3. 구현 범위

- `L3AchievementFrame`
  - L1 시간 요구 상태
  - 시간 검사 전체/성공 count
  - 시간 요구 충족 상태
  - 시간 tool result data ID
- `LLoopReturnSummaryFrame`
  - 최신 L3의 시간 검사 상태와 count 복사
- `Node3InputBriefFrame`
  - code가 검증한 시간 메타데이터 material 목록
  - 시간 검사 전체/성공 count
  - 시간 요구 충족 상태
- node_3 LLM payload
  - 내부 DataStore ID 대신 안전한 material 번호와 절대 필드 제공
- CODE grounding block
  - 원문 tool read, 공급 context, 시간 metadata inspection을 별도 줄로 표시
- L1 prompt
  - 사용자가 파일 내용이 아닌 시간 메타데이터만 요구하면
    `minimum_read_documents=0`, `artifact_requirement_mode=not_applicable`을 선택할 수
    있다고 명시한다.

## 4. 권한 경계

- 시간 메타데이터 값, 성공 count, source path 대응: CODE 절대정보
- 시간 근거가 필요한지: L1 LLM 상대/혼합 판단
- 원문 내용도 필요한지와 artifact 요구 관계: L1 LLM 판단
- 시간 요구와 원문 요구의 구조적 충족 여부: CODE count/ID 대조
- 시간 값의 의미 해석과 사용자 설명: node_3 LLM

CODE는 사용자 문장의 `최신`, `수정`, `시간` 같은 단어를 직접 분류하지 않는다.

## 5. 테스트

1. 성공한 시간 tool result는 L3 source와 temporal count에 포함된다.
2. 시간 요구가 `required`이고 성공 결과가 있으면 시간 요구는 `satisfied`다.
3. 시간 요구가 `required`인데 성공 결과가 없으면 `unsatisfied`다.
4. 원문 count는 시간 검사 count 때문에 증가하지 않는다.
5. L return summary와 node_3 brief에 시간 상태가 보존된다.
6. node_3 payload에는 수정 시각 등 절대 필드가 있고 raw DataStore ID는 없다.
7. grounding block은 tool 원문 읽기, 공급 context, 시간 검사를 분리한다.
8. compileall, 전체 pytest, smoke-test를 통과한다.

## 6. 금지

- 시간 tool result를 `read_doc` 또는 원문 읽기로 집계
- 사용자 문장 키워드 휴리스틱 추가
- 여러 파일 중 최신 파일 자동 선택
- document context pack 자동 제거 또는 원문 공급 정책 변경
- L/R 라우팅, 예산, same-turn 반복 횟수 변경
- node_4 guard 약화

## 7. 완료 조건

ORDER 284 live 사례에서 수정 시각 절대정보가 node_3까지 도달하고, 최종 근거 블록이
`read_doc=0`, `supplied context=1`, `temporal inspection=1`을 서로 다른 사실로
표시할 수 있다.

## 8. 구현 결과

- 시간 메타데이터 결과가 L3, 0의 반환 요약, node_2 경계, node_3 brief와
  최종 grounding block까지 별도 근거로 전달된다.
- 첫 live 재현에서 `read_doc=0`, `supplied context=1`,
  `temporal inspection=1`, `temporal success=1`이 분리되어 표시됐고,
  node_3가 수정 시각을 보고했으며 node_4가 통과시켰다.
- 후속 live에서는 L1이 `minimum_read_documents=0`과
  `artifact_requirement_mode=exact_one`을 동시에 선택해 revision에서 원문을
  추가로 읽었다. 시간 근거 전달은 정상 동작했지만 이 L1 계약 모순은 별도 후속
  구조 검증 대상으로 남긴다.
