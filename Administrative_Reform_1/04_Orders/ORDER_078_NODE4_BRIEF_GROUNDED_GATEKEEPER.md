# ORDER 078: Node4 Brief-Grounded Gatekeeper

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: node_4가 report와 내부 장부 일부만 보고 잘못 pass를 준 문제  
**목표**: node_4가 최종 답변을 `Node3InputBrief` 및 문서 재료와 대조해 검사하도록 강화한다.

## 배경

node_4는 최종 답변의 환각과 근거 이탈을 잡아야 한다.  
하지만 현재는 어떤 주장을 어떤 재료와 대조했는지 노출이 약하고, “문서가 없다” 같은 명백한 모순도 놓칠 수 있다.

node_4는 내부 trace 장부보다 node_3가 실제로 받은 브리프와 최종 답변을 비교해야 한다.

## 범위

1. node_4 입력에 `Node3InputBriefFrame`을 넣는다.
2. node_4 입력에는 내부 ID보다 다음을 우선 넣는다.
   - user_question
   - read_documents
   - answer_materials
   - allowed_claims
   - rendered_markdown
3. node_4 output에는 다음을 포함한다.
   - `gate_status`
   - `reason`
   - `checked_claims`
   - `unsupported_claims`
   - `contradictions`
   - `revision_targets`
4. 다음 조건은 자동 반려 후보로 둔다.
   - read_documents가 있는데 답변이 “문서가 없다”고 말함
   - answer_materials가 있는데 답변이 “보고할 내용이 없다”고 말함
   - 내부 ID를 사용자 답변 본문에 노출함
   - user_question에 직접 답하지 않음
5. `needs_revision` 발생 시 이후 ORDER에서 재작성 루프를 붙일 수 있게 한다.

## 원칙

1. node_4는 답변을 새로 쓰지 않는다.
2. node_4는 검사 결과와 반려 이유만 쓴다.
3. pass는 “완벽한 진실”이 아니라 “제공된 brief 안에서 큰 위반 없음”을 뜻한다.
4. 검사 결과는 사람이 볼 수 있어야 한다.

## 완료 기준

1. node_4가 `Node3InputBriefFrame`을 입력으로 받는다.
2. read_doc 존재와 “문서 없음” 답변이 충돌하면 `needs_revision`이 나온다.
3. node_4 pretty runtime에 checked/unsupported/contradiction 개수가 보인다.
4. fake 실패 케이스로 node_4 반려가 검증된다.
