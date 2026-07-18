# ORDER 268 Workspace Explicit Path And L3 Terminal Honesty 실행 기록

## 1. 실행 일자

- 2026-07-18

## 2. 작업 배경

ORDER 267 live Qwen 시험에서는 `workspace_policy.py` 원문이 결국 읽혔지만, 한글 조사
`를`이 파일명 바로 뒤에 붙으면 최초 명시 경로 감지가 실패했다. 또한 terminal은 revision
전 최초 L3 판단을 일반 `L3 달성 판단`으로 표시해 최신 상태처럼 오해하게 했고, 기존
`llm_call` 장부에 있던 L2/L3 fallback 원인은 화면에서 바로 확인하기 어려웠다.

## 3. 구현 내용

### 3.1 명시 경로 감지

- 실제 workspace 허용 파일 목록과 사용자 문장의 문자열만 대조한다.
- ASCII 경로 문자만 경로 토큰 경계로 취급해 `workspace_policy.py를`에서도 실제
  `workspace_policy.py`를 검출한다.
- 한글 조사 단어 목록이나 파일명 의미 판단은 추가하지 않았다.
- 같은 시작 위치에서 실제 파일 경로가 겹치면 더 긴 실제 경로 하나를 보존한다.

### 3.2 L3 최초/최신 표시

- revision이 없으면 기존 `L3 달성 판단`을 유지한다.
- revision이 있으면 최초 frame을 `L3 최초 달성 판단`, 가장 마지막 revision frame을
  `L3 최신 달성 판단`으로 분리한다.
- 원문 count, node_0 누적 return summary, node_3 brief의 데이터 의미는 변경하지 않았다.

### 3.3 L2/L3 fallback 진단

- 새 실패 schema를 만들지 않았다.
- 기존 `llm_call` record에서 L2/L3 실패의 node, prompt, failure type, parse status,
  validation status, 짧은 error message를 재렌더링한다.
- raw LLM text 전문과 node_3/node_4의 무관한 실패는 이 진단판에 노출하지 않는다.

## 4. 검증 결과

```text
python -m pytest tests/test_order_268_workspace_path_and_l3_terminal_honesty.py -q
-> 3 passed

python -m pytest \
  tests/test_order_260_l2_explicit_code_path_contract.py \
  tests/test_order_261_code_range_material_and_l3_recheck.py \
  tests/test_order_267_external_workspace_read_only_boundary.py \
  tests/test_order_268_workspace_path_and_l3_terminal_honesty.py -q
-> 23 passed, 1 skipped

python -m compileall songryeon_core main.py
-> passed

python -m pytest
-> 488 passed, 1 skipped, 5 deselected in 186.82s

python main.py smoke-test
-> SMOKE_TEST_OK in 192.9s

python main.py competition-demo
-> SONGRYEON_COMPETITION_DEMO_OK
-> LOCAL PASS / HONEST FALLBACK PASS / CODE GUARD PASS

git diff --check
-> passed
```

Windows 로컬 환경에서는 symbolic-link 생성 권한이 없어 ORDER 267의 해당 테스트 하나가
계속 skip됐다.

작은 직접 재현도 통과했다.

```text
input = workspace_policy.py를 실제로 읽어줘
detected_explicit_paths = [workspace_policy.py]
```

## 5. Live Qwen 재측정

ORDER 267과 같은 질문을 `songryeon_core/tools` workspace와 `--force-l`로 다시 실행했다.
설정한 600초 실행 제한을 넘겨 604초에 command timeout 되었고, CLI 최종 출력은 반환되지
않았다. 따라서 이번 재측정에서는 최종 node_4 상태와 실제 L revision 횟수를 확정할 수
없다.

이 결과는 다음 두 사실을 분리해 기록한다.

1. 명시 경로 감지, 최초/최신 L3 표시, 기존 실패 장부 렌더링은 deterministic 테스트로
   통과했다.
2. 강제 L live Qwen 경로의 순차 모델 호출 시간은 아직 제품 수준으로 안정화되지 않았다.

이번 발주에서는 호출 예산, 반복 횟수, controller 정책을 변경하지 않았다. live 속도 문제는
별도 감사와 발주가 필요한 후속 과제다.

## 6. 일부러 하지 않은 것

- L 반복 예산과 tool 예산 변경
- same-turn L reroute 횟수 변경
- 파일명 의미 기반 선택
- 한글 조사 사전 휴리스틱
- LLM 실패를 code 성공으로 변환
- node_4 guard 완화
- 외부 API, Neo4j, 심야정부 변경

## 7. 판정

ORDER 268의 좁은 정확성·표시 정직성 목표는 완료됐다. 다음 확장보다 먼저 live Qwen의
순차 호출 수와 timeout 위치를 절대정보로 측정할 진단 설계가 필요하다.
