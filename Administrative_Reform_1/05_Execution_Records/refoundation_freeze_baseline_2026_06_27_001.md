# ORDER_113 재정립 freeze 기준선 감사 실행 기록

## 목적

SongRyeon Core의 기능 확장을 잠시 멈추고, 리팩터링 전 기준선을 고정했다.

ORDER_112는 명시 artifact 우선순위와 whole-document packing을 추가하는 기능 발주서지만, 현재는 `schemas.py`와 `smoke_test.py`가 이미 비대해졌고 pytest/tests 기준선이 없다. 따라서 ORDER_112 구현은 ORDER_113~117 재정립 이후로 보류한다.

이번 기록은 기능 구현이 아니다.

## freeze 범위

ORDER_113 기준선 감사 동안 다음 작업은 하지 않았다.

- ORDER_112 구현
- 새 memory 기능
- 새 L loop 정책
- W/R loop
- scheduler
- 외부 DB/vector DB
- schema field 대량 추가

허용한 작업은 기준선 측정과 실행 기록 작성뿐이다.

## 기준선 명령 결과

검증 명령:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

결과:

```text
compileall passed
smoke-test passed: SMOKE_TEST_OK
```

첫 `smoke-test` 실행은 도구 제한 124초에서 timeout이 났다. 같은 명령을 300초 제한으로 재실행했고, 127.4초 뒤 `SMOKE_TEST_OK`로 완료됐다.

주요 smoke 결과:

```text
status=SMOKE_TEST_OK
trace_count=49
data_record_count=76
task_frame_count=14
task_result_count=14
document_memory_index_docs=259
document_memory_index_has_order=True
live_trace_line_count=13
recent_memory_relevance_candidate_count=8
memory_selection_node3_selected_count=1
selected_recent_memory_context_copied=1
node1_recent_memory_router_visibility_route=2
top_doc=05_Execution_Records/l3_achievement_frame_2026_06_21_001.md
```

## 파일 비대도

가장 큰 Python 파일 상위 20개:

```text
Lines  Path
5492   .\songryeon_core\runtime\smoke_test.py
3539   .\songryeon_core\core\schemas.py
1550   .\songryeon_core\loops\l_loop.py
1371   .\songryeon_core\runtime\terminal_view.py
1224   .\songryeon_core\runtime\dry_run.py
1085   .\songryeon_core\nodes\node_2_handoff.py
1046   .\songryeon_core\nodes\l3_result_keeper.py
949    .\songryeon_core\nodes\node_0_memory_supplier.py
643    .\songryeon_core\nodes\node_2_metainfo_boundary.py
509    .\tmp\pdfs\generate_l3_reading_pdf.py
509    .\songryeon_core\nodes\l2_query_setter.py
502    .\songryeon_core\nodes\memory_relevance_selector.py
452    .\songryeon_core\core\registry.py
395    .\songryeon_core\nodes\node_1_router.py
367    .\songryeon_core\loops\l_loop_revision_tool_attempt.py
366    .\songryeon_core\llm\fake.py
352    .\main.py
305    .\songryeon_core\nodes\node_4_gatekeeper.py
292    .\songryeon_core\nodes\l2_revision_input.py
283    .\songryeon_core\runtime\user_turn.py
```

핵심 수치:

```text
songryeon_core/core/schemas.py: 3539 lines
songryeon_core/runtime/smoke_test.py: 5492 lines
```

## pytest/tests 기준선

확인 결과:

```text
tests folder: NOT_FOUND
pyproject.toml: NOT_FOUND
pytest.ini: NOT_FOUND
tox.ini: NOT_FOUND
setup.cfg: NOT_FOUND
```

현재 pytest 기반 테스트 발견/실행 체계는 없다.

## CI 기준선

현재 GitHub Actions 파일:

```text
.github/workflows/smoke-test.yml
```

현재 CI 명령:

```yaml
- name: Compile Python files
  run: python -m compileall songryeon_core main.py

- name: Run smoke tests
  run: python main.py smoke-test
```

pytest 설치 또는 `python -m pytest` 실행 단계는 없다.

## ORDER_112 상태

`ORDER_112_EXPLICIT_ARTIFACT_PRIORITY_AND_WHOLE_DOCUMENT_PACKING_V0.md`의 상태는 다음과 같다.

```text
발주서 초안.
사용자 승인 후 구현한다.
```

이번 대화에서 사용자가 ORDER_112 기능 구현을 ORDER_113~117 재정립 이후로 보류하라고 명시했다. 따라서 ORDER_112는 현재 구현 보류 상태로 기록한다.

## 다음 발주 순서

권장 순서:

```text
1. ORDER_114: Pytest Baseline Harness v0
2. ORDER_115: Schema Module Split With Compatibility Layer v0
3. ORDER_116: Smoke Test Decomposition To Pytest v0
4. ORDER_117: CI And Development Routine Lock v0
```

ORDER_116은 ORDER_114 완료 후, 가능하면 ORDER_115 일부 완료 뒤 진행한다. ORDER_117은 pytest와 smoke-test를 개발 루틴/CI에 잠그는 마무리 발주로 둔다.

## ORDER_112 재개 조건

ORDER_112 같은 기능 구현은 최소한 다음 조건을 만족한 뒤 재개한다.

- pytest baseline 존재
- schema split 계획 또는 최소 1차 완료
- smoke decomposition 시작
- CI가 pytest와 smoke-test를 모두 실행
- 기능 구현과 재정립 리팩터링을 같은 변경 묶음에 섞지 않음

## 결론

현재 기준선은 compileall과 smoke-test 기준으로 통과한다.

하지만 `schemas.py` 3539줄, `smoke_test.py` 5492줄, pytest/tests 부재, CI의 compileall/smoke-test 단일 구조 때문에 새 기능 추가보다 테스트/구조 재정립을 먼저 해야 한다.

다음 권장 발주는 ORDER_114다.
