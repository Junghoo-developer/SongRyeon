# ORDER_141_CORE_EGO_GUIDE_WORKER_LLM_HINTS_V0_CANDIDATE

## Candidate Status

이 문서는 후보 발주서다.

ORDER_139와 ORDER_140의 결과를 확인하기 전에는 구현하지 않는다.

## 1. 목표

RLoopGraphGuidePacket의 code-generated graph snapshot 위에 LLM 기반 traversal hint를 추가하는 후보 발주다.

이번 후보의 핵심:

```text
code는 graph count/entry/depth/source를 쓴다.
LLM은 그 snapshot을 보고 R루프가 어디서 시작하면 좋을지 hint를 쓴다.
hint는 mixed 정보로 source bundle과 함께 기록한다.
```

## 2. 선행 조건

- ORDER_139 완료.
- RLoopGraphGuidePacket이 code-generated absolute/status 정보로 생성되어야 한다.
- ORDER_140에서 R루프 frame/state machine이 감사되어야 한다.

## 3. LLM이 쓸 수 있는 것

LLM Guide Worker 후보 출력:

```text
recommended_entry_node_ids
avoid_entry_node_ids
traversal_strategy_hint
reason_summary
risk_notes
expected_depth_policy
source_graph_node_ids
source_data_ids
generated_by
info_class = mixed
semantic_judgement_status = ran
```

이 정보는 최종 진실이 아니다.

R루프가 graph DB를 탐색할 때 참고하는 안내판이다.

## 4. code가 쓸 수 있는 것

code는 다음만 쓴다.

- graph node count
- edge count
- node kind count
- depth range
- source leaf count range
- available entry node id 목록
- schema validation status
- LLM call trace/data id

code는 추천 이유를 쓰지 않는다.

## 5. 검증 경계

LLM hint는 다음 검증을 통과해야 한다.

- 추천 entry id가 available entry node 목록 안에 있다.
- source graph node id가 실제 snapshot 안에 있다.
- hint가 빈 문자열이 아니다.
- generated_by가 LLM임을 드러낸다.
- info_class는 mixed다.
- semantic_judgement_status는 ran 또는 failed다.

실패 시 code fallback으로 추천을 만들지 않는다.

실패 상태만 기록한다.

## 6. 금지

- R route를 열지 않는다.
- R1/R2/R3를 실제 실행하지 않는다.
- LLM hint를 절대정보처럼 표시하지 않는다.
- code fallback으로 "이 노드가 좋아 보인다"는 의미 판단을 만들지 않는다.
- node_3 최종 답변에 바로 사용하지 않는다.
- 의미축 graph hierarchy를 만들지 않는다.

## 7. 테스트 후보

1. LLM이 허용된 entry node id를 추천하면 pass.
2. 허용 목록 밖 entry node id를 추천하면 schema 실패.
3. LLM 실패 시 recommendation은 비고, status만 failed로 남는다.
4. hint는 `info_class=mixed`와 source bundle을 가진다.
5. RLoopGraphGuidePacket의 code-generated count와 LLM hint가 분리된다.

## 8. 완료 조건 후보

아직 구현 금지.

승격 시:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

