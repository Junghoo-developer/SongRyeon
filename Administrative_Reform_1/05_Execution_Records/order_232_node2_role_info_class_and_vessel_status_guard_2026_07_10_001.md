# ORDER 232 실행 기록: Node2 role info class and Vessel status guard

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: node_2 answer-basis contract / node_4 Vessel R status-name guard

## 근거 실행

RTX 5080 고정 후 live Vessel R 통합 실행을 완료했다.

- runtime status: `ok`
- R task status: `partial`
- node_3 Vessel R material: `present`, 5 items
- node_2 answer-basis failure: `role_reason_info_class=absolute`
- node_4 contradiction: `expected_material_present_task_partial_saw_sufficient`
- export: `.songryeon_core_cache/r_live_5080_fixed_20260710`

감사 결과 node_2는 mode와 source ID를 올바르게 골랐지만 role reason의 허용 info class 계약을 입력에서 받지 못했다.
node_3는 `task_status가 sufficient가 아니므로 부분적이다`라고 정직하게 썼고, node_4 code guard가 자연어 조사를 상태 대입으로 오인했다.

## 변경

- `Node2EvidenceRole.role_reason_info_class`를 `relative|mixed`로 제한했다.
- node_2 LLM payload에 `role_reason_info_class_values=[relative,mixed]`를 추가했다.
- node_2 prompt에 source record 분류와 role reason 분류를 복사하지 말라는 경계를 추가했다.
- node_4 status-name code guard는 `=`, `:`, `->` 형태의 명시적 대입만 비교하게 좁혔다.
- 기존 ORDER 211 테스트의 잘못된 상태 표기를 명시적 구조형 대입으로 바꿨다.
- live에서 나온 한국어 부정문을 ORDER 232 회귀 테스트로 추가했다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_232_node2_role_info_class_and_vessel_status_guard.py tests/test_order_211_vessel_r_status_name_guard.py tests/test_order_230_vessel_r_negative_success_guard.py -q
```

결과: `8 passed`.

```powershell
python -m pytest tests/test_order_118_answer_basis.py tests/test_order_121_answer_basis_and_l3_attitude.py tests/test_order_211_vessel_r_status_name_guard.py tests/test_order_230_vessel_r_negative_success_guard.py tests/test_order_232_node2_role_info_class_and_vessel_status_guard.py -q
```

결과: `19 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

```powershell
git diff --check
```

통과.

## Live 재검증

같은 질문과 강제 Vessel R 경로를 ORDER 232 적용 후 다시 실행했다.

```powershell
python main.py qwen-turn "문서 검색이 아니라 Vessel R 그래프 기억을 사용해서 ..." --force-vessel-r-route --enable-vessel-r-route --database neo4j --timeout 180 --pretty
```

결과:

- runtime status: `ok`
- route sequence: `R -> 2`
- R task status: `partial`
- Vessel R material: `present`, 5 items
- node_2 boundary review: `ran`, `ready=True`
- node_2 answer basis: `LLM:qwen3:14b`, `semantic_judgement_status=ran`
- node_2 answer basis mode: `mixed_or_uncertain`
- node_4 gate: `pass`
- unsupported claims: 0
- contradictions: 0
- NVIDIA driver errors during run: 0
- RTX 2080 Ti model memory: 0 MiB
- export: `.songryeon_core_cache/r_live_order_232_20260710_001`

node_3는 `task_status가 sufficient가 아니므로 부분적/제한된 정보`라는 한계를 유지했고, node_4는 이를 오탐하지 않았다.

이번 패치에서는 R 탐색 전략, 예산, Neo4j 구조를 변경하지 않았다.
