# ORDER 277 L Original Material Attitude And Grounding Limit Consistency 실행 기록

- 실행일: 2026-07-20
- 상태: 구현 및 검증 완료
- 선행 감사: ORDER 276 사례 C

## 1. 수정 전 증상

```text
실제 read_doc 도구 원문 읽기: 0개
...
답변 한계: L 원문은 확보됐지만 L3 의미 검사가 실패했으므로 ...
```

CODE grounding block 안에서 절대 count와 한계 문장이 충돌했다.

## 2. 원인

`node_2_handoff._l_loop_result_attitude_hint()`가
`l3_semantic_execution_status=failed`만 확인하고 `original_material_count`를 확인하지 않았다.
그 결과 원문 0개와 원문 1개 이상이 같은 태도로 합쳐졌다.

## 3. 구현

- semantic failure 시 `original_material_count`를 읽는다.
- count가 1 이상이면 기존
  `l_loop_original_material_acquired_l3_semantic_failed`를 유지한다.
- count가 0이면
  `l_loop_no_original_material_l3_semantic_failed`를 기록한다.
- node_3 grounding 한계 문장은 원문 0개일 때 검색 후보와 처리 장부를 원문 근거처럼
  말하지 않는다고 표시한다.
- schema validator에 새 태도 enum 하나만 추가했다.

code는 문서 의미나 관련성을 판단하지 않고 기존 절대 count만 사용한다.

## 4. 결정론적 검증

```text
python -m compileall songryeon_core main.py
PASS

python -m pytest tests/test_order_277_l_original_material_attitude.py tests/test_order_272_l3_evidence_binding_and_failure_propagation.py tests/test_order_121_answer_basis_and_l3_attitude.py -q
13 passed

python -m pytest
510 passed, 1 skipped, 5 deselected

python main.py smoke-test
SMOKE_TEST_OK
```

Windows host의 기존 symbolic link 테스트 1개는 조건부 skip되었다.

## 5. 라이브 Qwen 재시험

입력:

```text
내부 문서에서 ORDER_275 final state index와 관련된 문서 후보 목록만 찾아줘.
이번 시험에서는 원문을 읽지 말고, 검색 후보 수와 실제 읽은 원문 수를 반드시
구분해서 짧게 말해줘.
```

조건:

```text
--force-l --max-tool-calls 1 --max-query-attempts 1 --max-read-doc-calls 1
```

결과:

- runtime: `ok`
- 후보: 12개
- 실제 원문: 0개
- node_3 공급 context: 2개
- 새 한계 문장:

```text
실제 L 원문을 확보하지 못했고 L3 의미 검사도 실패했으므로,
검색 후보와 처리 장부를 원문 근거처럼 말하지 않는다.
```

- 최종 본문: `검색 후보 수: 12, 실제 읽은 원문 수: 0`
- node_4: `pass`

공급 context 수가 2개로 변해도 실제 원문 0개와 혼동하지 않았다.

## 6. 일부러 하지 않은 것

- supplied document context 생성 정책 변경
- material delivery mode 재설계
- node_4 새 guard 추가
- L3 validator 약화
- router, 예산, 반복 횟수, R/Neo4j 변경

이번 패치는 CODE가 붙이는 한계 문장과 기존 절대 원문 count를 일치시키는 데만 한정했다.
