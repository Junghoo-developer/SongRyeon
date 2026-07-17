# ORDER 262 L3 Trust Boundary And Count Consistency 구현 기록

## 1. 구현 일자

- 2026-07-17

## 2. 구현 목적

ORDER 261 라이브 감사에서 L3 LLM이 실제 질문과 무관한 코드 구간을 보고도
`semantic_goal_match_status=matched`를 반환할 수 있음이 확인됐다. 또한 같은 턴의
다른 L run 자료 오염, node_3 코드 원문 총예산 부재, 최신 revision 상태 누락,
node_2 repair 과업 drift, 코드 고유 파일 수와 호출 수 혼동이 함께 확인됐다.

이번 구현은 code가 의미 적합성을 대신 판단하지 않으면서도 LLM 판단이 실제로
공급된 원문 조각에 대응하도록 구조적 출처 결속과 절대정보 경계를 추가했다.

## 3. 구현 내용

1. L3 `matched` 응답에 `semantic_evidence_bindings`를 추가했다.
   - LLM은 code가 공급한 안전한 `material_ref`를 고른다.
   - LLM은 해당 preview에서 짧은 원문을 그대로 복사한다.
   - code는 ref 존재 여부와 excerpt의 정확한 부분 문자열 여부만 검증한다.
   - excerpt가 질문에 의미상 맞는지는 L3 LLM 책임으로 남겼다.
2. L3 achievement schema를 `0.3`으로 올리고 binding의 원 source data ID와
   정확한 excerpt를 보존한다.
3. L3의 explicit artifact, read_doc, read_code_file, preview 조회를 현재
   `input_data_ids`로 제한했다.
4. 최초 L3 입력에 현재 run의 다음 절대 ID를 명시적으로 연결했다.
   - 명시 문서 참조 frame
   - `read_doc`, `read_artifact`, `read_code_file` 원문 tool result
   - raw `search_docs` result는 직접 넣지 않고 기존 distillation 경계를 유지했다.
5. L3 코드 preview는 총 24,000자 안에서 최신 전체 구간을 우선 보존한다.
   - 한 구간을 추가로 중간 절단하지 않는다.
6. node_3 코드 원문도 총 24,000자 예산을 사용한다.
   - node_2 evidence role 순서를 우선한다.
   - 예산을 넘기는 구간은 원문 전체를 제외한다.
   - 제외된 구간의 파일 경로, `[start, end)` 좌표, 문자 수, 제외 이유는 남긴다.
7. `l3_result` 상태 record만 선택했다는 이유로 모든 코드 원문을 node_3에
   자동 주입하던 경로를 제거했다. 코드 원문은 정확한 `read_code_file` evidence
   ref가 선택돼야 들어간다.
8. node_0 return summary와 문서 장부는 초기/수정 L3 중 source 순서상 가장
   최신 achievement frame을 사용한다.
9. node_2 schema repair는 첫 응답의 과업 계약 필드가 개별적으로 유효하면
   오류 종류와 무관하게 잠근다.
   - `user_task_summary`
   - `fulfillment_requirements`
   - `evidence_requirement`
10. 사용자-facing count를 분리했다.
    - `read_code_file` 고유 파일 수
    - `read_code_file` 호출/구간 수

## 4. 구현 중 발견한 배선 누락

current-run 조회를 적용하자 최초 L3 입력 목록에 실제 원문 tool result ID가 없던
기존 배선 누락이 드러났다. 과거에는 L3가 DataStore 전체를 훑어 우연히 원문을
발견했기 때문에 가려져 있었다.

이를 고치면서 raw `search_docs` result까지 L3에 직접 넣자 smoke의 distillation
우선 계약이 깨졌다. 최종 구현은 원문 tool result만 직접 연결하고 search result는
distillation을 통해 공급하도록 분리했다.

## 5. 정보 분류 경계

