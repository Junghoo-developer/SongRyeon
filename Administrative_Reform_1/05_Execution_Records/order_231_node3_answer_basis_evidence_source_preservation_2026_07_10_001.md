# ORDER 231 실행 기록: Node3 answer-basis evidence source preservation

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: node_2 answer-basis -> node_3 input brief source ledger

## 발생한 문제

컴퓨터 재시작 이후 Vessel R live 재확인을 다시 돌리는 과정에서 Neo4j 연결 실패가 발생했다.
이때 런타임은 실패 상태를 정직하게 보고해야 했지만, node_3 input brief 조립 중 다음 구조 실패가 발생했다.

```text
Node2EvidenceRole.source_data_id must exist in frame.source_data_ids
```

원인은 node_2 answer-basis가 만든 `evidence_roles`를 node_3 brief가 복사하면서, role의 `source_data_id`를 `Node3InputBriefFrame.source_data_ids`에 함께 넣지 않은 데 있었다.

## 변경 요약

- node_3 input brief source_data_ids에 `answer_basis_frame.source_data_ids`를 포함했다.
- node_3 input brief source_data_ids에 `answer_basis_frame.evidence_roles[].source_data_id`를 포함했다.
- Vessel R 실패/partial 상황에서도 answer-basis evidence role 좌표 누락 때문에 structure_failed가 나지 않도록 했다.
- 관련 reporting rule의 R partial 문구도 `성공으로 단정하지 않는다`에서 `요구 수준에 도달했다고 말하지 않는다`로 정리했다.

## 하지 않은 것

- code가 node_2의 evidence role 의미 판단을 새로 만들거나 바꾸지 않았다.
- Neo4j 연결 실패를 성공으로 바꾸지 않았다.
- R route/R traversal 정책은 변경하지 않았다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_231_node3_answer_basis_evidence_source_preservation.py -q
```

결과: `1 passed`.

```powershell
python -m pytest tests/test_order_121_answer_basis_and_l3_attitude.py::test_node2_answer_basis_accepts_available_evidence_source_from_boundary_sample tests/test_order_230_vessel_r_negative_success_guard.py -q
```

결과: `3 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

```powershell
git diff --check
```

통과.

## 남은 확인

Neo4j가 켜진 상태에서 동일한 Vessel R live 강제 테스트를 다시 실행해야 ORDER 230의 최종 live pass 여부까지 확인할 수 있다.

## Neo4j 상태 확인

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.env.vessel.local.ps1
python main.py vessel-readback --database neo4j
```

결과:

- env password configured: true
- `readback_status=read_failed`
- failure: `ServiceUnavailable`
- reason: `Couldn't connect to localhost:7787`

해석:

컴퓨터 재시작 이후 Neo4j Vessel 인스턴스가 아직 켜져 있지 않다.
따라서 live R 재확인은 코드 문제가 아니라 외부 로컬 DB 프로세스 상태 때문에 보류한다.
