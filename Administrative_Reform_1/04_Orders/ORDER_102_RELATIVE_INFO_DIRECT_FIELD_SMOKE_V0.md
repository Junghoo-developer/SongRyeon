# ORDER 102: Relative Info Direct-Field Smoke v0

## 상태

구현 및 검증 완료.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_102_relative_info_direct_field_smoke_2026_06_26_001.md`

## 목표

ORDER_102의 목표는 `RelativeInfoRef` 통로가 실제로 작동하는지 smoke-test로 잠그는 것이다.

ORDER_101 이후 메타정보 정의가 정정되었다.

```text
하나의 절대정보 record/field에 직접 대응하는 의미 판단: relative_info
하나로 못 박기 어렵거나 부적절한 source bundle 기반 의미 판단: mixed_info
```

ORDER_102는 이 기준이 코드에서 퇴행하지 않도록, 최소 fixture를 통해 다음을 확인한다.

```text
direct field claim -> relative_info
source bundle claim -> mixed_info 유지
relative_info -> node_3 brief -> report 저장
```

## 구현 범위

1. synthetic DataStore/TraceStore fixture를 만든다.
2. 하나의 LLM semantic field가 자기 source record 하나에만 직접 대응하도록 구성한다.
3. `build_metainfo_boundary()`가 해당 claim을 `relative_info`로 분류하는지 확인한다.
4. `mixed_info`로 잘못 들어가지 않는지 확인한다.
5. `record_node3_input_brief()`가 claim의 `info_class=relative`, `source_mode=direct_field`, `claim_alignment=one_to_one_field`를 보존하는지 확인한다.
6. fallback report와 `ReportFrame.allowed_relative_info_ids`가 relative info ID를 보존하는지 확인한다.

## 비범위

- 새 LLM 호출을 추가하지 않는다.
- 새 의미 판단을 code가 만들지 않는다.
- 라우팅, L 루프, memory packet, 장기기억 구조는 바꾸지 않는다.
- source bundle 기반 판단을 relative로 바꾸지 않는다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

추가 smoke 기대값:

```text
relative_info_direct_field=true
relative_info_brief_preserved=true
relative_info_report_preserved=true
l2_query_plan_mixed_info=true
```
