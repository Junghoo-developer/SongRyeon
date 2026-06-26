# ORDER 077: Node3 Input Brief

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: node_3에게 내부 ID 장부를 직접 주자 14B 모델이 문서 추출 여부와 역할을 혼동한 문제  
**목표**: node_3가 사용자에게 답하기 위해 필요한 의미 단위 입력을 `Node3InputBrief`로 제공한다.

## 배경

`source_data_ids`, `trace_000021`, `boundary_dry_001` 같은 내부 ID는 무결성 추적에는 필요하지만, node_3가 자연어 답변을 만드는 데 직접 필요한 정보는 아니다.  
node_3는 검색자가 아니며, 내부 장부 검증자도 아니다.

node_3에게 필요한 것은 다음과 같은 보고 브리프다.

- 사용자 질문
- 이번 턴에서 실제로 읽은 문서
- 답변에 사용할 수 있는 문서 내용 요약 또는 원문 발췌
- 사용 가능한 혼합 정보
- 금지 사항
- 불확실성 표기 규칙

## 범위

1. `Node3InputBriefFrame` 또는 동등한 payload를 만든다.
2. 생성 위치는 2 또는 2.5로 둔다.
   - 2: 메타정보 경계 확정
   - 2.5: node_3용 의미 브리프 생성
3. node_3 LLM payload에는 내부 ID를 직접 넣지 않는다.
4. node_3 LLM payload에는 다음을 넣는다.
   - `user_question`
   - `read_documents`
   - `answer_materials`
   - `allowed_claims`
   - `uncertainty_rules`
   - `forbidden_phrases`
5. 내부 source id는 `Node3InputBriefFrame`과 `ReportFrame`의 기록용 필드에만 남긴다.

## 원칙

1. node_3는 보고관이지 검색자가 아니다.
2. node_3는 내부 ID를 본문에 노출하지 않는다.
3. node_3가 “문서가 없다”고 말하려면 handoff/brief에 실제로 문서가 없어야 한다.
4. 문서 원문과 요약은 출처를 가진 재료로 다루되, 최종 진실성은 단정하지 않는다.
5. brief는 LLM이 알아먹는 형태여야 하며, DataStore 내부 형식을 그대로 노출하지 않는다.

## 완료 기준

1. `node_3` LLM call input에 `source_data_ids`, `trace_id`, `boundary_id`가 직접 들어가지 않는다.
2. read_doc 결과가 있으면 `Node3InputBriefFrame.read_documents`가 비어 있지 않다.
3. `너는 누구니?` 같은 질문에서 node_3가 “자료 없음”이라고 잘못 말하지 않는다.
4. pretty runtime에서 `node_3 input brief: documents=N, claims=M`이 보인다.
5. source id는 런타임 장부에는 남지만 사용자-facing answer 본문에는 나오지 않는다.
