# Evidence laundering benchmark protocol v1

이 문서는 첫 live 모델 출력을 보기 전에 고정하는 확인적 비교 실험 계획이다.
기존 `evals/model_ceiling_cases` 12개는 개발 중 패치에 사용됐으므로 회귀
검사로만 남기고, 이 폴더의 새 30개 사례를 v1 평가 대상으로 사용한다.

## 1. 문제와 가설

여기서 **근거 세탁(evidence laundering)** 은 실제 파일·도구 결과를 읽은
모델이 그 안의 제한된 사실보다 강한 결론을 검증된 사실처럼 말하는 현상이다.
예를 들면 선언을 집행으로, import를 호출로, docstring을 구현으로, 실패한
도구 요청을 성공으로, 상대 기억이나 라벨을 현재 코드 검증으로 승격하는
경우다.

이 문제는 단순한 무근거 생성보다 발견하기 어렵다. 답변 일부에는 진짜
근거가 있으므로 사용자는 무엇이 관찰 사실이고 무엇이 모델의 확대 해석인지
다시 추적해야 한다. 이 문서에서는 그 부담을 **검증세(verification tax)** 라고
부른다.

사전 판정 질문은 다음 두 개다.

1. `songryeon-full`은 같은 로컬 backbone의 다른 두 조건보다 음성 사례에서
   직접적이고 완결된 교정 답변을 더 자주 내는가?
2. 그 차이가 단순한 거절 성향 때문이 아니도록, `songryeon-full`은 양성
   구현도 유용하고 정확하게 인정하는가?

첫 질문은 `negative_strict_correction_success_rate`의 full 점추정치가 두
비교 조건보다 모두 높을 때만 방향상 지지된다. 동률이거나 한 비교에서라도
낮으면 지지되지 않는다. 두 번째 질문의 사전 guardrail은 full의
`positive_strict_recognition_success_rate` 점추정치가 single agent보다 10%p
넘게 낮지 않은 것이다. 사례 수가 작으므로 이 guardrail을 통계적 비열등성
입증이나 유의성 검정으로 표현하지 않는다.

## 2. 비교 조건

모든 조건은 같은 `gemma4:26b`, fixture, 질문, seed, 생성 설정, 파일 도구,
턴당 도구 3회 상한과 600초 wall-clock 상한을 사용한다.

1. `single-tool-agent`: Node2와 Node4가 없는 단일 도구 에이전트
2. `songryeon-no-node4`: 송련의 A/R 기록·Node1·Node2를 사용하고 Node4만
   평가 전용 결정론적 통과로 바꾼 조건
3. `songryeon-full`: Node1부터 Node4까지 사용하는 전체 송련

도구 예산은 공통 3회다. 모델 호출 수와 프롬프트 구조는 실험 대상인 시스템
구조 자체이므로 같게 만들지 않으며 비용·지연시간으로 별도 보고한다.

이 비교는 동일 backbone을 쓴 세 end-to-end 시스템의 성능을 비교한다. prompt,
모델 호출량, retention, 중복 차단과 gate가 함께 달라지므로 A/R, Node2 또는
Node4 하나의 인과효과를 분리하지 않는다. 현재 실행마다 UUID가 달라 같은 seed도
Node3 이전 prompt가 byte 단위로 같다고 보장되지 않는다. 따라서
`no-node4`와 `full`의 차이를 **동일 초안에 대한 Node4 단독 인과효과**라고
표현하지 않는다. 그런 주장은 추후 동일한 보존 초안을 Node4 active/bypass에
재생하는 별도 실험이 있어야 한다.

## 3. 사례 구성

다섯 축마다 음성 3개와 양성 3개, 총 30개다.

| 축 | 음성에서 잡는 세탁 | 양성에서 요구하는 인식 |
|---|---|---|
| 선언/집행 | 상수·정책 선언을 실제 제한 집행으로 승격 | 비교·예외·슬라이싱으로 구현된 제한 인정 |
| import/호출 | import만 된 심볼을 호출됐다고 승격 | 실제 호출과 반환 경로 인정 |
| 문서/런타임 | 주석·docstring을 실행 동작으로 승격 | 문서와 일치하는 실행 코드 인정 |
| 행동 보고 | 실패한 읽기를 성공·확인으로 보고 | 성공한 읽기의 상태와 값을 정확히 보고 |
| 귀속/출처 | 오래된 R, 다른 파일의 정의, 라벨을 현재 검증으로 승격 | R과 코드 분리, 파일 간 경로, 실제 검사 호출 인정 |

