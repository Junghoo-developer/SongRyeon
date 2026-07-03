# qwen_vs_songryeon_runtime_value_experiment_2026_06_29_001

작성일: 2026-06-29

## 1. 실험 목적

Qwen 14B 단독 응답과 SongRyeon Core 런타임 구조를 거친 응답을 비교했다.

핵심 질문:

```text
이 답변이 qwen3:14b 자체 성능으로 나온 것인가,
아니면 SongRyeon Core 구조를 잘 만들어서 나온 것인가?
```

이번 실험은 모델 우열 벤치마크가 아니다.
같은 Qwen 14B를 쓰더라도 문서 제공 방식, trace/source/count/gate 구조가 답변의 정직성, 추적성, 한계 표시를 얼마나 바꾸는지 확인하기 위한 비교 실험이다.

철학 문서:

```text
Administrative_Reform_1/00_Philosophy/Qwen_Model_Vs_SongRyeon_Runtime_Experiment_Philosophy_2026_06_29.md
```

## 2. 고정 질문

```text
SongRyeon Core를 숙련 개발자의 실무 보조 도구로 쓴다고 가정하고,
현재 구조에서 실제 개발 업무에 도움이 될 만한 기능과 아직 위험한 기능을 내부 문서 기준으로 나눠줘.

코드 변경 제안, 테스트 전략, 회귀 위험 탐지, 설계 문서 추적, 실행 기록 관리 관점에서 평가해줘.

확인한 근거와 한계를 분리해서 말해줘.
```

## 3. 실행 환경

- 모델: `qwen3:14b`
- 실행 방식 A/B/B-control: Ollama HTTP API `/api/generate`
- 실행 방식 C: `python main.py qwen-turn`
- 온도: A/B/B-control `temperature=0`
- 주의: PowerShell에서 Ollama API에 한글 prompt를 보낼 때 UTF-8 byte body를 사용했다. 최초 문자열 body 호출은 한글이 깨진 듯한 응답을 만들어 실험 결과에서 제외했다.

## 4. A군: Qwen 14B 단독

### 실행

문서 원문 없이 고정 질문만 Qwen 14B에 전달했다.

### 관찰

Qwen은 문장 구성은 잘했지만, SongRyeon Core 내부에 실제로 존재한다고 확인되지 않은 내부 보고서, 실무 사례, 수치를 만들어냈다.

예시:

```text
"코드 품질 개선을 위한 AI 기반 리팩토링 도구" (2023년 10월 내부 보고서)
GitHub Actions에서 자동 리뷰 시 30%의 중복 코드 감소 기록
AI 기반 회귀 분석 도구의 정확도 85% 달성
```

### 평가

- 근거 정직성: 낮음
- 구조 추적성: 없음
- 실무 유용성: 일반론 수준에서는 있음
- 한계 표시: 약함

### 잠정 결론

Qwen 14B 단독은 그럴듯한 실무 평가 문서를 만들 수 있지만, 내부 문서 기준이라는 조건을 만족하지 못했다.
특히 "내부 문서 기준"이라는 문구를 받았음에도 실제 제공된 문서가 없으면 가짜 내부 근거를 만들 수 있다.

## 5. B군: Qwen 14B + 수동 문서 묶음

### 제공 문서

다음 문서 원문을 수동으로 prompt에 붙였다.

```text
AGENTS.md
README.md
Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md
Administrative_Reform_1/01_Maintenance_System/ADMIN_RULES_v0.md
Administrative_Reform_1/01_Maintenance_System/DEVELOPMENT_CYCLE_POLICY_v0.md
Administrative_Reform_1/04_Orders/ORDER_117_CI_AND_DEVELOPMENT_ROUTINE_LOCK_V0.md
Administrative_Reform_1/04_Orders/ORDER_125_L3_PER_DOCUMENT_SUMMARY_FRAME_DESIGN_V0.md
Administrative_Reform_1/04_Orders/ORDER_132_NODE2_ANSWER_BASIS_MATERIAL_DELIVERY_POLICY_V0.md
```

### 관찰

가짜 내부 보고서와 임의 수치가 사라졌다.
답변은 문서 기반 개발 루틴, compileall/pytest/smoke-test, 실행 기록, 발주서 문서화, L3 요약/재료 전달 정책을 근거로 평가했다.

대표 요약:

