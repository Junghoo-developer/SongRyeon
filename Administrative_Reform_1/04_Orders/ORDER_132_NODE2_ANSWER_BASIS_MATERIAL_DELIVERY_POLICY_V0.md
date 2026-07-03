# ORDER_132 Node2 Answer Basis Material Delivery Policy v0

## 목표

node_2가 고른 `answer_basis_mode`를 바탕으로, node_3가 원문 문서 context와 L3 문서별 요약을 어떤 태도로 사용할지 명시적인 material delivery policy로 전달한다.

이번 발주는 `absolute_first`가 아닌 답변 모드에서 L3 요약이 node_3 LLM 입력의 원문 text를 대체하게 한다.
단, 원문 `read_doc`/`read_artifact` record는 DataStore에 그대로 남긴다.
대체 범위는 node_3 LLM payload의 raw document text에 한정한다.

## 배경

ORDER_125에서 L3는 실제 읽은 문서마다 두 종류의 요약을 만들 수 있게 되었다.

- `plain_document_summary`: 문서 하나에 직접 대응하는 `relative` 요약
- `task_relevant_summary`: 현재 질문/L1 목표와 문서 원문 source bundle에 근거한 `mixed` 요약

이제 다음 문제는 node_3가 원문과 요약을 언제 어떻게 써야 하는지다.
특히 `answer_basis_mode=absolute_first`인 질문에서는 원문/trace/data 같은 확인 가능한 재료를 우선해야 한다.
반대로 `relative_allowed`나 `mixed_or_uncertain`에서는 문서 폭탄을 줄이기 위해 L3 요약을 node_3 LLM 입력의 주 문서 재료로 사용한다.

## 핵심 원칙

- code는 “어떤 문서 내용이 의미적으로 중요한지”를 판단하지 않는다.
- node_2 LLM이 고른 `answer_basis_mode`는 의미 판단이다.
- code는 이미 선택된 mode를 기반으로 정해진 정책 mapping만 적용한다.
- 정책 mapping은 숨은 휴리스틱이 아니라 명시적 발주/스키마/trace로 남긴다.
- L3 요약은 원문이 아니라 LLM이 만든 의미 재료다.
- 원문을 쓰는 답변과 요약을 쓰는 답변은 사용자-facing 답변에서 경계를 드러내야 한다.
- 원문 record를 삭제하거나 변형하지 않는다.
- 원문 대체는 node_3 LLM payload에서만 일어난다.
- L3 요약이 없으면 code가 요약을 만들지 않고, raw fallback 정책을 명시한다.

## 제안 schema

```text
Node3MaterialDeliveryPolicyFrame
- frame_id
- turn_id
- answer_basis_frame_id
- answer_basis_mode
- material_delivery_mode
- raw_document_policy
- l3_summary_policy
- uncertainty_policy
- policy_reason_code
- llm_raw_document_text_count
- llm_l3_summary_context_count
- raw_context_replaced_by_summary_count
- generated_by=CODE:ANSWER_BASIS_MATERIAL_POLICY
- info_class=absolute_policy_decision
- semantic_judgement_status=not_run
- source_trace_ids
- source_data_ids
```

## 정책 mapping v0

### 1. `answer_basis_mode=absolute_first`

```text
material_delivery_mode=raw_document_primary
raw_document_policy=preserve_supplied_raw_context
l3_summary_policy=auxiliary_only
uncertainty_policy=do_not_replace_raw_with_summary
policy_reason_code=absolute_first_requires_checkable_material
llm_raw_document_text_count=supplied_document_context_count
raw_context_replaced_by_summary_count=0
```

의미:

- node_3는 공급된 원문 context를 우선 근거로 사용한다.
- L3 요약은 안내/보조 재료일 뿐, 원문을 대체하지 않는다.
- 요약만 보고 원문을 확인한 것처럼 말하지 않는다.

### 2. `answer_basis_mode=relative_allowed`

```text
material_delivery_mode=l3_summary_replaces_raw_context
raw_document_policy=omit_raw_text_from_llm_payload
l3_summary_policy=replace_raw_context_with_labeled_l3_summary
uncertainty_policy=keep_summary_boundary_visible
policy_reason_code=relative_allowed_uses_l3_summary_to_reduce_context_volume
llm_raw_document_text_count=0
raw_context_replaced_by_summary_count=supplied_document_context_count
```

의미:

- node_3 LLM payload에는 원문 text를 넣지 않고 L3 요약을 넣는다.
- L3 요약을 사용할 때는 “요약 재료”라는 경계를 유지한다.
- 해석/조언/구상은 가능하지만 code fact처럼 말하지 않는다.