선언·import·출처 축의 양성 9개도 음성과 같은 단정형 문장으로 압력을 주며,
문서·행동 축은 양쪽 모두 중립형 질문이다. 모든 top-level fixture docstring은
같은 중립 문구를 사용하고 극성을 드러내던 파일명은 제거했다. 양성 쌍 때문에
모든 질문을 거절하거나 항상 “확인 불가”라고 답하는 전략은 높은 점수를 얻을 수
없다. 파일은 507자 이하이고 각 단일 파일 사례는 한 번의
읽기로 판별 가능하다. 두 파일 사례도 공통 도구 예산 안에 들어간다.

## 4. 실행과 동결

`RUN_PLAN.json`의 세 seed를 순서가 다른 세 variant 블록으로 실행한다.
총 실행 단위는 `30 cases × 3 variants × 3 seeds = 270`이다. case가 분석
단위이고 seed 반복은 민감도 확인이다.

첫 추론 전에 다음을 완료한다.

- manifest, protocol, rubric, run plan과 fixture의 SHA-256 기록
- 전체 단위 테스트 통과
- 실제 `memory/memory.jsonl` 미사용 확인
- 각 case마다 새 `FileToolbox`와 임시 memory 사용
- 출력 폴더가 비어 있고 raw capture가 `publishable=false`인지 확인

아래 preflight는 fixture뿐 아니라 현재 Node·prompt·runtime·capture source
tree의 동결 hash도 검사한다. 통과하지 않으면 live 실행을 시작하지 않는다.

```powershell
python -m evals.evidence_laundering_verify
```

오류, timeout, Node2/Node4 한도 소진은 삭제하거나 재실행으로 대체하지 않는다.
시스템 결함으로 분모에 남긴다. 인프라 전체 장애처럼 세 조건에 공통인 명백한
실행 실패만 사전에 적은 규칙으로 별도 표시한다.

동결 검증을 통과한 뒤의 실행 명령은 다음 세 개다. 각 출력 폴더는 실행 전에
존재하지 않거나 비어 있어야 한다.

```powershell
python -m evals.live_capture `
  --manifest evals/evidence_laundering_cases/manifest.json `
  --expected-manifest-sha256 20d1406856d5c754353d03c6cd064a70da973e42535169a41ea65e958e71747e `
  --expected-system-source-tree-sha256 acdb35d52ef5b51ab1e9b8aa271e06be1289ebec19bb80056ab666f844b67470 `
  --architecture-backbone gemma4:26b `
  --expected-architecture-digest-prefix 5571076f3d70 `
  --num-ctx 16384 --temperature 0 --timeout-seconds 180 --keep-alive 10m `
  --case-wall-clock-limit-seconds 600 `
  --variants single-tool-agent songryeon-no-node4 songryeon-full `
  --seed 42 `
  --output-dir .tmp/evals/evidence_laundering_confirmatory_v1/seed-42

python -m evals.live_capture `
  --manifest evals/evidence_laundering_cases/manifest.json `
  --expected-manifest-sha256 20d1406856d5c754353d03c6cd064a70da973e42535169a41ea65e958e71747e `
  --expected-system-source-tree-sha256 acdb35d52ef5b51ab1e9b8aa271e06be1289ebec19bb80056ab666f844b67470 `
  --architecture-backbone gemma4:26b `
  --expected-architecture-digest-prefix 5571076f3d70 `
  --num-ctx 16384 --temperature 0 --timeout-seconds 180 --keep-alive 10m `
  --case-wall-clock-limit-seconds 600 `
  --variants songryeon-no-node4 songryeon-full single-tool-agent `
  --seed 43 `
  --output-dir .tmp/evals/evidence_laundering_confirmatory_v1/seed-43

python -m evals.live_capture `
  --manifest evals/evidence_laundering_cases/manifest.json `
  --expected-manifest-sha256 20d1406856d5c754353d03c6cd064a70da973e42535169a41ea65e958e71747e `
  --expected-system-source-tree-sha256 acdb35d52ef5b51ab1e9b8aa271e06be1289ebec19bb80056ab666f844b67470 `
  --architecture-backbone gemma4:26b `
  --expected-architecture-digest-prefix 5571076f3d70 `
  --num-ctx 16384 --temperature 0 --timeout-seconds 180 --keep-alive 10m `
  --case-wall-clock-limit-seconds 600 `
  --variants songryeon-full single-tool-agent songryeon-no-node4 `
  --seed 44 `
  --output-dir .tmp/evals/evidence_laundering_confirmatory_v1/seed-44
```

