# ORDER 256-257 live 검증 기록

## 범위

ORDER 256의 node_2 과업 계약 및 node_3 집중 payload와 ORDER 257의 node_4 과업 수행·본문
일관성 검사를 실제 `qwen3:14b`로 두 차례 검증했다. 이 기록에서는 추가 code patch를 하지 않았다.

## 시험 1: 근거 비의존 한 문장 요청

입력:

```text
안녕. 오늘도 잘 부탁한다고 한 문장으로만 답해줘.
```

확인된 절대 상태:

```text
runtime status = ok
route sequence = [2]
node_2 answer basis = relative_allowed
task_contract_status = recorded
evidence_requirement = not_required
node_4 task_fulfillment_status = fulfilled
node_4 grounding_consistency_status = consistent
node_4 gate_status = pass
완료 소요 = 326.2초
```

최종 답변:

```text
오늘도 잘 부탁드립니다.
```

판정: 기능 합격. 내부 runtime 장부나 grounding block이 사용자 한 문장 요청을 대체하지 않았다.
다만 간단한 요청에 5분 이상 걸린 속도는 별도 성능 문제다.

첫 시도는 외부 실행 제한 244초에 종료됐고 export가 생성되지 않았다. 같은 입력을 전체 파이프라인
완료 시간을 허용해 다시 실행한 결과가 위 기록이다.

## 시험 2: 실제 코드 원문 근거 요청

입력:

```text
songryeon_core/nodes/node_2_handoff.py 파일을 실제로 읽고, 이 파일이 node_3에게
집중된 답변 재료를 어떻게 전달하는지 한 단락으로 설명해줘. 읽지 못했다면 읽었다고 말하지 마.
```

확인된 절대 상태:

```text
runtime status = ok
route sequence = [L, L, 2]
actual L runs = 1
blocked top-level L reroute requests = 1
L internal continuation attempts = 12
unique actual_read_code_file = 1
actual_read_doc = 0
node_3 source-code contexts = 12
L evidence acquisition = original_material_acquired
L3 semantic goal match = partial
node_2 evidence requirement = required
node_4 task_fulfillment_status = partial
node_4 grounding_consistency_status = consistent
node_4 gate_status = needs_revision
완료 소요 = 179.1초
```

node_2에게 공급된 후보표에는 다음 answer-ready 후보가 실제 존재했다.

```text
E033: 읽은 코드 원문: songryeon_core/nodes/node_2_handoff.py
source_kind = read_code_file
material_channel = answer_ready
```

그러나 node_2 LLM은 다음 일반 자료만 supporting context로 선택했다.

```text
E001: node_2 입력 프레임
material_channel = generic
```

node_3는 파일의 세부 흐름을 확인할 수 없다고 쓴 동시에 일반적인 메타정보 처리 설명을 생성했다.
node_4는 이를 과업 부분 수행으로 판단했고 code 정책이 `needs_revision`으로 강제해 원문 노출을 막았다.

## 분리된 문제

### 1. source-code 원문 범위 부족

읽은 코드 미리보기에는 파일 앞부분의 import와 schema 이름이 주로 나타났다. 사용자가 물은 집중
payload 조립 로직은 파일 뒤쪽에 있어, 파일 앞부분만으로는 과업을 수행하기 어려웠다.

이것은 확인된 preview 내용에 근거한 해석이다. 향후 symbol/range/chunk 단위 code inspection 설계가
필요한지 별도 논의해야 한다.

### 2. code read와 minimum read 판정 불일치

실제 `read_code_file=1`이 존재했지만 L3 revision reason은 계속 다음을 기록했다.

```text
CODE_STATUS:l1_minimum_read_documents_not_met:required_1_actual_0
```

그 결과 같은 파일을 대상으로 12회 continuation이 이어졌다. 문서 읽기 수량과 코드 읽기 수량을
어떤 요구 종류에서 합산해야 하는지 구조 감사가 필요하다.

### 3. 중복 code material

같은 파일의 read-code 결과가 node_3 source-code context 12개와 node_2 answer material 후보 여러 개로
반복 노출됐다. 이는 node_2의 후보 선택 부담과 node_3 입력량을 키웠다.

### 4. node_2 선택 품질

ORDER 256 후보표는 answer-ready code record를 정상적으로 드러냈다. 하지만 실제 Qwen은 이를 고르지
않고 generic 입력 프레임을 골랐다. 따라서 후보표 생성 성공과 LLM 선택 성공을 분리해야 한다.

### 5. node_4 guard 성공

ORDER 257은 이번 실패에서 의도대로 작동했다. unsupported claim이나 count mismatch가 없어도 사용자
과업이 부분 수행에 그치면 pass시키지 않았다.

## 다음 결재 전 금지

- 실패 원인을 한 가지 prompt 문제로 단정하지 않는다.
- read-code 중복을 임의 dedupe해서 근거 장부까지 삭제하지 않는다.
- code가 관련 코드 구간을 키워드로 의미 선택하게 만들지 않는다.
- node_4 guard를 약화하거나 자동 재작성 루프를 열지 않는다.
- L 반복 예산을 더 늘려 문제를 가리지 않는다.
