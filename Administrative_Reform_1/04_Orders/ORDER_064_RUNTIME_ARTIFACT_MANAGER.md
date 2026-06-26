# ORDER 064: Runtime Artifact Manager

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: trace, replay, cache, report 산출물이 늘어날 때 폴더 혼잡을 막을 필요  
**목표**: 실행 산출물을 날짜, 턴, run ID 기준으로 정리하고 manifest로 추적한다.

## 배경

프로젝트가 LLM 호출, 도구 호출, replay, graph candidate, memory index를 만들수록 산출물이 빠르게 늘어난다.  
산출물이 흩어지면 나중에 실패 원인을 재현하거나 문서화하기 어렵다.

## 범위

1. `RuntimeRunManifest` 또는 동등한 구조를 만든다.
2. 실행마다 `run_id`, `created_at`, `command`, `config`, `artifact_paths`를 기록한다.
3. trace, data record, report, replay input, replay output, cache reference를 구분한다.
4. cache는 근거 자료가 아니라 재사용 최적화 자료로 표시한다.
5. 실행 기록 문서에서 manifest 경로를 참조할 수 있게 한다.

## 원칙

1. 실행 산출물은 디버깅과 감사의 재료이다.
2. 임시 파일도 가능하면 출처와 생성 이유를 가져야 한다.
3. cache와 evidence를 섞지 않는다.

## 완료 기준

1. dry-run 실행 후 manifest 파일이 생성된다.
2. manifest에서 trace/data/report 위치를 확인할 수 있다.
3. replay가 manifest를 입력으로 받을 수 있다.
4. `python main.py smoke-test`가 통과한다.
