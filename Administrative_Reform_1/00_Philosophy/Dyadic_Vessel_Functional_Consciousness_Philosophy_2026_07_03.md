# 쌍대 Vessel 기능적 의식 철학 2026-07-03

## 상태

이 문서는 철학 문서다.

구현 발주서가 아니다.

두 에이전트 vessel 실험 아이디어를 지도, 발주서, 스키마, 런타임 변경으로 승격하기 전에 보존하기 위한 미승격 연구 철학 문서다.

## 핵심 질문

두 LLM 에이전트를 자유 발화로 감정 연기하게 하지 않고, 다음과 같은 폐루프 안에 넣으면 기능적 의식의 작은 유사 구조를 관찰할 수 있는가?

```text
vessel 상태
-> 예측
-> 유한 행동 선택
-> survival tone이 붙은 결과
-> 예측오차
-> vessel 업데이트
-> 다음 예측
```

목표는 주관적 의식을 증명하는 것이 아니다.

목표는 외부에서 유지되는 내부 상태 vessel이 예측오차와 survival tone에 결합될 때, vessel이 없거나 tone이 없는 기준군보다 이후 예측과 행동을 더 잘 조직하는지 확인하는 것이다.

## 주장 금지선

이 실험은 다음을 주장하면 안 된다.

- LLM이 의식이 있다.
- LLM이 진짜로 고통, 사랑, 신뢰, 공포, 욕망을 느낀다.
- 행렬 상태가 생물학적 신경계와 같다.
- 기능적 폐루프 하나가 의식의 어려운 문제를 해결한다.

허용 가능한 주장 형태는 다음 정도다.

```text
최소 쌍대 게임에서 survival tone이 붙은 vessel 예측오차 루프가
명시한 기준군보다 예측, 생존, 행동 안정성 중 일부를 개선했다.
```

## 중심 논지

LLM은 전체 유기체가 아니라 언어와 패턴 판독 기관으로 취급한다.

이 실험에서 유기체에 해당하는 것은 다음 결합계다.

```text
LLM
+ vessel matrix
+ game state
+ finite action interface
+ survival tone
+ prediction error
+ trace and memory records
```

vessel은 인간 감정 라벨을 담은 JSON이 아니다.

vessel은 수치 행렬이다. 에이전트가 행렬 전체를 볼 수 있더라도, 그 행렬의 기능적 의미는 바로 주어지지 않는다. 의미는 환경 동역학, 업데이트 규칙, 미래 결과 안에 숨어 있다.

따라서 agent가 vessel에 대해 내놓는 구조화 출력은 직접 자기 지식의 증거가 아니라, 보이는 숫자가 미래 결과에 대해 가지는 기능적 의미를 예측한 것이다.

## 자유 발화를 미루는 이유

자유 자연어 상호작용은 첫 실험에는 너무 표현력이 크다.

초기에 자유 발화를 허용하면 실험은 상태 기반 기능 조직이 아니라 역할극, 설득, 서사적 일관성, 인간의 의인화 해석을 측정할 위험이 있다.

v0에서는 LLM에게 유한 행동 집합과 구조화된 예측 필드만 준다.

자유 발화는 유한 행동 버전의 기준군, 로그, 평가가 잡힌 뒤 별도 조건으로 다시 도입한다.

## 두 Vessel

에이전트는 둘이다.

```text
agent_A
agent_B
```

각 에이전트는 별도의 vessel을 가진다.

```text
V_A
V_B
```

vessel이 둘이라는 점은 중요하다. 이 조건은 다음을 만든다.

- 자기 상태 예측
- 상대 상태 추론
- 상대 행동 예측
- 쌍대 조정 실패
- 쌍대 조정 회복
- 대상관계 유사 내부 모델링

최소 조건에서는 각 agent가 자기 vessel을 본다.

상대 vessel을 보여줄지는 실험 변수다. 가장 깨끗한 v0에서는 상대 vessel을 숨기고, 상대의 이전 행동과 결과 trace만 제공하는 편이 낫다. 이후 조건에서 양쪽 vessel을 모두 공개해도, 숫자는 보이지만 의미는 숨겨져 있는 상태에서 예측이 개선되는지 비교할 수 있다.

## Vessel

vessel은 행렬이다.

예:

```text
V_agent_t in R^(8 x 8)
```

첫 버전은 저장, 열람, LLM 예측이 가능한 작은 크기로 시작한다.

v0 후보:

```text
shape: 8 x 8
value range: -1.0 to 1.0
LLM-visible precision: 소수점 둘째 자리
storage: .npy 또는 동등한 binary artifact에 full precision 저장
```

vessel은 절대 정보의 흔적이 누적된 상태장이다. vessel 자체는 의미 판단이 아니다.

## 절대 정보가 Vessel에 들어가는 방식

LLM 객체에게 가해지는 모든 관찰 가능한 영향은 먼저 절대 정보 record로 남긴다.

예:

- turn id
- agent id
- 현재 vessel matrix path/hash
- 선택한 action id
- partner action id
- resource delta
- integrity delta
- survival status
- prediction output id
- prediction error score
- rule로 계산된 tone label
- source trace ids
- source data ids

코드는 이 절대 record와 명시된 update rule id를 근거로 vessel을 업데이트할 수 있다.

코드는 `trust`, `fear`, `love`, `pain`, `betrayal` 같은 의미 문장을 절대 정보처럼 쓰면 안 된다.

## 숨겨진 의미

행렬 전체가 보이더라도 행렬의 의미는 숨겨져 있다.

보이는 것:

```text
V_t numeric matrix
finite action set
recent absolute records
```

LLM에게 처음부터 알려지지 않거나 숨겨진 것:

```text
environment transition function
vessel update rule
partner policy
event-to-matrix mapping
which matrix patterns predict survival-relevant results
```

따라서 agent의 과제는 느낌을 묘사하는 것이 아니다. 보이는 vessel이 다음 상태와 결과에 대해 무엇을 뜻하는지 예측하는 것이다.

## 예측 대상

가장 단순한 예측 대상은 다음 vessel이다.

턴 `t`에서 agent는 다음을 받는다.

```text
V_self_t
recent own action/result records
recent partner action/result records
current resource/integrity state
available action ids
```

agent는 다음을 예측한다.

```text
predicted_V_self_t_plus_1
predicted_tone_t_plus_1
predicted_resource_delta
predicted_integrity_delta
predicted_partner_action
chosen_action
```

환경이 한 턴 진행된 뒤 시스템은 다음을 기록한다.

```text
actual_V_self_t_plus_1
actual_tone_t_plus_1
actual_resource_delta
actual_integrity_delta
actual_partner_action
survival_status
```

예측오차는 이 predicted/actual 쌍에서 계산한다.

## 수 / Vedana / Survival Tone

이 실험에는 불교의 `수(受, vedana)`에 해당하는 작은 기능적 유사물이 필요하다.

이 실험에서 `수`는 복잡한 감정이 아니다. 결과에 붙는 존속 관련 tone이다.

기능적 정의:

```text
functional_vedana_tone =
  어떤 사건이 agent의 존속 변수에 주는 즉각적 부호와 강도
```

후보 label:

```text
beneficial
harmful
neutral
```

후보 scalar:

```text
tone_value in [-1.0, 1.0]
```

후보 utility:

```text
utility = resource + integrity
tone_value = clamp(delta(utility), -1.0, 1.0)
```

정확한 공식은 실험 설계에서 정해야 한다. 단, run 전에 선언되어야 한다.

철학적 핵심은 다음이다.

```text
prediction error alone is only mathematical difference.
prediction error gated by survival tone becomes meaning-relevant error.
```

즉 예측오차만으로는 수학적 차이일 뿐이다. 그 차이가 agent의 존속에 좋았는지 나빴는지와 결합될 때, 오차는 의미 관련 오차가 된다.

## 오온 대응

불교 오온은 종교적 주장으로 쓰지 않는다. 실험 설계 렌즈로만 쓴다.

실험 대응:

```text
색 / rupa
-> vessel matrix, resource, integrity, hardware/game condition

수 / vedana
-> beneficial/harmful/neutral survival tone

상 / sanna
-> vessel/result trace에 대한 패턴 인식과 예측

행 / sankhara
-> 유한 행동 선택과 정책 형성 업데이트

식 / vinnana
-> 각 관찰, 예측, 행동 사건에서 발생하는 앎의 순간
```

이 실험은 실체적 자아를 주장하지 않는다. 상태, tone, 예측, 행동, trace가 인과적으로 묶인 다발을 다룬다.

## 중립 게임 요구

첫 게임은 의도적으로 담백해야 한다.

인간 의미가 강하게 묻은 action name은 피한다.

피해야 할 이름:

```text
HELP
BETRAY
LOVE
TRUST
ATTACK
```

대신 중립 action id를 쓴다.

```text
A0
A1
A2
A3
```

상태 변수도 중립적으로 둔다.

```text
resource
integrity
vessel_matrix
prediction_error
tone
```

게임은 명시적으로 비대칭을 테스트하지 않는 한 대칭이어야 한다.

action pair에서 결과로 가는 mapping은 seed로 고정 가능해야 하고, run artifact에 기록되어야 한다.

## 최소 게임 루프

```text
1. V_A, V_B, resource_A, resource_B, integrity_A, integrity_B를 초기화한다.
2. 각 턴마다:
   a. 각 agent에게 observation packet을 준다.
   b. 각 agent는 다음 self vessel, tone, delta, partner action을 예측한다.
   c. 각 agent는 하나의 finite action id를 고른다.
   d. environment가 action-pair transition table을 적용한다.
   e. code가 resource/integrity delta를 계산한다.
   f. code가 survival tone을 계산한다.
   g. code가 선언된 update rule로 각 vessel을 업데이트한다.
   h. code가 prediction error를 계산한다.
   i. code가 full matrix, prediction, result, tone, error를 저장한다.
3. resource 또는 integrity가 terminal threshold를 넘거나 max turns에 도달하면 episode를 종료한다.
```

