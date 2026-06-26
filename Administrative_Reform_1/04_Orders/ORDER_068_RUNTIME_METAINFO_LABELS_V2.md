# ORDER 068: Runtime Metainfo Labels v2

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 사용자가 런타임에서 코드 산출물과 LLM 산출물을 헷갈린 문제  
**목표**: 터미널 출력과 저장 artifact가 모든 핵심 정보의 생성자, 정보 등급, 출처, 의미판단 여부를 보여주게 한다.

## 배경

현재 런타임 출력은 `CODE:RULE_STUB`, `LLM:qwen3:14b`, `TOOL_RESULT` 같은 라벨을 일부 보여준다.  
하지만 새 메타정보 관리법은 모든 사용자 가시 정보에 최소한 `generated_by`, `info_class`, `source_data_ids`, `semantic_judgement_status`를 요구한다.

## 범위

1. `terminal_view.py`의 `[runtime]` 출력을 v2로 바꾼다.
2. 각 줄은 가능하면 다음 꼴을 따른다.

```text
- field: value
  generated_by: CODE
  info_class: absolute
  source: data_id
  semantic_judgement_status: not_run
```

3. LLM 산출물은 모델 ID와 `llm_call:*` data id를 표시한다.
4. 도구 산출물은 `TOOL_RESULT`와 tool result data id를 표시한다.
5. 문서 발췌는 `DOCUMENT_EXTRACT`와 `copied_from`을 표시한다.
6. 코드 렌더러가 만든 최종 답변은 반드시 `CODE/RENDERER | LLM_REPORTER=not_run`을 유지한다.

## 원칙

1. 보기 좋은 출력보다 헷갈리지 않는 출력이 우선이다.
2. 중간 처리 정보는 사용자가 학습할 수 있을 만큼 보이되, 과도한 raw JSON은 기본 출력에서 숨긴다.
3. 자세한 JSON은 export artifact에서 확인할 수 있어야 한다.

## 완료 기준

1. `qwen-chat --pretty`에서 Node0, Node1, L1, L2, L3, Node2, Node3의 생성자가 구분된다.
2. LLM이 실제로 호출되지 않은 노드는 `not_run`으로 보인다.
3. 도구 점수와 문서 발췌가 진실 판단처럼 출력되지 않는다.
4. smoke test가 런타임 라벨의 존재를 검사한다.

