# L loop 및 메타정보 소비 경계 감사 2026-07-14-001

## 1. 감사 목적

이번 감사는 새 기능을 구현하기 위한 작업이 아니다. 다음 두 질문을 현재 코드와 기존 라이브 실행 기록으로 확인하는 작업이다.

1. L loop가 실제 코드 원문을 읽고도 사용자의 질문에 필요한 부분을 충분히 공급하지 못한 원인은 무엇인가?
2. 절대/상대/혼합 정보 분류가 node_2 -> node_3 -> node_4에서 실제 행동을 통제하는가, 아니면 표시용 딱지에 머무는가?

감사 중 휴리스틱 추가, validator 완화, 예산 증액, 프롬프트 임시 덧칠은 하지 않았다.

## 2. 감사 전 체크포인트

- 체크포인트 commit: `12a5318 feat: checkpoint routing and reporting guards through ORDER 257`
- 범위: ORDER 251~257 및 그에 딸린 코드, 테스트, 발주서, 실행 기록
- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: `444 passed, 5 deselected in 79.53s`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

이 체크포인트는 감사 전 기존 작업을 보존하기 위한 기준선이다.

## 3. 기존 라이브 사례의 절대정보

근거 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_256_257_live_validation_2026_07_12_001.md`

확인값:

- route sequence: `[L, L, 2]`
- 실제 top-level L run: 1회
- 차단된 top-level L reroute 요청: 1회
- L 내부 continuation: 12회
- 고유 `read_code_file` 원문 파일 수: 1개
- `read_doc` 원문 수: 0개
- node_3에 공급된 source-code context: 12개
- L evidence acquisition: `original_material_acquired`
- L semantic goal match: `partial`
- node_2 catalog에는 읽은 코드 원문 재료가 있었지만, node_2 LLM은 일반적인 다른 재료를 primary로 선택함
- node_4는 최종 답변을 `needs_revision`으로 차단함

따라서 이 사례는 “아무것도 읽지 못한 실패”가 아니다. 같은 코드 파일의 앞부분을 여러 번 읽었지만, 질문에 필요한 위치까지 도달하지 못한 실패에 가깝다.

## 4. L loop 감사 결과

### L-1. 코드 원문 읽기가 파일 앞부분에 고정되어 있다

- 위치: `songryeon_core/tools/code_tools.py:120`
- 위치: `songryeon_core/tools/tool_runner.py:200`
- 현재 동작: `read_code_file`은 기본 최대 12,000자를 읽고 `text[:max_chars]`만 반환한다.
- 빠진 것: offset, line range, symbol range, 다음 구간 continuation 좌표
- 판정: **높은 위험**

큰 파일의 뒤쪽 구현을 물어도 L은 같은 파일 첫 12,000자만 다시 받을 수 있다. 이는 모델 크기보다 도구 계약의 한계다.

### L-2. “원문이 잘렸다”는 절대정보가 node_3까지 보존되지 않는다

- 위치: `songryeon_core/core/schemas.py:2177`
- 위치: `songryeon_core/nodes/node_2_handoff.py:2643`
- 현재 동작: tool result에는 `truncated`가 있으나 `Node3BriefDocument`에는 해당 필드가 없다.
- 추가 문제: node_3는 잘린 text와 파일 전체 `char_count`를 함께 받을 수 있다.
- 판정: **높은 위험**

node_3 입장에서는 12,000자만 받았는데도 파일 전체를 공급받은 것처럼 오해할 여지가 있다. 코드가 확정할 수 있는 truncation/range 정보가 downstream에서 사라진다.

### L-3. revision L3가 최초의 코드 전용 tool-scope 근거를 잃는다

- 최초 L3 입력: `songryeon_core/loops/l_loop.py:1307`
- revision L3 입력: `songryeon_core/nodes/l3_result_keeper.py:181`
- code-evidence 기대 판정: `songryeon_core/nodes/l3_result_keeper.py:1521`
- 판정: **높은 위험**

최초 L3에는 `L_tool_scope_frame` ID가 들어가지만 revision L3 입력에는 그 ID가 보존되지 않는다. L1이 `source_code_file`을 명시하지 않은 경우 revision은 이번 일이 코드 원문 획득 작업이었다는 근거를 잃을 수 있다.

이 때문에 다음 두 상태가 동시에 나타날 수 있다.

- 실제로는 code original 1개를 읽음
- 최소 원문 요구 수 계산에서는 `required=1 / actual=0`으로 남음

### L-4. 코드 읽기 예산은 선언되어 있지만 실제 사용 장부와 continuation 판단에 연결되지 않는다

- tool budget: `songryeon_core/core/schemas.py:5114`
- code budget partition: `songryeon_core/core/schemas.py:3892`
- revision budget 갱신: `songryeon_core/loops/l_loop_revision_tool_attempt.py:190`
- continuation 판단: `songryeon_core/loops/l_loop_continuation.py:40`
- 판정: **높은 위험**

`LToolBudgetPartitionFrame`에는 `code_read_budget`이 있지만, 공용 `ToolUseBudgetFrame`에는 code read count/path history가 없다. revision budget 갱신과 continuation 판단도 주로 `read_doc` 중심이다.

즉 “코드를 몇 번 읽었는가”, “어느 파일의 어느 구간을 이미 읽었는가”, “code read 예산이 얼마나 남았는가”가 하나의 일관된 장부로 관리되지 않는다.

### L-5. revision 기억 구조가 문서 중심이라 실제 `read_code_file` 이력을 잃는다

- 위치: `songryeon_core/core/schemas.py:4024`
- 위치: `songryeon_core/core/schemas.py:4234`
- 위치: `songryeon_core/nodes/l2_revision_input.py:271`
- 판정: **높은 위험**

revision 입력에는 `read_document_names`와 unread document ID는 있지만, 읽은 code path/range 목록은 없다. 이전 tool 이름 허용 목록도 `search_docs`, `read_doc`, `read_artifact`뿐이다.

그 결과 직전 실제 도구가 `read_code_file`이어도 revision L2에게는 `search_docs`처럼 보일 수 있다. L2가 “같은 코드 앞부분을 이미 읽었다”는 절대정보를 바탕으로 다음 행동을 정할 수 없는 구조다.

### L-6. 같은 파일을 여러 번 읽은 raw 실행 기록과 node_3 공급 context가 분리되지 않는다

- 공급 context 조립: `songryeon_core/nodes/node_2_handoff.py:2643`
- 고유 파일 count 계산: `songryeon_core/nodes/node_2_handoff.py:3073`
- 판정: **중간 위험**

절대 실행 장부에는 반복 read 12건을 모두 남기는 것이 맞다. 그러나 node_3 답변 재료도 record ID만 기준으로 12개가 만들어져 같은 파일 앞부분이 중복 공급된다.

삭제가 답은 아니다. 다음 두 보기를 분리해야 한다.

- 감사용 raw tool ledger: 모든 실행을 보존
- node_3 delivery view: `(file_path, range 또는 content hash)` 기준으로 중복을 제거

### L-7. 이미 잘 되어 있는 부분

- 후보만 찾은 상태와 실제 원문 획득 상태를 구분한다.
- `read_doc`과 `read_code_file` 획득을 별도 count로 기록한다.
- L3 semantic 판단은 “원문이 비어 있지 않음”과 “질문에 충분히 관련됨”을 구분하도록 요구받는다.
- node_4는 이번 라이브 사례에서 불충분한 최종 답변을 실제로 차단했다.

따라서 L loop 전체를 다시 만들 이유는 없다. 코드 읽기 continuity와 downstream truncation 계약을 좁게 보강하는 것이 맞다.

## 5. 메타정보 소비 경계 감사 결과

### M-1. 절대/상대/혼합 분류는 schema 수준에서 실제로 구분된다

- 위치: `songryeon_core/core/schemas.py:169`
- 위치: `songryeon_core/core/schemas.py:237`
- 위치: `songryeon_core/nodes/node_2_metainfo_boundary.py:1437`
- 판정: **통과**

현재 구조는 다음 차이를 validator로 강제한다.

- 상대정보: 특정 하나의 source record/field와 1:1 대응
- 혼합정보: 여러 source를 묶은 source bundle

node_2 boundary도 텍스트 단어를 보고 분류하는 휴리스틱이 아니라 source record의 대응 모양을 사용한다.

### M-2. node_2의 분류/답변 모드는 실제 node_3 재료 전달 방식을 바꾼다

- answer-basis schema: `songryeon_core/core/schemas.py:1219`
- material policy: `songryeon_core/nodes/node_2_handoff.py:897`
- 회귀 테스트: `tests/test_order_132_material_delivery_policy.py`
- 판정: **통과**

현재 세 모드는 단순 표시가 아니다.

- `absolute_first`: raw 원문 우선
- `relative_allowed`: L3 summary가 raw text를 대체할 수 있음
- `mixed_or_uncertain`: 혼합/불확실성 자세와 fallback 정책 적용

즉 메타정보 분류가 실제 payload 조립에 영향을 준다. SongRyeon Core는 “딱지만 붙이는 시스템”보다 한 단계 앞서 있다.

### M-3. node_2 material catalog는 답변 재료/상태/과정을 구조적으로 나눈다

- 위치: `songryeon_core/nodes/node_2_metainfo_boundary.py:623`
- 위치: `songryeon_core/nodes/node_2_metainfo_boundary.py:835`
- 판정: **부분 통과**

장점:

- `answer_ready`, `status`, `process` channel을 분리한다.
- read document, read code, recent memory, Vessel material을 답변 가능 재료로 표시한다.
- node_2 prompt는 일반 질문에서 process ledger를 primary answer basis로 고르지 않도록 요구한다.

한계:

- catalog row와 `available_evidence_sources`에는 source의 `info_class`, `source_mode`, `claim_alignment`가 직접 포함되지 않는다.
- 별도의 relative/mixed sample에는 info class가 있지만, node_2가 보는 모든 재료 행이 동일한 메타정보 소비 계약을 갖지는 않는다.

따라서 “이 재료가 답변 가능하다”와 “이 재료를 어느 주장 강도로 소비할 수 있다”가 아직 한 행에서 완전히 결합되지 않았다.

### M-4. node_3는 자유형 본문을 만들고, 주장별 출처 연결을 반환하지 않는다

- 출력 prompt: `songryeon_core/prompts/node_3_reporter_v0.md:9`
- report 저장: `songryeon_core/nodes/node_3_reporter.py:190`
- ReportFrame: `songryeon_core/core/schemas.py:1082`
- 판정: **높은 위험**

`ReportFrame`에는 허용된 absolute/relative/mixed ID 목록이 저장되지만, validator는 최종 문장의 각 주장과 이 ID를 연결하지 않는다. node_3 LLM 출력도 `body_markdown` 한 덩어리다.

따라서 다음을 코드가 직접 확인할 수 없다.

- 어느 문장이 어느 source를 사용했는가
- 상대정보 해석이 절대사실처럼 표현되었는가
- 여러 source를 합친 혼합 판단이 단일 source 사실처럼 세탁되었는가

### M-5. node_4는 많은 절대 경계를 막지만 일반적인 의미 세탁은 LLM 검사에 의존한다

- code guard: `songryeon_core/nodes/node_4_gatekeeper.py:378`
- gate prompt: `songryeon_core/prompts/node_4_gatekeeper_v0.md:23`
- 회귀 테스트: `tests/test_order_257_node4_task_fulfillment_and_body_consistency.py`
- 판정: **부분 통과**

code가 직접 강제하는 것:

- count mismatch
- 최근 기억 원문 없이 과거 대화 주장
- document 역할 혼동
- Vessel 상태/ID 누출
- task 미이행 및 본문-절대 grounding 모순

LLM node_4가 의미적으로 검사하는 것:

- proposal/example을 실행 완료 사실처럼 말했는가
- `absolute_first`인데 근거 없는 추측을 강하게 단정했는가
- `mixed_or_uncertain`인데 한계를 숨겼는가
- 해석/평가/요약이 supplied facts와 연결되는가

이 분업 자체는 원칙에 맞다. 코드는 의미를 대신 판단하면 안 된다. 다만 node_3가 주장별 구조를 내지 않기 때문에, 일반적인 상대/혼합 정보 세탁은 여전히 node_4의 자유형 의미 판정에 크게 의존한다.

## 6. ARM-Eval 결과와의 비교 판정

감사 대상 보고서:

- `output/pdf/ARM_EVAL_EXPERIMENT_RESULTS_REPORT_KO_2026_07_14.pdf`

보고서가 지지하는 범위:

- role label을 정확히 붙이는 것만으로는 상대정보 세탁이 유의하게 줄지 않았다.
- “이 정보는 이렇게 소비해야 한다”는 명시적 consumer rule을 추가했을 때 세탁률이 감소했다.
- 실험은 8개 고정 사례의 prompt-level 비교이며 SongRyeon runtime 안전성을 직접 증명하지 않는다.

SongRyeon Core에 대한 판정:

1. SongRyeon은 label-only 시스템은 아니다. answer basis에 따라 실제 raw/summary payload가 달라지고 node_4 guard도 존재한다.
2. 그러나 claim-level source linkage가 없어 ARM-Eval이 시사한 “소비 규칙의 구조적 강제”는 아직 완성되지 않았다.
3. 따라서 현재 상태를 “메타정보 분류가 안전성을 완전히 보장한다”고 홍보하면 과장이다.
4. 현재 정확한 표현은 “메타정보를 schema, 재료 전달 정책, 최종 검사에 실제 사용하지만, 자유형 최종 문장의 주장별 소비 계약은 아직 연구/개발 중”이다.

## 7. 다음 패치 권고 순서

### 우선순위 1: L code-read continuity MVP

한 발주서 안에서 다음만 다루는 것이 안전하다.

1. revision L3까지 `L_tool_scope_frame`을 보존한다.
2. 읽은 code path/range와 code read count/remaining budget을 장부에 추가한다.
3. `read_code_file`이 offset/range 또는 symbol 기반 다음 구간을 읽을 수 있게 한다.
4. LLM이 읽을 path/range를 선택하고, code는 실제 파일/범위/예산만 검증한다.
5. node_3에는 `truncated`, 반환 범위, 전체 길이를 절대정보로 공급한다.
6. raw tool event는 전부 보존하고 node_3 delivery view만 정확한 path/range 기준으로 중복 제거한다.

### 우선순위 2: 메타정보 claim-consumption contract 감사/설계

바로 구현하지 말고 먼저 schema를 결재해야 한다.

후보 구조:

- node_3가 `body_markdown` 외에 structured claim item을 반환
- 각 claim에 `claim_id`, `source_refs`, `used_info_class`, `assertion_modality`를 기록
- code는 ID 존재, enum, source linkage만 검증
- node_4 LLM은 claim의 의미와 말하기 강도가 해당 modality에 맞는지 판정
- code가 단어 짜깁기 휴리스틱으로 의미를 판정하지 않음

### 우선순위 3: 비교 실험

ARM-Eval 후속은 다음 조건을 분리해야 한다.

- label only
- prompt consumer rule
- structured claim linkage
- structured linkage + node_4 semantic gate

이 비교가 있어야 SongRyeon 구조가 일반 prompt보다 실제로 무엇을 더 막는지 주장할 수 있다.

## 8. 하지 말아야 할 것

- L 예산만 늘려 같은 파일 앞부분을 더 많이 읽게 만들기
- 키워드가 보이면 다음 범위를 고르는 code heuristic 추가
- 중복 tool event를 삭제해 감사 가능성 훼손
- node_4 guard 약화
- node_3 의미 본문을 code가 대신 작성
- ARM-Eval 결과를 SongRyeon 제품 안전성 증명으로 과장

## 9. 최종 판정

### 초등학생식 한 줄

송련은 공책에 “사실/해석/여러 자료를 섞은 판단” 딱지를 붙이고 그 딱지에 따라 재료를 다르게 주는 데까지는 성공했다. 하지만 최종 답변의 각 문장이 어느 딱지를 썼는지 번호표를 붙이지는 못했다.

L loop는 머리가 나빠서 실패한 것이 아니라, 큰 코드책의 첫 장만 12번 다시 읽게 만든 배관 때문에 실패했다.

### 총괄 판정

- 현재 기준선: 보존 완료
- L loop 전체 재설계 필요: 없음
- L code-read continuity 패치 필요: 있음, 우선순위 높음
- 메타정보가 실제 행동에 영향: 있음
- claim-level 소비 강제 완성: 아님
- 즉시 제품 안전성 주장 가능: 아님
- 다음 안전한 한 수: L code-read continuity를 먼저 좁게 고친 뒤, claim-consumption contract를 별도 설계