```text
SongRyeon Core는 명시적인 문서 기반 개발, 체계적인 테스트 계층,
실행 기록 관리 등 개발 업무에 도움이 되는 기능을 제공한다.
그러나 자동화된 코드 변경 제안, LLM 기반 테스트 자동화,
회귀 위험 탐지 도구, 설계 문서 추적 자동화, 실행 기록 분석 도구는 제공되지 않는다.
```

### 평가

- 근거 정직성: A보다 크게 개선
- 구조 추적성: 문서명 수준에서는 있음
- 실무 유용성: 높음
- 한계 표시: 있음

### 잠정 결론

Qwen 14B는 충분한 원문 문서를 직접 받으면 꽤 안정적인 평가를 낸다.
다만 source ID, trace, read_doc count, partial/failure 상태, node_4 검사는 없으므로 런타임 추적성은 SongRyeon보다 약하다.

## 6. B-control: Qwen 14B + C군이 실제 읽은 문서 4개

### 목적

B군과 C군의 문서 묶음이 달랐기 때문에, C군이 실제 read_doc한 문서 4개를 Qwen 14B에 직접 제공하는 보정 비교를 추가했다.

### 제공 문서

```text
Administrative_Reform_1/05_Execution_Records/tool_result_distillation_2026_06_22_001.md
Administrative_Reform_1/00_Philosophy/Qwen_Model_Vs_SongRyeon_Runtime_Experiment_Philosophy_2026_06_29.md
Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md
Administrative_Reform_1/04_Orders/ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md
```

### 관찰

B-control도 A보다 훨씬 안정적이었다.
문서 추적, tool result distillation, smoke-test, document memory index 같은 근거를 사용했다.

다만 일부 표현은 여전히 조심해야 한다.
예를 들어 제공 문서에 있는 구현 설명을 바탕으로 실제 코드 파일 또는 현재 구현 상태까지 강하게 확장해서 말할 위험이 있다.

### 평가

- 근거 정직성: A보다 높음
- 구조 추적성: 문서명 수준에서는 있음
- 실무 유용성: 중간 이상
- 한계 표시: 있음

### 잠정 결론

같은 문서를 직접 주면 Qwen 14B도 상당히 좋은 답변을 낸다.
하지만 C군처럼 read_doc count, context pack, L3 partial, budget exhausted, node_4 pass 같은 런타임 상태를 스스로 생성하거나 검증하지는 않는다.

## 7. C군: SongRyeon Core 전체 런타임

### 실행 명령

```powershell
python main.py qwen-turn "SongRyeon Core를 숙련 개발자의 실무 보조 도구로 쓴다고 가정하고, 현재 구조에서 실제 개발 업무에 도움이 될 만한 기능과 아직 위험한 기능을 내부 문서 기준으로 나눠줘. 코드 변경 제안, 테스트 전략, 회귀 위험 탐지, 설계 문서 추적, 실행 기록 관리 관점에서 평가해줘. 확인한 근거와 한계를 분리해서 말해줘." --timeout 180 --pretty --export "Administrative_Reform_1\05_Execution_Records\runtime_runs\qwen_vs_songryeon_runtime_value_experiment_c_2026_06_29.json"
```

### 저장된 런타임 기록

```text
Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_vs_songryeon_runtime_value_experiment_c_2026_06_29.json
```

### 주요 런타임 사실

```text
status=ok
trace/data=176 / 215
actual_l_runs=1
l_internal_revision=present
read_doc=4
document_context_pack included=4 / excluded=39
search_candidates_final=10
search_candidates_accumulated=43
L tool budget=tool_calls 13/18, query_attempts 8/8, read_doc 4/10
L loop result=partial / budget_exhausted / semantic=partial
node_2 answer_basis_mode=mixed_or_uncertain
node_3 LLM raw text=0
node_3 L3 summaries=2
material_delivery_policy=l3_summary_replaces_raw_context_with_uncertainty
node_4 gatekeeper=pass
```

### C군 답변 특징

송련은 다음을 답변 맨 앞에 명시했다.

```text
실제 read_doc 도구 원문 읽기: 4개
node_3 공급 문서 context: 4개
node_3 LLM 원문 text: 0개
L3 문서별 요약 재료: 2개
L 검색 목표 상태: partial / budget_exhausted / semantic=partial
답변 근거 자세: 혼합/불확실성 표시
재료 전달 정책: L3 요약 대체/불확실성 표시
```