- material ref, source data mapping, exact excerpt 존재: 절대정보
- current-run source 범위, 24,000자 예산 적용, 제외 좌표: 절대정보/명시 정책
- L3 의미 일치 상태와 이유: 여러 공급 자료에 근거한 혼합정보
- node_2 과업 계약과 evidence role: LLM 상대/혼합정보
- 최신 revision 선택과 count 표시: 절대정보

## 6. 변경 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/llm/fake.py`
- `songryeon_core/loops/l_loop.py`
- `songryeon_core/nodes/l3_result_keeper.py`
- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_2_metainfo_boundary.py`
- `songryeon_core/nodes/node_3_reporter.py`
- `songryeon_core/prompts/l3_result_keeper_v0.md`
- `songryeon_core/runtime/terminal_view.py`
- `tests/test_order_135_code_evidence_accounting.py`
- `tests/test_order_243_autonomous_r_route_reality_and_downstream_honesty.py`
- `tests/test_order_249_code_owned_absolute_facts_and_evidence_refs.py`
- `tests/test_order_261_code_range_material_and_l3_recheck.py`
- `tests/test_order_262_l3_trust_boundary_and_count_consistency.py`
- `Administrative_Reform_1/04_Orders/ORDER_262_L3_TRUST_BOUNDARY_AND_COUNT_CONSISTENCY_V0.md`

## 7. 새 회귀 테스트

- 존재하지 않는 material ref를 사용한 L3 `matched` 거절
- 원문에 없는 바꿔 쓴 excerpt를 사용한 L3 `matched` 거절
- 같은 턴의 이전 L run 코드 원문이 현재 L3 preview/count에 섞이지 않는지 확인
- node_3 코드 원문 총량 24,000자 이하 확인
- 예산 초과 코드 구간을 중간 절단하지 않고 좌표만 보존하는지 확인
- `l3_result` 상태 선택만으로 코드 원문이 자동 공급되지 않는지 확인
- 최신 revision achievement가 L return summary에 반영되는지 확인
- 일반 evidence ref 오류에서도 유효한 node_2 과업 계약이 잠기는지 확인
- 동일 파일 두 구간이 `고유 파일 1 / 호출·구간 2`로 표시되는지 확인
- L 최초 입력에 명시 artifact frame과 원문 tool result가 포함되는지 확인

## 8. 자동 검증

```text
python -m compileall songryeon_core main.py
passed

focused pytest
20 passed

python -m pytest
475 passed, 5 deselected in 134.38s

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
passed
```

## 9. 라이브 검증 상태

- 이번 구현 뒤 별도 Qwen live 턴은 실행하지 않았다.
- 확인 시점에 활성 Ollama endpoint를 찾지 못했다.
- 자동 테스트는 invalid binding, current-run 오염, 예산, revision 전달을 결정론적으로 검증한다.
- 다음 live 재시험에서는 L3 LLM call record의 `semantic_evidence_bindings`와 최종
  node_3 코드 원문 문자 수를 함께 확인해야 한다.

## 10. 남은 한계

1. exact excerpt는 L3가 실제 공급 원문을 가리켰다는 사실만 보증한다.
   그 excerpt가 사용자 질문과 의미상 맞다는 진실까지 code가 보증하지 않는다.
2. node_3의 24,000자 예산에서 제외된 구간은 DataStore에서 삭제되지 않지만,
   해당 턴의 node_3 LLM은 그 원문을 보지 못한다.
3. 문서 원문 채널 전체의 별도 문자 예산은 이번 발주 범위가 아니다.
4. Qwen의 실제 binding 형식 준수 여부는 다음 live 시험에서 확인할 대상이다.

## 11. 의도적으로 하지 않은 것

- 함수명/키워드 휴리스틱으로 관련성 판정
- code가 excerpt의 의미를 판정
- 코드 구간 중간 절단
- node_4 guard 약화
- L/R 라우팅, W/R loop, scheduler, 외부 DB 변경