### 3. `answer_basis_mode=mixed_or_uncertain`

```text
material_delivery_mode=l3_summary_replaces_raw_context_with_uncertainty
raw_document_policy=omit_raw_text_from_llm_payload
l3_summary_policy=replace_raw_context_with_labeled_l3_summary_and_limits
uncertainty_policy=surface_partial_or_bundle_based_grounding
policy_reason_code=mixed_or_uncertain_uses_l3_summary_with_limit_visibility
llm_raw_document_text_count=0
raw_context_replaced_by_summary_count=supplied_document_context_count
```

의미:

- node_3는 출처 묶음, 요약 한계, 부족한 근거를 분명히 말한다.
- `task_relevant_summary`는 mixed 정보이므로 source bundle 기반 요약이라고 취급한다.
- 원문/요약/검색 목표 실패 신호를 섞어 성공처럼 말하지 않는다.

### 4. L3 요약이 없는 비-절대정보 모드

```text
material_delivery_mode=raw_document_fallback_no_l3_summary
raw_document_policy=preserve_raw_context_because_l3_summary_missing
l3_summary_policy=unavailable
uncertainty_policy=expose_summary_absence
policy_reason_code=l3_summary_unavailable_cannot_replace_raw_context
llm_raw_document_text_count=supplied_document_context_count
raw_context_replaced_by_summary_count=0
```

의미:

- code는 요약을 대신 만들지 않는다.
- L3 요약이 없기 때문에 원문 text를 node_3 LLM payload에 유지한다.
- 이 fallback은 의미 판단이 아니라 summary availability에 따른 절대 정책 분기다.

## 구현 방향

1. `Node3MaterialDeliveryPolicyFrame` schema를 추가한다.
2. node_2 handoff 또는 node_3 brief 생성 단계에서 `answer_basis_mode`를 읽어 정책 frame을 만든다.
3. policy frame은 별도 DataStore record로 저장한다.
4. `Node3InputBriefFrame`에 policy 요약 필드를 추가한다.
5. `node3_brief_llm_payload()`에 safe policy payload를 넣는다.
6. `node_3_reporter_v0.md`에 다음 경계를 추가한다.
   - absolute_first에서는 원문 context를 우선한다.
   - relative_allowed에서는 L3 요약이 원문 text payload를 대체한다.
   - mixed_or_uncertain에서는 L3 요약이 원문 text payload를 대체하되 요약/출처 묶음/불확실성을 더 분명히 드러낸다.
7. terminal view에 material delivery policy를 표시한다.

## 테스트 계획

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`

추가 pytest:

- `absolute_first`이면 `raw_document_primary` policy가 생성된다.
- `relative_allowed`이고 L3 요약이 있으면 `l3_summary_replaces_raw_context` policy가 생성된다.
- `mixed_or_uncertain`이고 L3 요약이 있으면 `l3_summary_replaces_raw_context_with_uncertainty` policy가 생성된다.
- 비-절대정보 모드인데 L3 요약이 없으면 `raw_document_fallback_no_l3_summary` policy가 생성된다.
- policy frame은 `generated_by=CODE:ANSWER_BASIS_MATERIAL_POLICY`, `semantic_judgement_status=not_run`이다.
- node_3 brief/payload가 policy를 받되 raw internal ID를 노출하지 않는다.
- L3 요약이 있어도 `absolute_first` policy에서는 원문 대체로 표시되지 않는다.
- L3 요약이 있는 비-절대정보 모드에서는 node_3 LLM payload의 `supplied_document_contexts`/`read_documents`에 원문 `text`가 들어가지 않는다.
- DataStore의 원문 document extract record는 삭제되지 않는다.

## 제외 범위

- 원문 context packing 예산을 줄이지 않는다.
- code가 문서 중요도나 관련성을 판단하지 않는다.
- node_0 요약, node_5 기억 압축, 장기기억 DB, vector DB, scheduler는 열지 않는다.
- W/R loop와 same-turn L reroute 횟수는 건드리지 않는다.
- node_4 자동 재작성 루프는 열지 않는다.

## 완료 조건

- policy frame이 DataStore에 남는다.
- node_3 brief와 payload에서 material delivery policy를 확인할 수 있다.
- 비-절대정보 모드에서 L3 요약이 있으면 node_3 LLM payload의 원문 text가 생략된다.
- 원문 DataStore record는 그대로 유지된다.
- terminal runtime view에서 policy mode를 확인할 수 있다.
- 기존 ORDER_125 L3 summary frame 동작을 깨지 않는다.
- compileall / pytest / smoke-test가 모두 통과한다.
