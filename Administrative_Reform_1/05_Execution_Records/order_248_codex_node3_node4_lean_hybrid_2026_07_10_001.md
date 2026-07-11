# ORDER 248 실행 기록

- 날짜: 2026-07-10
- 결과: Codex 5.6-sol을 node_3/node_4에만 배치한 경량 혼합 턴 성공
- 발주서: `ORDER_248_CODEX_NODE3_NODE4_LEAN_HYBRID_V0.md`

## 구현

- Qwen 담당에 L3 result keeper와 node_2 metainfo boundary를 옮겼다.
- Codex 담당은 node_3 final reporter와 node_4 gatekeeper 두 개만 남겼다.
- runtime policy를 `qwen_worker_codex_node3_node4_v1`로 기록한다.
- terminal은 Codex 모델을 `final_report_gate`로 표시한다.
- 실제 llm_call record에서 L3/node_2=Qwen, node_3/node_4=Codex를 검사한다.

## 동일 입력 비교

입력과 도구 예산은 ORDER 247 실제 시험과 같게 유지했다.

`안녕. 지금 송련이 어떤 방식으로 답하는지 한 문장으로 말해줘`

결과:

- status: ok
- route: L -> L request blocked -> 2
- Codex turns: 2 / 2 / 2
- Codex tokens: 88,186
- Codex tool activity: 0
- node_4: pass
- 실행 시간: 약 108.1초

비교:

- ORDER 247 경량화 전: 5 calls / 128,572 tokens / 120.6초
- ORDER 248 경량화 후: 2 calls / 88,186 tokens / 108.1초
- 감소: 3 calls / 40,386 tokens / 약 31.4%
- ORDER 246 all-node 206,074 tokens 대비 감소: 117,888 tokens / 약 57.2%

## 발견된 문제

- Qwen node_2 answer-basis가 schema_failed로 닫혔다.
- 오류는 `Node2EvidenceRole.source_data_id must exist in frame.source_data_ids`였다.
- code는 의미 판단을 대신하지 않고 기존 정책대로
  `mixed_or_uncertain + llm_mode_selection_failed` fallback을 기록했다.
- node_3와 node_4는 실행됐고 node_4는 pass했지만, node_2 Qwen 기준선은 정상화가 필요하다.
- Codex 호출을 2회로 줄여도 88,186 tokens이므로 node별 입력 크기 계측이 필요하다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 247~248 좁은 pytest: 4 passed
- 전체 pytest: 410 passed, 5 deselected
- `python main.py smoke-test`: SMOKE_TEST_OK
- Codex 실제 호출: 2회 확인

## 남은 위험

- 현재 Codex usage는 두 호출의 합계만 보이고 node_3/node_4별 token은 구분되지 않는다.
- node_3에는 문서 context 7개와 runtime task 14개가 전달됐다.
- node_4도 report와 brief/check material을 다시 읽으므로 문맥 중복 가능성이 크다.
- 입력 축소 전에 per-node token과 payload 크기를 먼저 계측해야 한다.
