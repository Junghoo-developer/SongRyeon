# L/R/2 라이브 통합 시험 기록 2026-07-11

## 범위

ORDER 253~255 이후 로컬 Qwen과 Neo4j를 실제로 연결해 다음을 확인했다.

1. L 원문 확보 절대 상태가 terminal과 node_3까지 전달되는가
2. R partial 이후 node_1이 L/R/2를 다시 판단하는가
3. 근거 조회가 필요 없는 질문이 route 2로 곧바로 닫히는가

코드 수정 없이 live 실행만 수행했다.

## 사전 확인

```text
Qwen ping: ok
model: qwen3:14b
transport: ollama

Vessel readback: passed
Neo4j records: 4611
Neo4j relationships: 1747
required property missing: 0
```

## 시험 1: L 원문 확보

입력:

```text
Administrative_Reform_1/04_Orders/ORDER_255_L_CANDIDATE_VS_ORIGINAL_MATERIAL_STATUS_V0.md
문서를 검색해서 read_doc으로 실제 원문을 읽고, 검색 후보 수와 실제 원문 확보 수를
구분해서 핵심을 설명해줘.
```

실행 결과:

```text
status: ok
elapsed: 292.1 seconds
route: L -> L requested -> 2
actual L runs: 1
actual read_doc records: 7
node_3 supplied document contexts: 4
L evidence acquisition: original_material_acquired
L original material count: 7
L task: partial
L semantic goal match: partial
node_4: pass
```

ORDER 255의 절대 상태 전달은 작동했다. 검색 후보와 실제 원문 수가 분리됐고,
지정 문서를 실제로 읽지 못한 사실도 L3가 partial로 표시했다.

그러나 node_3 최종 본문은 grounding block의 `실제 read_doc 7개`와 반대로
`실제 문서 또는 코드 원문 읽기는 발생하지 않았다`고 서술했다. node_4는 이 모순을
잡지 못하고 pass했다. 또한 최종 본문은 요청 문서 설명보다 실행 단계 나열에 치우쳤다.

## 시험 2: 복잡한 R 재판정

입력:

```text
Vessel R 그래프 기억에서 ORDER 090 L Loop Budget Plan을 찾아 시간축과 요약 계층을 따라
가능한 근거를 확인하고, 충분하지 않으면 현재 R 결과를 바탕으로 다음 경로를 다시 판단해줘.
```

same-turn R reroute를 활성화하고 최대 2회로 실행했으나 424초 제한을 넘겼다.
최종 export는 생성되지 않았고 Python 프로세스도 남지 않았다. 따라서 이 실행만으로
R 2회차 동작 성공/실패를 판정하지 않는다. 긴 지연 자체는 별도 운영 위험이다.

## 시험 3: 좁은 R 1회와 L 전환

입력:

```text
Vessel R 그래프 기억에서 CoreEgo와 Time Axis가 어떤 관계로 연결되는지
한 가지 경로만 확인해서 설명해줘.
```

실행 결과:

```text
status: ok
elapsed: 267.4 seconds
route: R -> L -> 2
R runs: 1
R task: partial
R continuation: stop_budget_exhausted
node_1 recheck route: L
L runs: 1
L evidence acquisition: original_material_acquired
L original material count: 3
L semantic goal match: matched
node_4: pass
```

R partial 결과를 node_0이 보존하고 node_1이 L로 전환하는 ORDER 254 배선은 실제 Qwen에서도
작동했다. L도 관련 문서 원문 3개를 확보했다.

그러나 최종 답변은 CoreEgo와 Time Axis의 구체적인 관계를 설명하지 않고 실행 상태만
나열했다. node_4는 사용자 과업 미충족을 잡지 못하고 pass했다.

## 시험 4: route 2 직행

입력:

```text
안녕. 오늘도 잘 부탁한다고 한 문장으로만 답해줘.
```

실행 결과:

```text
status: ok
elapsed: 36.9 seconds
route: 2
L runs: 0
R runs: 0
node_2 answer basis: mixed_or_uncertain
node_4: pass
```

node_1은 L/R을 열지 않고 route 2를 올바르게 선택했다. 그러나 node_3는 단순 인사를
하지 않고 `자료가 충분하지 않아 구체적인 답변을 제공할 수 없다`고 답했다.
node_4는 사용자 지시 불이행을 잡지 못하고 pass했다.

## 판정

### 구조 배선

부분 합격.

- L 후보/원문 절대 상태 분리: 작동
- R partial -> node_1 recheck -> L 전환: 작동
- 단순 요청 route 2 직행: 작동
- same-turn R 최대 2회 live 완료: 시간 제한으로 미확인

### 최종 답변 품질과 검사

불합격.

- node_3가 code-supplied grounding count와 모순되는 문장을 쓸 수 있다.
- node_3가 사용자 질문 대신 런타임 상태를 보고하는 경향이 있다.
- 근거 조회가 필요 없는 생성/대화 요청도 근거 부족으로 거절한다.
- node_4가 위 세 종류의 사용자 과업 미충족을 pass할 수 있다.

## 다음 우선순위

새 L/R 기능을 추가하기 전에 다음 경계를 감사해야 한다.

1. node_3가 grounding block의 절대 count와 반대되는 서술을 쓰는 경로
2. node_3가 사용자 과업보다 runtime material inventory를 답변 본문으로 선택하는 경로
3. node_4의 user-task-fulfillment 검사 부재
4. 근거 비의존 생성 요청에서 node_2의 `mixed_or_uncertain`과 node_3 거절 태도

키워드 휴리스틱이나 질문 유형별 code 답변은 추가하지 않는다. 사용자 과업 해석과
답변 적합성 판단은 LLM 책임으로 유지하되, code가 제공한 절대 count와 명시적 사용자 지시를
검사 가능한 구조로 전달하는 방향을 우선 검토한다.
