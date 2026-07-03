# ORDER_137_SOURCE_CODE_CONTEXT_SUMMARY_COVERAGE_GUARD_V0

## 1. 목표

`read_code_file`로 source/config 파일 원문을 읽는 경로는 열렸지만, node_3가 최종 답변에서 파일 안의 공개 함수나 상수 같은 핵심 구조를 빠뜨릴 수 있다.

이번 MVP는 code가 읽힌 source-code 원문에서 문법적으로 확인 가능한 outline을 만들고, node_3에게 coverage checklist로 전달한다.

## 2. 배경

최근 live 테스트에서 `songryeon_core/tools/code_tools.py`는 정상적으로 직접 읽혔다.

- L scope: `code_only`
- budget partition: `document=0 / code=18`
- 실제 도구: `read_code_file`
- L3: `achieved`, `goal_match_status=matched`
- node_3 brief: `actual_read_code_file=1`, `source_code_contexts=1`

하지만 최종 답변은 `read_code_file` 중심으로 설명했고, 같은 파일의 공개 기능인 `list_code_files`, `search_code` 등을 충분히 다루지 못했다.

이는 검색/읽기 실패가 아니라, 읽힌 코드 원문의 구조를 node_3가 답변 coverage 기준으로 안정적으로 보지 못한 문제다.

## 3. 구현 범위

1. `read_code_file` 결과 원문에서 source-code outline을 생성한다.
   - Python 파일은 `ast.parse`로 top-level 구조를 읽는다.
   - 함수, async 함수, class, 대문자 상수 assign을 기록한다.
   - 이름, 종류, line number, public/private 여부, docstring 존재 여부만 기록한다.

2. outline은 절대정보로 취급한다.
   - code는 함수의 의미를 요약하지 않는다.
   - code는 이름과 문법 위치만 기록한다.
   - 의미 설명은 node_3 LLM이 source text와 outline을 보고 작성한다.

3. `Node3InputBriefFrame`에 source-code outline 목록을 추가한다.
   - `source_code_outlines`
   - outline count는 grounding block과 runtime view에 표시한다.

4. node_3 prompt를 보강한다.
   - source-code 파일의 기능을 설명할 때 outline의 public top-level function 목록을 coverage checklist로 사용한다.
   - 함수 이름만 보고 동작을 단정하지 말고, supplied source text를 근거로 설명한다.
   - outline은 코드 문법 장부이며 의미 요약이 아님을 명시한다.

5. node_4 guard, L routing, tool budget, W/R loop, scheduler, 외부 DB는 건드리지 않는다.

## 4. 금지

- 질문 문자열 기반 휴리스틱 추가 금지.
- code가 함수 의미를 대신 요약하는 것 금지.
- read_code_file을 read_doc으로 섞어 세는 것 금지.
- L loop 예산 확대 금지.
- W loop, R loop, scheduler, 외부 DB, 장기기억 DB 변경 금지.

## 5. 완료 조건

1. `python -m compileall songryeon_core main.py`
2. `python -m pytest`
3. `python main.py smoke-test`
4. 추가 테스트:
   - `code_tools.py`를 `read_code_file`로 읽으면 source-code outline이 생성된다.
   - outline public function 목록에 `list_code_files`, `search_code`, `read_code_file`이 포함된다.
   - outline 상수 목록에 `DEFAULT_CODE_FILE_EXTENSIONS`, `DEFAULT_IGNORED_DIR_NAMES`가 포함된다.
   - node_3 LLM payload에 raw internal data id 없이 outline coverage checklist가 들어간다.
   - grounding block과 runtime view에 source-code outline count가 표시된다.
