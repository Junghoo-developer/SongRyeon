# ORDER 242: Proposal Modality And Vessel Gate Grounding v0

## 상태

- Status: implemented and fully integrated live verification passed
- Date: 2026-07-10
- Scope: node_3 source modality / node_4 Vessel grounding authority

## 배경

ORDER 241 통합 시험에서 node_3는 ORDER_090 RawSource 원문을 직접 받았지만,
문서의 예시 `requested=5, approved=3`을 현재 턴에 실제 승인된 사건처럼 썼다.
node_4는 이 과장을 반려했지만, 동시에 brief의 실제 `Vessel=present`,
`R=sufficient`, `L=not_recorded`를 반대로 읽는 오독도 만들었다.
node_4 prompt의 첫 grounding 목록이 Vessel channel을 누락한 것이 한 원인이었다.

## 목표

- node_3가 제안/후보/예시와 현재 실행 사실을 분리한다.
- node_3는 Vessel 내부 field name을 사용자 문장에 그대로 노출하지 않는다.
- node_4가 Vessel raw text를 "그 원문이 무엇을 제안하는가"의 직접 근거로 인정한다.
- node_4가 Vessel/L status를 brief에 적힌 값 그대로 검사한다.

## 구현 경계

- 의미 판단은 node_3/node_4 LLM 책임이다.
- code 키워드 판정이나 current/proposal 자동 변환을 추가하지 않는다.
- node_4 code guard는 유지한다.
- read_doc, document context, Vessel 원문 채널은 계속 구분한다.

## 하지 않는 것

- 제안 문서 내용을 현재 구현 사실로 승격하지 않는다.
- Vessel 원문을 read_doc 근거로 재분류하지 않는다.
- node_4를 자동 pass로 바꾸지 않는다.
- 원문이나 trace/data record를 수정하지 않는다.

## 완료 조건

- node_3 prompt가 proposal/example/current runtime 경계를 명시한다.
- node_4 grounding channel 목록에 Vessel R material이 포함된다.
- Vessel raw text는 proposal claim을 검사할 수 있는 근거로 인정된다.
- 관련 pytest, quick-smoke, 완전 통합 qwen-turn을 실행한다.
