# ORDER 048: Tool Result Distillation

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "능률 도구 사용"  
**목표**: 도구 결과 전체를 매번 LLM에게 다시 먹이지 않고, L루프가 읽기 좋은 작은 근거 프레임으로 압축한다.

## 배경

`search_docs` 결과와 `read_doc` 원문은 커질 수 있다.  
LLM에게 매번 원문 전체를 넣으면 느리고 비싸며, Qwen 14B 로컬 환경에서는 context 압박도 커진다.

## 범위

1. `ToolResultDistillationFrame`을 만든다.
2. search result의 doc_id, chunk_id, score, text_preview를 보존한다.
3. read_doc 결과는 필요한 구간만 발췌하거나 chunk 단위로 요약한다.
4. distillation에는 원본 tool_result data_id를 반드시 붙인다.
5. L2/L3/controller는 원본 payload 대신 distillation frame을 우선 읽는다.

## 원칙

1. distillation은 원문을 대체하지 않는다. 항상 원본 data_id로 되돌아갈 수 있어야 한다.
2. 요약이나 선별은 혼합 정보이며 근거 ID를 가져야 한다.
3. 절대정보 필드와 혼합 정보 필드를 분리한다.

## 완료 기준

1. search_docs 결과마다 distillation frame이 만들어진다.
2. L3 preserved candidates가 distillation source를 참조할 수 있다.
3. LLM 입력 payload 크기가 기존 tool_result 전체보다 작아진다.
4. 원본 tool_result를 따라가 replay할 수 있다.