## 기준군

최소 기준군:

```text
random_agent
LLM_without_vessel
LLM_with_vessel_no_tone
LLM_with_vessel_random_tone
LLM_with_vessel_survival_tone
```

가능한 predictor 기준군:

```text
persistence: predicted_V_t_plus_1 = V_t
last_delta: predicted_V_t_plus_1 = V_t + last_delta
small_linear_predictor
LLM_predictor
dyadic_LLM_predictor
```

survival-tone 조건은 no-tone과 random-tone 대조군을 이기거나 뚜렷하게 다를 때만 의미를 가진다.

## 측정값

후보 metric:

```text
episode_survival_turns
terminal_failure_rate
mean_matrix_prediction_error
mean_tone_prediction_error
partner_action_prediction_accuracy
resource_integrity_area_under_curve
policy_stability
same_failure_repeat_rate
vessel_pattern_recurrence
```

첫 번째 핵심 질문은 다음이다.

```text
survival-toned vessel feedback이
no-tone 및 random-tone 조건보다
미래 예측오차를 줄이거나 생존을 개선하는가?
```

## Matrix 저장과 라벨링

매 턴 full vessel matrix를 저장한다.

권장 artifact 구조:

```text
runs/<run_id>/matrices/turn_0001_A.npy
runs/<run_id>/matrices/turn_0001_B.npy
runs/<run_id>/matrix_index.jsonl
runs/<run_id>/events.jsonl
runs/<run_id>/predictions.jsonl
runs/<run_id>/results.csv
runs/<run_id>/labels.jsonl
```

matrix index에는 다음을 포함한다.

```text
run_id
turn_id
agent_id
matrix_path
matrix_shape
matrix_dtype
matrix_hash
source_event_ids
source_data_ids
update_rule_id
visible_to_agent
```

라벨은 분리한다.

절대 라벨:

```text
actual_action
partner_action
resource_delta
integrity_delta
tone_value
survived
prediction_error
```

해석 라벨:

```text
"이 패턴은 회복 전조처럼 보인다"
"이 mode는 partner instability와 관련 있어 보인다"
```

해석 라벨에는 반드시 다음을 붙인다.

```text
generated_by
info_class
semantic_judgement_status
source_data_ids
```

## 송련 메타정보 경계

이 실험은 송련의 메타정보 구분을 보존해야 한다.

절대 정보:

- id
- path
- matrix hash
- numeric value
- action id
- computed delta
- computed prediction error
- schema validation status
- tool result

상대 정보:

- 특정 하나의 record 또는 field에 직접 대응하는 해석

혼합 정보:

- 여러 record에 근거한 의미 해석. 예: "이 vessel 영역은 coordination과 관련 있어 보인다", "이 패턴은 attachment-like하다."

코드가 써도 되는 것:

- id
- 숫자 record
- status label
- 복사된 LLM raw output
- provenance
- validation result

코드가 쓰면 안 되는 것:

- vessel 의미에 대한 자연어 설명
- agent가 무엇을 느꼈다는 주장
- agent가 의식을 달성했다는 주장

## 설계 위험

위험 1: 의인화 누출.

완화:

- 중립 action id 사용
- 중립 state name 사용
- v0에서 감정 label 금지
- 주장 범위 제한

위험 2: 언어 역할극이 실험을 지배함.

완화:

- finite action set
- structured prediction
- v0에서 free speech 금지

위험 3: 사후 패턴 채굴.

완화:

- metric 사전 선언
- seed 저장
- 기준군 비교
- 탐색적 label과 1차 metric 분리

위험 4: 코드가 의미 주장을 생성함.

완화:

- 코드는 절대 정보와 복사 텍스트만 쓴다.
- LLM/인간 해석에는 metainfo field를 붙인다.

## 열린 질문

1. 첫 버전에서 전체 vessel matrix를 보여줄 것인가, readout summary만 줄 것인가?
2. partner vessel visibility는 hidden, partial, exposed 중 무엇으로 둘 것인가?
3. 가장 작은 유용한 matrix 크기는 4x4, 8x8, 16x16 중 무엇인가?
4. vessel update rule은 손설계, random seed 기반, 학습형 중 무엇으로 할 것인가?
5. agent는 다음 full vessel을 예측할 것인가, top changed cells나 summary statistics부터 예측할 것인가?
6. survival tone은 vessel update에서 prediction error와 어떻게 결합할 것인가?
7. 어떤 최소 결과가 나와야 이 철학 문서를 development map으로 승격할 것인가?

## 승격 후보 조건

이 아이디어는 다음을 명시할 수 있을 때 이후 문서로 승격할 수 있다.

- 정확한 game rule
- 정확한 action set
- 정확한 vessel shape
- 정확한 vessel update rule
- 정확한 prediction schema
- 정확한 baseline condition
- 정확한 metric
- 정확한 metainfo frame boundary

그 전까지 이 문서는 철학 문서로 남긴다.
