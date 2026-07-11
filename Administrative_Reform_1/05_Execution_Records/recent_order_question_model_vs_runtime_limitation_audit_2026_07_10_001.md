# 최근 발주서 질문의 모델 한계 대 런타임 한계 감사

- 날짜: 2026-07-10
- 대상 질문: `최근 발주서를 읽고 내가 너를 개발할 때 무엇을 개선할지 무엇을 염두에 둘지 말해줘`
- 작업 범위: 원인과 책임 경계 감사만 수행, 코드 수정 없음

## 판정 기준

1. 필요한 절대정보가 모델 입력에 실제로 있었는가.
2. 사용자 목표가 프롬프트와 스키마에서 끝까지 보존됐는가.
3. 코드가 확정 가능한 최신순·파일 ID·실제 읽기 수를 LLM 추측에 맡기지 않았는가.
4. 필요한 정보와 명시 지시가 있었는데도 모델이 이를 어겼는가.
5. 앞 단계의 실수를 후단 guard가 검출할 수 있었는가.

## 감사 결과

### 1. 최신 발주서 탐색 실패: 런타임 구조 책임이 큼

- L document memory index item에는 doc_id, content hash, snapshot ID, 문서 종류, 크기가 있지만 파일 수정 시각이나 ORDER 번호 정렬 키가 없다.
- search_docs는 query embedding cosine similarity만으로 내림차순 정렬한다.
- 따라서 `최근`은 시간 조건이 아니라 의미 검색어로만 처리됐다.
- 실제 검색 상위 결과는 ORDER_061과 과거 실행 기록이었다.
- Qwen은 최신 ORDER 목록이나 수정 시각을 받지 못했으므로 최신 문서를 확정할 수 없었다.

판정: 주원인 `runtime/input design`, 모델 책임 낮음.

### 2. L1이 목표를 단일 문서 조회로 축소: 혼합 책임

- L1은 원래 user query를 입력으로 받았다.
- L1 prompt에는 사용자 제약과 다중 문서 요구를 반영하라는 규칙이 있다.
- 하지만 `최근 발주서`라는 표현은 문법적으로 단수/집합 의미가 모호하고, 별도의 `latest_order_review` evidence kind도 없다.
- Qwen은 `single_doc_lookup`, minimum read 1을 선택했다.

판정: `model judgement + contract vocabulary gap` 혼합.

### 3. L 2회차가 같은 방향을 반복: 런타임 배선 책임

- node_0 return memory item에는 직전 read_doc IDs와 search result IDs가 기록된다.
- node_1 router는 memory packet record 본문을 볼 수 있다.
- 그러나 다음 L1 입력은 memory packet target, trace IDs, source data IDs만 받고 memory item 본문은 받지 않는다.
- 따라서 새 L1은 직전 검색이 어떤 문서를 읽었는지 직접 확인하지 못한 채 목표를 다시 만들었다.

판정: `runtime memory handoff gap`.

### 4. L3의 achieved/matched 판정: 모델 책임이 큼

- L3는 user query, L1 goal, read_doc IDs, read document previews, candidate previews를 받았다.
- prompt는 사용자의 실제 요청 범위에 충분할 때만 achieved/matched를 허용한다.
- 실제 read_doc은 ORDER_061과 문서화 규칙 기록 2개였는데, L3 이유는 ORDER_059/058/057까지 읽었다고 서술했다.
- 이는 공급된 read_doc IDs와 맞지 않고, prompt의 read candidate/read document 분리 규칙도 어겼다.
- 다만 code count guard는 L1이 잘못 설정한 minimum 1만 검사하므로 이 의미 오류를 막지 못했다.

판정: 주원인 `Qwen semantic judgement failure`, 부원인 `guard coverage gap`.

### 5. node_3가 개선 조언 대신 런타임 상태를 답함: 혼합 책임

- node_3 payload에는 원래 user_question과 7개 문서 원문이 포함됐다.
- prompt 첫 규칙은 user_question에 직접 답하라는 것이다.
- Qwen은 이를 따르지 않고 처리 단계, 모델 사용, 문서 count를 중심으로 답했다.
- 동시에 payload에는 문서 장부, runtime task 19개, 여러 count와 상태가 함께 있어 작은 모델의 주의가 내부 상태로 쏠릴 가능성이 높다.
- 실제 문서도 최신 개발 방향과 직접 맞지 않아 개선 조언 재료가 약했다.

판정: `model instruction-following failure + noisy/low-relevance payload` 혼합.

### 6. node_4 pass: 런타임 검증 범위 책임이 큼

- node_4 prompt의 주목적은 brief 밖 주장, count 모순, 근거 역할 혼동을 검사하는 것이다.
- 사용자 질문에 실제로 답했는지를 별도 구조 규칙으로 강제하지 않는다.
- 최종 답변은 질문에는 답하지 않았지만 count와 내부 상태 주장은 brief 범위 안에 있었으므로 pass했다.

판정: `gate contract gap`, 모델 성능만 높여도 보장되지 않음.

## 최종 결론

- 최신 문서를 못 찾은 핵심 원인은 모델 크기보다 최신순 절대정보와 검색 연산이 없는 런타임 구조다.
- L3의 거짓 achieved와 node_3의 질문 불이행에는 Qwen3 14B의 의미 판단·지시 준수 한계가 실제로 드러났다.
- node_4가 이를 놓친 것은 검증 계약이 관련성/질문 충족을 직접 다루지 않기 때문이다.
- 더 큰 모델은 L1/L3/node_3 판단 품질을 개선할 가능성이 있지만, 최신 정보 미공급과 후단 guard 부재는 해결하지 못한다.

요약 판정: `모델만의 한계가 아니라, 구조가 먼저 실패하고 모델이 그 실패를 확대했으며 guard가 마지막에 놓친 복합 실패`.
