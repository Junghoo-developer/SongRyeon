# Metainfo Relative/Mixed Schema Split 2026-06-26 001

## 상태

구현 및 검증 완료.

`metainfo_classification_code_audit_2026_06_26_001.md`에서 확인한 핵심 문제 중, 코드가 상대정보와 혼합정보를 같은 `mixed_info` 통로로만 운반하던 문제를 1차로 정리했다.

## 변경 목표

정정된 메타정보 기준을 코드 구조에 반영한다.

```text
하나의 절대정보 record/field에 직접 대응하는 의미 판단: relative_info.
하나로 못 박기 어렵거나 부적절한 source bundle 기반 의미 판단: mixed_info.
```

## 핵심 변경

- `songryeon_core/core/schemas.py`
  - `RelativeInfoRef` 추가.
  - `MixedInfoRef`에 `source_mode="source_bundle"`, `claim_alignment="multi_source_bundle"` 추가.
  - `RelativeInfoRef`에 `source_mode="direct_field"`, `claim_alignment="one_to_one_field"` 추가.
  - `MetainfoBoundary.relative_info`를 실제 `list[RelativeInfoRef]` 통로로 변경.
  - `ReportFrame.allowed_relative_info_ids` 추가.
  - `Node3BriefClaim`에 `info_class`, `source_mode`, `claim_alignment` 추가.

- `songryeon_core/nodes/node_2_metainfo_boundary.py`
  - `_build_mixed_info_refs`를 `_build_semantic_info_refs`로 확장.
  - direct field claim은 `RelativeInfoRef`, source bundle claim은 `MixedInfoRef`로 분리할 수 있게 했다.
  - L2 query candidate purpose는 여러 근거 묶음에서 생성되는 planner 판단이므로 `mixed_info`로 유지했다.
  - node_2 review LLM payload에 `relative_info_count`, `relative_info`를 추가했다.

- `songryeon_core/nodes/node_2_handoff.py`
  - node_3 input brief의 `allowed_claims`가 relative/mixed 구분을 보존한다.

- `songryeon_core/nodes/node_3_reporter.py`
  - fallback report에 `Relative Info`와 `Mixed Info`를 별도 섹션으로 출력한다.
  - report 기록 시 `allowed_relative_info_ids`를 저장한다.

- `songryeon_core/runtime/terminal_view.py`
  - node_3 input brief를 `mixed_brief_from_absolute_sources`로 표시하던 라벨을 `code_assembled_brief_from_absolute_sources`로 정정했다.

- `songryeon_core/runtime/smoke_test.py`
  - boundary/report smoke가 `relative_info`와 `mixed_info`를 모두 검사한다.
  - `source_mode`, `claim_alignment`, source trace/data evidence를 검사한다.

## 일부러 하지 않은 것

- 새 의미 판단을 만들지 않았다.
- LLM 판단을 code가 대신 생성하지 않았다.
- W loop, R loop, scheduler, 외부 DB, 장기기억 DB는 건드리지 않았다.
- same-turn L reroute 횟수는 건드리지 않았다.
- 현재 기본 dry run에 억지로 relative_info를 만들지 않았다.

## 검증 결과

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python main.py smoke-test
```

통과. `SMOKE_TEST_OK`.

주요 smoke 확인값:

```text
relative_info_count=0
mixed_info_count=0
semantic_info_count=0
l2_query_plan_mixed_info=true
```

기본 dry run에는 현재 node_2가 보고 가능한 LLM semantic claim을 만들지 않아 relative/mixed count가 0이다.
별도 L2 query planner smoke에서는 `l2_query_candidate_purpose`가 source bundle 기반 `mixed_info`로 유지되는 것을 확인했다.

## 남은 위험

- 현재 `RelativeInfoRef` 통로는 준비되었지만, 기본 경로에서 실제 relative claim을 생성하는 대표 사례는 아직 없다.
- 앞으로 단일 문서 요약, 단일 data record 해석 같은 기능이 열리면 `RelativeInfoRef` smoke를 별도로 추가해야 한다.
- 스키마 주석 일부는 생성자/status에 따라 정보 등급이 달라지는 필드가 있어 "분류 경계"로 남겨 두었다. 후속 감사에서 field별 생성자 정책이 더 세분화되면 추가 정리가 필요하다.