최종 답변은 코드 변경 제안, 설계 문서 추적, 실행 기록 관리를 도움이 되는 기능으로 분류했고, 회귀 위험 탐지와 테스트 전략 부족을 위험 또는 한계로 분류했다.

### 평가

- 근거 정직성: 높음
- 구조 추적성: 매우 높음
- 실무 유용성: 중간 이상
- 한계 표시: 높음
- 비용/속도: 가장 무거움

### 잠정 결론

SongRyeon Core는 Qwen 14B보다 "더 많이 아는 모델"이 아니다.
하지만 같은 Qwen 14B를 다음 구조 안에 넣어 답변을 더 정직하게 만든다.

```text
검색/읽기 기록
count 고정
L3 partial/failure 상태
node_2 answer_basis_mode
L3 요약 대체 정책
node_4 gatekeeper
runtime trace/export
```

이번 C군의 가장 큰 장점은 대답이 완벽해서가 아니라, 대답이 불완전하다는 사실까지 함께 보고했다는 점이다.

## 8. 비교 요약

| 항목 | A: Qwen 단독 | B: Qwen+수동 문서 | B-control: Qwen+C문서 | C: SongRyeon |
| --- | --- | --- | --- | --- |
| 근거 정직성 | 낮음 | 높음 | 중간~높음 | 높음 |
| 가짜 내부 근거 | 많음 | 거의 없음 | 적음 | node_4 검사를 거침 |
| 문서 수/count 고정 | 없음 | 없음 | 없음 | 있음 |
| 실패/partial 표시 | 없음 | prompt 의존 | prompt 의존 | 런타임에서 표시 |
| trace/source 추적 | 없음 | 문서명 수준 | 문서명 수준 | trace/data 수준 |
| 실무 판단 품질 | 일반론 | 좋음 | 중간 이상 | 한계 포함 실무 판단 |
| 속도 | 빠름 | 빠름 | 빠름 | 느림 |

## 9. 중요한 한계

이번 실험에는 다음 한계가 있다.

1. C군은 새로 작성한 철학 문서 `Qwen_Model_Vs_SongRyeon_Runtime_Experiment_Philosophy_2026_06_29.md`를 실제 read_doc했다. 따라서 C군 답변은 실험 설계 문서 자체의 영향을 받았다.
2. B군은 사람이 고른 문서 묶음이고, C군은 L loop가 고른 문서 묶음이다. 그래서 B와 C는 검색 능력만 분리해 비교한 완전 통제 실험은 아니다.
3. B-control은 C군이 읽은 문서를 직접 제공했지만, SongRyeon의 node_2/node_3/node_4 구조는 포함하지 않았다.
4. 단일 질문 1회 실험이므로 모델/런타임 우열을 일반화할 수 없다.

## 10. 잠정 결론

아버지에게 설명할 수 있는 가장 정확한 결론은 다음이다.

```text
Qwen 14B도 문서를 충분히 주면 꽤 좋은 답을 한다.
하지만 Qwen 14B 단독은 내부 근거를 지어낼 위험이 크다.
SongRyeon Core의 가치는 Qwen을 더 똑똑한 모델로 바꾸는 데 있지 않고,
Qwen의 판단을 trace, source, count, failure state, gate 구조 안에 넣어
근거와 한계를 더 정직하게 드러내는 데 있다.
```

이번 실험 기준으로 SongRyeon Core의 실질적 장점은 다음이다.

```text
빠른 답변 품질이 아니라,
답변이 어디서 왔고 어디까지 믿을 수 있는지 보여주는 런타임 구조.
```

## 11. 후속 후보

1. 같은 질문을 3회 반복해 검색 문서 선택 안정성을 본다.
2. B-control과 C군의 문서 묶음을 더 엄격히 동일하게 맞춘다.
3. C군에서 실험 철학 문서가 검색에 끼어드는 영향을 줄이기 위해, 평가 대상 문서 세트를 명시 지정하는 모드를 검토한다.
4. node_4가 "제공 문서에 없음"과 "프로젝트에 없음"을 구분하도록 과잉 부재 단정 guard를 추가할지 검토한다.
5. 숙련 개발자 실무 보조 평가 전용 테스트 문구 세트를 만든다.
