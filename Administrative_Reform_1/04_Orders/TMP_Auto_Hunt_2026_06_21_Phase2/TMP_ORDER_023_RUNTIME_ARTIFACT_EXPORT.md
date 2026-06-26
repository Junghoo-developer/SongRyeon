# TMP ORDER 023: Runtime Artifact Export

## 목표

드라이런 한 턴의 trace, data, state, report를 파일로 내보낸다.

## 배경

현재 실행 결과는 콘솔에만 보인다.  
나중에 0.state, 회고, 디버깅, 테스트에 쓰려면 실행 산출물이 파일로 남아야 한다.

## 범위

1. `runs/` 또는 `Administrative_Reform_1/05_Execution_Records/runtime_runs/` 위치를 정한다.
2. `trace.json`, `data.json`, `report.md`, `summary.json`을 저장한다.
3. 기존 `TraceStore.save_json`, `DataStore.save_json`을 사용한다.
4. dry_run에서 옵션으로 export를 켤 수 있게 한다.

## 완료 기준

- `python dry_run.py` 기본 실행은 유지된다.
- export 실행 시 JSON/Markdown 산출물이 생긴다.
- 저장 경로가 실행 기록에 남는다.

## 제외

- DB 저장.
- UI 뷰어.
