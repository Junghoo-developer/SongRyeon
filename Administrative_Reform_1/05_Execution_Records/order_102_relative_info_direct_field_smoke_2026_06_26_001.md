# ORDER 102 Relative Info Direct-Field Smoke 2026-06-26 001

## 상태

구현 및 검증 완료.

## 목적

`RelativeInfoRef` 통로가 실제로 작동하는지 smoke-test로 고정했다.

이 작업은 새 의미 판단 기능을 여는 것이 아니라, ORDER_101 이후 갈라놓은 `relative_info` / `mixed_info` 경계가 퇴행하지 않도록 막는 작업이다.

## 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_102_RELATIVE_INFO_DIRECT_FIELD_SMOKE_V0.md`
- `Administrative_Reform_1/04_Orders/ORDER_101_RECENT_RAW_CONVERSATION_CAPSULE_ALIGNMENT_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/runtime/smoke_test.py`

## 핵심 구현

`songryeon_core/runtime/smoke_test.py`에 `_run_relative_info_direct_field_smoke()`를 추가했다.

이 smoke는 synthetic `L3AchievementFrame` payload를 만든다.

조건:

```text
schema_name=L3AchievementFrame
achievement_generation_source=LLM:relative-info-smoke
llm_semantic_judgement_status=ran
source_data_ids는 자기 record 하나뿐
field_path=reason
```

기대:

```text
boundary.relative_info count = 1
boundary.mixed_info count = 0
relative_info.source_mode = direct_field
relative_info.claim_alignment = one_to_one_field
node_3 brief allowed_claim.info_class = relative
ReportFrame.allowed_relative_info_ids에 relative info id 저장
```

기존 L2 query planner smoke는 유지한다.
따라서 source bundle 기반 `l2_query_candidate_purpose`는 계속 `mixed_info`로 남는다.

추가로 ORDER_101 문서에 있던 미래 후보명 `ORDER_102_RECENT_CAPSULE_LLM_SELECTOR_V0`는 번호 충돌을 피하기 위해 번호 미정 후속 후보로 정리했다.
selector 자체는 폐기하지 않았고, 별도 결재와 후속 번호가 필요한 후보로 남겼다.

## 비범위

- LLM 호출을 새로 추가하지 않았다.
- code가 의미 판단을 대신 만들지 않았다.
- 라우팅, L loop, memory packet, 장기기억 구조를 바꾸지 않았다.
- source bundle 판단을 relative로 바꾸지 않았다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python main.py smoke-test
```

통과. `SMOKE_TEST_OK`.

추가 확인값:

```text
relative_info_direct_field=true
relative_info_brief_preserved=true
relative_info_report_preserved=true
l2_query_plan_mixed_info=true
```

## 남은 위험

이번 smoke는 synthetic direct-field fixture다.
실사용 LLM 경로에서 단일 문서 요약이나 단일 record 해석이 열리면, 그 실제 경로에 대한 추가 smoke가 필요하다.
