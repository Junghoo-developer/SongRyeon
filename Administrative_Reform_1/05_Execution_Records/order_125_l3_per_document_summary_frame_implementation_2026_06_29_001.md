# ORDER_125 L3 Per-Document Summary Frame Implementation 2026-06-29 001

## 작업 범위

- `ORDER_125`를 설계 전용 문서에서 구현 발주로 보강했다.
- L3가 실제 document extract record마다 문서별 요약 frame을 만들 수 있게 했다.
- 한 frame 안에 두 종류의 요약을 분리했다.
  - `plain_document_summary`: 문서 하나에 직접 대응하는 `relative/direct_record/one_document_to_one_summary`
  - `task_relevant_summary`: 현재 질문/L1 목표/문서 원문 source bundle에 근거한 `mixed/source_bundle/one_document_plus_task_context`
- code는 요약 문장을 생성하지 않고, LLM payload/schema 검증과 source ID 연결만 수행한다.

## 주요 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_125_L3_PER_DOCUMENT_SUMMARY_FRAME_DESIGN_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/l3_result_keeper.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/prompts/l3_per_document_summary_v0.md`
- `songryeon_core/prompts/node_3_reporter_v0.md`
- `songryeon_core/loops/l_loop.py`
- `songryeon_core/runtime/terminal_view.py`
- `tests/test_order_125_l3_per_document_summary_frame.py`

## 검증한 경계

- 담백 요약이 `mixed`로 찍히면 schema validation이 실패한다.
- 상황 요약은 source bundle data ID가 2개 이상이어야 한다.
- L3 result keeper가 실제 read document extract record에서 summary frame을 기록한다.
- node_3 brief와 LLM payload는 L3 summary material을 받되 raw internal source ID를 payload item에 노출하지 않는다.
- L3 summary frame은 원문 context를 대체하지 않고 별도 의미 재료로만 전달된다.

## 검증 명령

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

## 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: `63 passed`
- `python main.py smoke-test`: `SMOKE_TEST_OK`

## 제외한 것

- node_0 요약 기능은 만들지 않았다.
- code가 문서 의미를 요약하지 않았다.
- 여러 문서 종합 요약은 만들지 않았다.
- L3 요약으로 node_3 원문 context를 자동 대체하지 않았다.
- answer_basis_mode에 따른 원문/요약 공급량 조절 정책은 열지 않았다.
- W/R loop, scheduler, vector DB, 외부 DB, 장기기억 DB, node_5 기억 압축은 건드리지 않았다.
