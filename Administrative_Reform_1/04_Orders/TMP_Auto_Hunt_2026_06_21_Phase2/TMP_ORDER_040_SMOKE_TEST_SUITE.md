# TMP ORDER 040: Smoke Test Suite

## 목표

현재 MVP 구조가 깨졌는지 빠르게 확인하는 최소 테스트 묶음을 만든다.

## 배경

스키마와 trace/data 흐름이 늘어나면서 작은 변경도 런타임을 깨뜨릴 수 있다.

## 범위

1. 표준 라이브러리 `unittest` 또는 간단한 스크립트 기반 smoke test를 만든다.
2. dry_run이 통과하는지 확인한다.
3. data_record_count, 핵심 data_id, L3 source_data_ids를 검증한다.
4. search_docs가 최소 1개 결과를 반환하는지 확인한다.

## 완료 기준

- 한 명령으로 smoke test가 통과한다.
- 실패 시 어떤 구조가 깨졌는지 메시지가 나온다.

## 제외

- 대규모 테스트 프레임워크.
- 모델 품질 평가.
