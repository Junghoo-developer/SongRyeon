# L3 Achievement Frame Execution 2026-06-21 001

## 목적

L3가 검색 결과를 보존하는 것에서 멈추지 않고, L루프의 검색/보존 운영 목표 달성 여부와 이유를 스키마로 남기게 했다.

## 변경 내용

- `L3AchievementFrame` 스키마와 검증 함수를 추가했다.
- L3 실행 시 `L3:preserved_info_frame`과 함께 `L3:achievement_frame`을 생성한다.
- L루프 결과에 `achievement_data_ids`를 추가했다.
- `Node2InputFrame.l_loop_output_ids`에 `L3:achievement_frame`이 자동 포함된다.
- smoke test가 `L3:achievement_frame`과 `reason`을 확인하게 했다.
- 기능 지도와 L3 prompt 문서를 갱신했다.

## 확인 결과

```text
python -m compileall -q songryeon_core
OK

python dry_run.py
DRY_RUN_OK
trace_count=15
data_record_count=15
movement_count=11
current_route=2

python main.py smoke-test
SMOKE_TEST_OK
trace_count=15
data_record_count=15
```

## L3AchievementFrame 확인

```text
achievement_status='achieved'
candidate_count=3
reason='search_docs 결과에서 보존 후보 3개가 L3PreservedInfoFrame에 저장되었으므로 L루프의 검색/보존 운영 목표를 achieved로 기록한다. 이 판단은 후보 내용의 사실성이나 충분성 판단이 아니다.'
evidence_data_ids=[
  'L1:goal_frame',
  'L2:query_frame',
  'tool_result:search_docs:trace_000007',
  'L3:preserved_info_frame'
]
```

## 해석

이 판단은 문서 내용이 사실인지, 사용자 의도에 충분한지까지 판단하지 않는다.

현재 v0.1은 `search_docs` 결과가 L3 보존 프레임에 후보로 저장되었는지를 기준으로 한 제한적 운영 판단이다. 나중에 LLM 판단을 붙이면 이 프레임의 `reason`, `evidence_trace_ids`, `evidence_data_ids` 구조를 그대로 쓰면서 판단 품질만 올릴 수 있다.
