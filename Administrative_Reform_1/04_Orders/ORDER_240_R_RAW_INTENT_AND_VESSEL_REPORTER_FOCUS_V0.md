# ORDER 240: R Raw Intent And Vessel Reporter Focus v0

## 상태

- Status: implemented and regression verified; follow-up completed through ORDER_242
- Date: 2026-07-10
- Scope: R1 requested granularity / node_3 Vessel evidence authority / R-only payload

## 배경

ORDER 239 통합 시험에서 R 배선은 성공했고 Vessel 재료 5개가 node_3 brief에
도달했다. 그러나 R1은 목표 문장에 RawSource 원문 확인을 썼으면서
`required_information_granularity=low_summary`를 냈고, R3는 source-leaf summary에서
충분하다고 멈췄다. node_3 프롬프트 첫 허용 근거 목록은 Vessel 재료를 누락해,
아래 Vessel 규칙과 모순되었다. node_3 LLM payload도 빈 L/document 장부를 포함해
16,701자까지 커졌다.

## 목표

- R1이 사용자가 요구한 가장 깊은 재료 농도를 stop floor로 보존한다.
- 원문/RawSource를 명시한 요청은 R1이 `raw`를 선택하도록 책임을 분명히 한다.
- node_3의 허용 근거 목록에 Vessel R material을 명시한다.
- Vessel만 말 재료인 턴은 빈 문서 장부를 제외한 focused payload를 사용한다.

## 구현 경계

- raw 필요성 판단은 R1 LLM 책임이며 code 키워드 분류를 추가하지 않는다.
- focused payload 여부는 material 존재와 count 0 여부만 code가 판정한다.
- node_3는 Vessel summary/raw material의 의미를 해석해 본문을 작성한다.
- full brief, provenance, trace/data records는 삭제하지 않는다.

## 하지 않는 것

- code가 R1 granularity를 사용자 문구로 강제 덮어쓰지 않는다.
- code가 Vessel summary 의미를 대신 작성하지 않는다.
- read_doc 0을 Vessel material 0으로 바꾸지 않는다.
- node_4 guard를 약화하지 않는다.

## 완료 조건

- R1 prompt가 required granularity를 deepest required material로 정의한다.
- node_3 prompt 허용 근거 목록에 Vessel R material이 포함된다.
- R-only node_3 payload는 Vessel material을 앞에 두고 빈 문서 장부를 생략한다.
- 기존 full brief와 DataStore provenance는 유지한다.
- pytest, quick-smoke, 완전 통합 qwen-turn을 실행한다.
