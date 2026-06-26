# ORDER 098 상태 기준선 정리 기록

## 상태

문서와 현재 구현 현실을 맞췄다.

## 배경

ORDER_098은 원래 run-aware terminal/final renderer와 runtime count consistency를 위한 발주서였다.
이후 실제 구현은 count 분리, L reroute 표시 분리, 최신 run 우선 표시, node_3 grounding block code 고정 생성까지 진행됐다.

다만 ORDER_098 문서만 보면 "node_3 identity boundary"까지 완전히 code guard로 닫힌 것처럼 오해할 수 있었다.

## 정리 내용

- `ORDER_098_RUN_AWARE_TERMINAL_FINAL_RENDERER_V0.md`의 상태 설명을 보강했다.
- ORDER_098 완료 범위를 화면 정직성, count 정합성, run-aware renderer, code-generated grounding block 기준으로 명시했다.
- node_3 identity leak을 node_4가 직접 반려하는 code guard는 후속 과제라고 분리했다.
- node_1 router fallback 정직성은 새 발주서 `ORDER_099_ROUTER_FALLBACK_HONESTY_MVP_V0.md`로 분리했다.
- `04_Orders/README.md`의 정식 발주서 범위를 ORDER_099까지 갱신했다.

## 기준 구현 상태

현재 안정된 것으로 보는 항목:

- `reportable_document_count`, `raw_document_extract_record_count`, `empty_document_extract_record_count` 분리.
- L internal continuation과 top-level same-turn L reroute 표시 분리.
- terminal/final renderer의 최신 run-scoped record 우선 표시.
- node_3 grounding count block을 code가 `Node3InputBriefFrame`의 절대 count로 고정 생성.
- node_4 grounding count guard 유지.
- node_4 needs_revision/failed 시 safe blocking answer 출력.
- same-turn L reroute 기본 1회, 실험 2회, 3회차 차단.

후속 잠금 과제:

- node_1 router fallback 정직성.
- node_4 remand return target 구조화.
- node_3 user-facing identity leak의 node_4 code guard.

## 검증

이번 작업은 문서 상태 정리와 발주서 작성만 수행했다.
코드 변경은 하지 않았다.

이전 기준 검증:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

최근 기준 수동 확인:

```powershell
python main.py qwen-turn "최대한 많은 내부 문서를 아무거나 골라서 읽고 이를 총합해서 지금 너가 무엇인지 스스로 추측해봐" --timeout 120 --pretty
```

확인된 핵심값:

- `node_4 gatekeeper=pass`
- `읽은 문서: 2개`
- `검색 후보 문서: 12개`
- `현재 턴 실행 순서 자료: 13개`

남은 위험:

- node_3 본문이 자신을 `node_3` 같은 내부 노드로 정의하는 표현은 아직 prompt/brief 경계만 있고, node_4 code guard는 없다.
