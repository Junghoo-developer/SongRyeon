# ORDER 268: Workspace Explicit Path And L3 Terminal Honesty v0

## 1. 배경

ORDER 267 live Qwen 시험에서 `workspace_policy.py` 원문 1개는 실제로 읽혀 node_3까지
전달됐지만 다음 문제가 확인됐다.

1. `workspace_policy.py를`처럼 한글 조사가 붙으면 명시 경로 감지 결과가 빈 목록이 됐다.
2. terminal의 `L3 달성 판단`은 revision 전 최초 frame을 최종처럼 표시했다.
3. L2/L3 fallback의 정확한 parse/schema/adapter 실패 정보는 기존 `llm_call` record에
   있지만 terminal에서 바로 확인하기 어려웠다.

## 2. 목표

새 의미 휴리스틱이나 예산 조정 없이, 사용자가 명시한 실제 workspace 경로를 자연스러운
한글 문장에서도 code가 정확히 복사하고 L3 최초/최신 상태와 기존 LLM 실패 절대정보를
terminal에서 정직하게 구분한다.

## 3. 구현 범위

### 3.1 명시 경로 문법

- code는 workspace에 실제 존재하는 허용 파일 목록과 사용자 문장의 문자열만 대조한다.
- 지원 확장자 뒤의 한글 조사는 ASCII path token의 일부로 보지 않는다.
- 의미나 중요도를 판단하지 않는다.
- 같은 위치에서 여러 실제 후보가 겹치면 더 긴 실제 경로를 우선해 짧은 prefix 오인을
  막는다.

### 3.2 L3 terminal 표시

- revision이 없으면 기존 `L3 달성 판단`을 유지한다.
- revision이 있으면 최초 frame은 `L3 최초 달성 판단`으로 표시한다.
- 최신 revision frame은 `L3 최신 달성 판단`으로 상세 표시한다.
- node_0 누적 return summary는 계속 별도 절대정보로 유지한다.

### 3.3 fallback 진단

- 새 실패 schema를 만들지 않는다.
- 기존 `llm_call` record의 다음 절대정보를 terminal에 표시한다.
  - node_id
  - prompt_ref
  - failure_type
  - parse_status
  - validation_status
  - error_message
- L2/L3 실패만 우선 표시하고 raw LLM text 전문은 노출하지 않는다.

## 4. 금지

- L 반복 예산, tool 예산, same-turn reroute 변경
- 파일명 의미 기반 선택
- 한글 조사 단어 목록 휴리스틱
- L3/LLM 실패를 code 성공으로 바꾸기
- node_4 guard 약화
- 외부 API, Neo4j, 심야정부 변경

## 5. 완료 조건

1. `workspace_policy.py를`에서 실제 `workspace_policy.py` 경로가 검출된다.
2. 띄어쓰기와 인용부호가 있는 기존 입력도 유지된다.
3. 겹치는 실제 경로는 짧은 prefix를 중복 선택하지 않는다.
4. revision이 있으면 terminal이 최초와 최신 L3를 구분한다.
5. L2/L3 parse/schema/adapter 실패가 기존 `llm_call` 절대정보 기준으로 표시된다.
6. 원문 count, node_0 return summary, node_3 brief 의미는 바꾸지 않는다.
7. 표적 pytest, 전체 pytest, smoke-test를 통과한다.

## 6. 후속 경계

ORDER 268 뒤 동일 live 질문을 다시 실행해 직행 여부와 시간을 재측정한다. 그 결과를 본
뒤에만 controller-step 예산 또는 순차 LLM 호출 최적화를 별도 발주로 논의한다.
