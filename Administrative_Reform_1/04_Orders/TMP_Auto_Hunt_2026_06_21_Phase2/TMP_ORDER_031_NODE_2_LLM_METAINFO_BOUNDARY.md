# TMP ORDER 031: Node 2 LLM Metainfo Boundary

## 목표

2 메타정보 경계관이 DataStore payload를 읽고 상대/혼합 정보 후보를 만들 수 있게 한다.

## 배경

2는 환각 방지의 핵심이다.  
LLM을 붙이더라도 절대정보 출처 없이 판단을 만들면 안 된다.

## 범위

1. `RelativeInfoClaim`, `MixedInfoClaim` 스키마를 만든다.
2. 모든 claim에 source_trace_ids/source_data_ids를 강제한다.
3. LLM 출력은 스키마 검증 후 boundary v0.3에 저장한다.
4. 실패 시 절대정보-only boundary로 fallback한다.

## 완료 기준

- 출처 없는 claim은 검증 실패한다.
- 3 보고관은 2가 허용한 claim만 볼 수 있다.

## 제외

- 고급 신뢰도 점수.
- 사실 검증 외부 검색.
