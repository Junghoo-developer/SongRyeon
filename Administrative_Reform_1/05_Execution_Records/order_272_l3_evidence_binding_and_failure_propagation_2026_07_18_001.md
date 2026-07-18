# ORDER 272 L3 Evidence Binding And Failure Propagation 실행 기록

## 1. 실행 범위

- 발주서: `ORDER_272_L3_EVIDENCE_BINDING_SELECTION_AND_FAILURE_PROPAGATION_V0.md`
- 목표: L3의 자유 문자열 원문 복사를 공급된 조각 번호표 선택으로 교체하고,
  L3 의미 검사 실패를 L3→0→2→3 경계에 보존한다.
- 라우팅, L 반복 횟수, 도구 예산, node_4 guard는 변경하지 않았다.

## 2. 구현 결과

### 2.1 code-owned 원문 조각

- 공급 원문 미리보기를 최대 400자의 연속·비중첩 조각으로 나눈다.
- 조각 번호표는 `{material_ref}:EXCERPT_{index:04d}` 형태로 재현 가능하게 만든다.
- code는 의미상 좋은 구간을 선택하지 않는다.
- L3 LLM은 `material_ref`와 `evidence_excerpt_ref`만 선택한다.
- code는 선택된 번호표가 실제 공급 목록에 있고 해당 material에 속하는지 검증한 뒤,
  정확한 원문 문자열을 `L3SemanticEvidenceBinding`에 복원한다.
- 같은 material의 서로 다른 조각 여러 개는 허용하고 같은 조각 번호표 중복은 거부한다.

### 2.2 실패 상태 보존

다음 절대정보를 L3 achievement, L return summary, node_3 brief/payload에 추가했다.

- `l3/llm_semantic_execution_status`: `not_run | ran | failed`
- `l3/llm_semantic_failure_type`
- `l3/llm_semantic_failure_reason`

원문 요구량을 충족하고 code 운영 판정은 달성했지만 L3 의미 검사가 실패한 경우:

- `failure_level=l3_semantic_failed`
- `recommended_next_route_for_node1=2`
- `l_loop_result_attitude_hint=l_loop_original_material_acquired_l3_semantic_failed`

으로 기록한다. 실제 원문은 버리지 않으며 자동 L 재검색은 열지 않는다.

### 2.3 prompt와 화면

- L3 prompt에서 자유 문자열 `evidence_excerpt` 생성을 제거했다.
- 허용 enum에 없는 `failed` 지시를 `missing`으로 정정했다.
- node_3 prompt에 “원문은 사용할 수 있지만 L3 의미 적합성이 확인됐다고 말하지 않는다”는
  실패 경계를 추가했다.
- terminal에 L3 의미 검사 실행 상태·실패 종류·이유를 표시한다.

## 3. live Qwen 검증

입력:

```text
내부 문서 ORDER_270을 직접 읽고, direct Ollama timeout 정책이 무엇을 바꿨는지 읽은 원문 기준으로 짧게 설명해줘.
```

명령:

```powershell
python main.py qwen-turn "..." --force-l --timeout 180 --pretty
```

### 3.1 첫 실행

- 전체 상태: `ok`
- 실제 원문: 1개
- L3 call: `schema_failed`
- 실패 이유: `L3 semantic evidence material refs must be unique`
- downstream: `l3_semantic_failed`와 원문 확보 상태가 함께 보존됨
- node_4: pass

Qwen은 같은 문서의 서로 다른 조각 여러 개를 골랐다. 기존의 material당 binding 1개
제한에는 안전 근거가 없으므로, 서로 다른 excerpt ref는 허용하고 같은 excerpt ref
중복만 거부하도록 수정했다.

### 3.2 수정 후 재실행

- 전체 상태: `ok`
- 전체 턴 시간: 80,640ms
- 실제 원문: 1개
- L3 call: `failure=none`
- L3 결과: `semantic=matched`
- 실행 상태: `semantic_execution=ran`
- 실패 종류: `semantic_failure=none`
- L return: `task=achieved / failure=none`
- node_4: pass

따라서 live Qwen이 원문을 다시 타이핑하지 않고 공급된 번호표를 선택하는 경로가 실제로
통과했다.

## 4. 검증 결과

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest -q
# 503 passed, 1 skipped, 5 deselected

python main.py smoke-test
# SMOKE_TEST_OK
```

skip 1개는 기존 Windows 호스트의 symbolic link 생성 불가 조건이다.

ORDER 272 표적 테스트 5개는 다음을 검증한다.

1. 고정 조각의 재현성, 400자 상한, 원문 무손실 재결합
2. 번호표 선택 뒤 code의 정확한 원문 복원
3. 한 material의 서로 다른 조각 여러 개 허용
4. schema failure의 L3→0→2→3 전파
5. prompt의 번호표 계약과 enum 정합성

## 5. 남은 위험

- 400자 고정 분할은 공개된 기계적 정책이지만 의미 경계와 일치하지 않을 수 있다.
- 조각 수가 커지면 L3 JSON 입력 오버헤드가 늘 수 있다.
- L3 retry는 열지 않았으므로 다른 schema 실패는 정직하게 실패 상태로 진행한다.
- 조각 크기·분할 방식 최적화는 별도 live 자료와 결재 없이 변경하지 않는다.

## 6. 학습 포인트

1. LLM에게 원문을 정확히 복사시키는 대신 code가 만든 ID를 선택하게 하면 형식 실패를
   줄이면서 의미 선택 권한은 LLM에 남길 수 있다.
2. “원문을 확보했다”와 “L3가 그 원문의 의미 적합성을 확인했다”는 서로 다른 상태다.
3. validator는 엄격해야 하지만, 안전 근거가 없는 제한까지 엄격하게 만들면 정상적인
   다중 근거 선택을 막는다.
