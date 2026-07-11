# ORDER 236 실행 기록

- 날짜: 2026-07-10
- 결과: 구현 및 회귀 검증 완료
- 변경: R3 LLM input에서 R1/R2 full provenance를 compact view로 바꾸고 선택 재료를 앞에 배치했다.
- 절대 기록: full source trace/data ID는 DataStore/TraceStore에 유지했다.
- 측정: 마지막 R3 input은 약 68,889자에서 약 9,751자로 줄었다.
- 검증: ORDER 236 pytest와 quick-smoke 통과.
- 남은 실패: RawSource를 `low_summary`로 오인하는 문제는 ORDER 238~239로 이어서 처리했다.