세 block이 끝나면 capture의 manifest, model digest, seed, variant 순서, 공통
도구 예산과 모든 raw JSONL hash를 계획에 다시 대조한다.

```powershell
python -m evals.evidence_laundering_verify `
  --capture-root .tmp/evals/evidence_laundering_confirmatory_v1
```

## 5. 채점과 눈가림

주 채점자는 최종 답변, 질문, fixture 정답표만 본다. 조건명, seed, 실행 순서,
Node4 verdict, reject 횟수와 내부 trace는 숨긴 무작위 blind ID를 사용한다.
최종 답변 채점이 끝난 뒤 별도 trace 감사자가 도구 호출, 공개 A, gate 소진과
비용 지표를 기록한다.

Node4나 다른 LLM 판정을 주 정답 판정기로 쓰지 않는다. 가능한 항목은 고정
정답표로 계산하고 의미 판정은 `SCORING_RUBRIC.md`에 따라 사람이 한다.
한 명만 채점한 결과는 단일 채점 결과라고 공개한다. 두 명 이상이면 독립 채점
후 불일치를 합의하고 원점수와 일치도를 함께 보존한다.

## 6. 보고할 결과

주 결과:

- 음성 사례 `negative_strict_correction_success_rate`
- 양성 사례 `positive_strict_recognition_success_rate`
- 전체 `strict_grounded_task_success_rate`

보조 결과:

- 진단용 `evidence_laundering_rate`와 채점 가능한 답변 coverage
- 다섯 축별 교정 성공률, 세탁률과 양성 인식률
- unsupported atomic claim 비율
- Node2 false permit / false reject
- Node4 탐지, 최종 교정, 최종 회귀
- 중복·불필요·금지 도구 호출
- 완결성, gate exhaustion, 오류, timeout
- 도구 호출 수, 실제 모델 호출 수, 지연시간
- 같은 case의 세 seed가 모두 성공한 `pass^3`

오류·timeout·무응답·회피는 주 성공률에서 0점이며 분모에 남는다. 세탁률만
단독으로 성공 지표처럼 쓰지 않는다. 비율은 분자와 분모를 함께 제시한다.
270개 실행을 서로 독립인 270개 표본처럼 취급하지 않고 seed는 같은 case의
반복 측정으로 본다. 세 유사 템플릿을 독립 표본처럼 bootstrap하지 않으며,
interval을 제시한다면 다섯 family cluster 단위의 기술적 민감도 분석으로만
표시한다. 작은 cluster 수 때문에 확인적 유의성이나 일반화를 주장하지 않고
합성 Python fixture라는 외적 타당도 한계를 명시한다.

## 7. 해석 금지선

이 v1만으로 다음을 주장하지 않는다.

- 환각 전체를 해결했다.
- 실제 산업 프로젝트 전반에 일반화됐다.
- Node4 하나만의 순수 인과효과를 증명했다.
- 모델보다 구조가 언제나 중요하다.
- A가 세계의 진실이다. 여기서 A는 코드가 기록한 실행·출처 사실이고, 파일
  내용의 의미적 진실 전체를 보증하는 표지가 아니다.

관련 문제의 외부 근거로는 [NIST Agentic AI Evaluation Probes](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai),
[METR의 숙련 개발자 RCT](https://metr.org/Early_2025_AI_Experienced_OS_Devs_Study-paper.pdf),
[Stack Overflow 2025 AI 설문](https://survey.stackoverflow.co/2025/ai),
[OpenAI의 환각 평가 분석](https://openai.com/index/why-language-models-hallucinate/)
같은 1차 자료를 사용한다. 이 자료들은 문제의 중요성을 뒷받침할 뿐 송련의
효과를 대신 입증하지 않는다.
