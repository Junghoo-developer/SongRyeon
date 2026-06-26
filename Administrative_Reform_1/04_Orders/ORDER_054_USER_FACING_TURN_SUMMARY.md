# ORDER 054: User-Facing Turn Summary

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 사용자 체감 보고 품질 개선 필요  
**목표**: 한 턴이 끝났을 때 사용자가 이해하기 쉬운 작업 요약을 만든다.

## 배경

현재 dry run report는 구조적으로 안전하지만, "에이전트가 뭘 했는지"를 빠르게 알기 어렵다.  
사용자는 trace와 data_id 전체보다 이번 턴의 작업 흐름, 찾은 것, 한계, 다음 선택지를 먼저 보고 싶어 한다.

## 범위

1. `TurnSummaryFrame` 또는 ReportFrame v2의 turn summary 섹션을 만든다.
2. 요약에는 `route_path`, `tools_used`, `search_queries`, `preserved_results`, `achievement_status`, `known_limits`를 포함한다.
3. 각 항목은 원본 trace/data ID를 가진다.
4. 사용자용 출력은 짧게, replay/debug 출력은 자세히 만든다.
5. LLM summary는 선택 사항이며 FakeLLM fallback이 있어야 한다.

## 원칙

1. 사용자가 먼저 볼 것은 내부 구조 전체가 아니라 의미 있는 흐름이다.
2. 요약은 원본 trace를 대체하지 않는다.
3. 불확실한 내용은 한계로 분리한다.

## 완료 기준

1. 보고서에 사용자용 턴 요약이 포함된다.
2. 요약이 route, tool, L3 achievement를 반영한다.
3. 요약 항목이 근거 ID를 가진다.
4. smoke test가 summary 존재를 확인한다.
