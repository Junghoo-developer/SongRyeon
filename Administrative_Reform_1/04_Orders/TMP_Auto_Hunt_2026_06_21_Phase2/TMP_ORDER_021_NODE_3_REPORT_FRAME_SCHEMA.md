# TMP ORDER 021: Node 3 Report Frame Schema

## 목표

3 보고관의 최종 보고도 DataStore payload로 저장하고 스키마화한다.

## 배경

현재 3은 Markdown 문자열을 반환하고 trace만 남긴다.  
보고 본체가 DataStore에 없어 나중에 턴 캡슐이나 회고에서 재사용하기 어렵다.

## 범위

1. `ReportFrame` 스키마를 만든다.
2. `report_id`, `turn_id`, `source_trace_ids`, `source_data_ids`, `rendered_markdown`, `allowed_info_ids`를 둔다.
3. `record_report()`가 DataStore에 report payload를 저장한다.
4. 기존 Markdown 출력은 유지한다.

## 완료 기준

- DataStore에 `report_dry_001` payload가 저장된다.
- report payload가 boundary trace/data를 source로 가진다.

## 제외

- LLM 문체 개선.
- 사용자 맞춤 보고 스타일.
