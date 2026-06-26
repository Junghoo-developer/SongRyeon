# Metainfo Relative/Mixed Definition Correction 2026-06-26 001

## 배경

대화 중 사용자가 상대정보와 혼합정보의 차이를 다시 명확히 지적했다.

이전 문서 일부는 혼합정보를 "출처가 연결된 상대정보"처럼 너무 넓게 설명했다.
이 표현은 SongRyeon Core의 실제 의도와 맞지 않는다.

## 정정된 기준

### 상대정보

상대정보는 특정 하나의 절대정보 record/field에 대응하거나 그것을 근거로 생성된,
시스템 안에서 의미 참거짓을 확정할 수 없는 정보다.

핵심 조건:

```text
one relative claim
-> one identifiable absolute source record or field
```

예:

```text
하나의 read_doc 원문에 대한 요약
하나의 사용자 입력에 대한 의도 해석
하나의 L3 achievement frame에 대한 의미 판단
```

### 혼합정보

혼합정보는 상대/의미 판단이 여러 절대정보 source bundle에 근거하거나,
특정 하나의 절대정보로 지정하는 것이 불가능하거나 부적절할 때 쓰는 정보다.

핵심 조건:

```text
one mixed claim
-> multiple absolute source records
or -> source bundle where one-to-one grounding is impossible or inappropriate
```

예:

```text
여러 턴 캡슐을 종합한 사용자 흐름 판단
L1 goal, search_docs 결과, read_doc 추출본을 함께 본 목표 달성 판단
여러 실행 기록을 종합한 시스템 상태 평가
```

## 중요한 차이

```text
출처가 있다는 이유만으로 혼합정보가 되는 것이 아니다.
특정 하나의 절대정보에 대응하면 상대정보다.
특정 하나로 대응시키기 어렵거나 부적절한 source bundle이면 혼합정보다.
```

두 정보 모두 의미 참거짓은 시스템이 확정하지 못한다.

차이는 출처 연결의 모양이다.

```text
상대정보: one-to-one grounding
혼합정보: source-bundle grounding
```

## 수정한 문서

- `Administrative_Reform_1/01_Maintenance_System/SCHEMA_METAINFO_POLICY_v0.md`
- `AGENTS.md`
- `Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md`
- `Administrative_Reform_1/03_Maps/03_Development_Maps/METAINFO_AUDIT_INVENTORY_v0.md`
- `<local-practice-notes>/SONGRYEON_CORE_CURRENT_ARCHITECTURE_AND_PRE_EXTENSION_AUDIT_2026_06_25.md`

## 하지 않은 것

- 코드 변경 없음.
- 스키마 필드명 변경 없음.
- runtime behavior 변경 없음.
- 과거 실행기록의 historical 표현을 모두 소급 수정하지 않음.

## 후속 감사 필요

향후 총괄이는 다음을 감사해야 한다.

```text
1. info_class=mixed로 되어 있는 기존 runtime/schema 필드 중
   사실상 one-to-one grounding인 상대정보가 있는가?

2. info_class=relative로 두어야 할 단일 출처 LLM 판단이
   관성적으로 mixed로 기록되고 있는가?

3. Node2 metainfo boundary가 direct_field와 source_bundle을
   각각 relative/mixed로 구분할 수 있는가?
```

## 한 줄 결론

상대정보와 혼합정보의 차이는 "출처 유무"가 아니라
절대정보에 대한 근거 대응 방식이다.

```text
하나에 대응하면 상대정보.
하나로 못 박기 어렵거나 부적절하면 혼합정보.
```
