# ORDER 261: Code Range Material Assembly And L3 Recheck v0

## 1. 배경

ORDER 258~260으로 `read_code_file`의 정확한 경로, 문자 구간 장부, 다음 구간 이어 읽기는
실제로 작동하게 되었다. 그러나 2026-07-14 로컬 Qwen 시험에서는 다섯 구간을 읽고도
목표 함수를 설명하지 못했고, 정상적인 부분 코드 조각을 `파싱 오류`나 `들여쓰기 문제`로
오해한 최종 답변을 node_4가 통과시켰다.

감사 결과 원인은 다음과 같았다.

1. 각 부분 구간을 완전한 Python 파일처럼 `ast.parse`했다.
2. 코드 원문과 구간 경계는 내부 ID로 연결되어 있지만 node_3 LLM payload에서는 분리됐다.
3. L3 revision keeper는 새 코드 구간을 읽은 뒤 의미 적합성을 다시 판단하지 않았다.
4. 코드 원문이 `supplied_document_contexts`와 `read_documents`에 중복될 수 있었다.
5. user-facing grounding count가 실제 task-focused payload count와 달라질 수 있었다.
6. Ollama 모델 자체는 40,960 token context를 지원하지만 direct adapter가 `num_ctx`를
   지정하지 않아 실제 실행은 4,096 token context였고, 긴 node_3 코드 재료의 뒤쪽이 잘렸다.

## 2. 목표

여러 `read_code_file` 결과를 각각의 정확한 범위와 결합한 하나의 코드 구간 재료로
node_3에게 공급한다. 부분 구간은 전체 파일 문법 오류로 판정하지 않으며, revision으로
새 구간을 읽을 때마다 L3 LLM이 의미 적합성을 다시 판단하게 한다.

## 3. 구현 범위

1. 코드 구간 재료는 다음 절대정보를 한 항목에 함께 보존한다.
   - 안전한 payload 전용 material ref
   - file path
   - `[range_start_char, range_end_char_exclusive)`
   - returned/total char count
   - truncation 상태
   - 원문 text
   - 분석 범위와 parse 상태
2. 부분 구간은 `analysis_scope=partial_range`, `parse_status=not_run_partial_range`로 기록한다.
3. 완전한 파일 구간에만 Python AST parse를 실행한다.
4. AST 분석용 문자열의 맨 앞 UTF-8 BOM은 인코딩 표지로만 제거한다. 원본 파일은 이번 발주에서 대량 변환하지 않는다.
5. node_3 payload에서 코드 원문은 `source_code_range_materials` 한 채널로만 공급한다.
6. 일반 문서 호환용 `read_documents` alias에는 코드 원문을 중복하지 않는다.
7. L3 revision은 현재 L run에서 읽은 코드 구간을 입력받아 의미 적합성을 다시 판단한다.
8. 다음 세 조건이 모두 맞을 때만 revision 결과를 구조적 달성으로 닫는다.
   - L3 LLM `semantic_goal_match_status=matched`
   - CODE가 비어 있지 않은 원문 확보를 확인
   - CODE가 파일/요구 수량/goal-match 구조 조건 충족을 확인
9. node_3 grounding block의 원문 count는 실제 LLM payload에 들어간 일반 문서와 코드 구간 수로 계산한다.
10. node_4 prompt에는 부분 구간의 parse 미실행을 파일 문법 오류로 해석하지 않는 경계를 추가한다.
11. node_2 answer material catalog의 `read_code_file` 항목은 파일 경로, 정확한 문자 범위,
    전체 길이, 잘림 여부, 반환 문자 수만 공급한다.
    - node_2는 코드 본문 해설자가 아니라 node_3에 넘길 근거 좌표 선택자다.
    - 코드 원문은 node_2가 해당 evidence ref를 고른 뒤 node_3에게만 공급한다.
    - answer-ready 항목은 상태/과정 장부보다 먼저 표시하되 evidence ref 자체는 바꾸지 않는다.
12. `evidence_requirement=required`이고 answer-ready 재료가 존재할 때 node_2가 그중 하나도
    primary/supporting으로 고르지 않으면 schema 실패로 처리하고 기존 1회 repair를 사용한다.
    - 이 검사는 관련 재료를 code가 고르는 의미 휴리스틱이 아니다.
    - repair가 근거 역할 외의 이미 유효한 과업 계약을 바꾸지 못하도록 필드를 잠근다.
13. direct Ollama Qwen 호출은 기본 `num_ctx=16384`를 명시한다.
    - `SONGRYEON_QWEN_NUM_CTX` 환경변수로 조정할 수 있다.
    - 모델 최대치 40,960을 기본으로 강제하지 않는다.

## 4. 정보 분류

- 경로, 범위, 원문 길이, BOM 존재, 구간 연결, parse 실행 여부: 절대정보
- 실제 Ollama `num_ctx` 설정과 answer-ready ref 목록: 절대정보/명시적 실행 정책
- L3의 사용자 목표 의미 적합성 판단: 혼합정보
- revision 종료 여부: 위 절대정보와 L3 판단을 결합하는 명시적 코드 정책
- node_3의 함수 설명과 node_4의 주장 검토: LLM 의미 판단

## 5. 금지

- 함수명/키워드 정규식으로 code가 관련 구간을 의미 선택하는 휴리스틱
- 부분 구간 parse 실패를 전체 파일 오류로 표시
- 원문 또는 trace/DataStore 기록 삭제
- read_code_file 예산 증가
- node_4 count/근거 guard 약화
- L/R 라우팅, W/R loop, scheduler, 외부 DB 변경
- 이번 발주에서 45개 BOM 파일을 일괄 재작성하는 대량 인코딩 정리

## 6. 완료 조건

1. 부분 Python 구간은 `not_run_partial_range`이며 `parse_failed`가 아니다.
2. 완전한 Python 파일은 BOM이 있어도 분석용 복사본에서 정상 parse된다.
3. 코드 원문, 경로, 범위가 하나의 node_3 LLM 재료 항목 안에 함께 존재한다.
4. 같은 코드 원문이 두 payload 채널에 중복되지 않는다.
5. revision L3가 새 코드 구간을 실제 입력으로 받고 의미 판단을 다시 실행한다.
6. 의미 일치와 CODE 원문/요구 조건 충족 시 continuation이 종료된다.
7. 실제 node_3 LLM 원문 count와 grounding block count가 일치한다.
8. 다중 코드 구간 end-to-end pytest가 추가된다.
9. `python -m compileall songryeon_core main.py` 통과.
10. `python -m pytest` 통과.
11. `python main.py smoke-test` 통과.
12. 로컬 Qwen live 시험에서 두 번째 코드 구간의 목표 함수를 node_3가 원문 근거로 설명한다.
