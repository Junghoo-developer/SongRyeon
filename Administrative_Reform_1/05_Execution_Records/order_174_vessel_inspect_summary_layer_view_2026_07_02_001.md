# ORDER 174 Execution Record: Vessel Inspect Summary Layer View v0

## 변경 요약

- `vessel-inspect`가 Neo4j Vessel의 `SummaryGraphNode`를 read-only로 조회하게 했다.
- 기존 `CoreEgo -> Time Axis -> Time Bundle -> Raw Capsule` tree 출력은 유지했다.
- inspect 결과 payload와 text renderer에 다음 절대정보를 추가했다.
  - `summary_count`
  - `active_summary_count`
  - `invalidated_summary_count`
  - `summary_count_by_data_kind`
  - `summary_count_by_depth`
  - `summary_sample_items`
  - `summary_lines`
- summary sample은 Neo4j node property와 `payload_json`에서 읽은 값만 표시한다.
- 새 요약 생성, 요약 품질 평가, semantic axis, R live route는 열지 않았다.

## 주요 파일

- `songryeon_core/core/graph_vessel_inspect.py`
- `songryeon_core/runtime/graph_vessel_inspect.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_163_vessel_inspect_manual_walk.py`
- `tests/test_order_174_vessel_inspect_summary_layer_view.py`
- `Administrative_Reform_1/04_Orders/ORDER_174_VESSEL_INSPECT_SUMMARY_LAYER_VIEW_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_163_vessel_inspect_manual_walk.py tests/test_order_174_vessel_inspect_summary_layer_view.py -q
```

`10 passed`.

```powershell
python main.py fast-test --profile graph
```

`FAST_TEST_OK`, graph profile `102 passed`.

## 사용 명령

Neo4j env가 설정된 PowerShell에서:

```powershell
python main.py vessel-inspect --database neo4j --format text
```

이제 출력에는 기본 시간축 tree 아래에 `Summary samples` 섹션이 함께 표시된다.
