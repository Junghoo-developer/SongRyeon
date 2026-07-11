# ORDER 241: Vessel Raw Original To Node3 Material v0

## 상태

- Status: implemented and regression verified; follow-up completed by ORDER_242
- Date: 2026-07-10
- Scope: node_0 Vessel return material / Node3 raw text / raw-primary focused delivery

## 배경

ORDER 240 통합 시험에서 R1은 `raw`를 요청했고 R은 6단계 끝에 ORDER_090
RawSource 원문을 실제로 읽었다. node_3 brief도 raw original count를 1로 셌다.
그러나 `Node3VesselRMaterialItem`은 summary text만 담을 수 있었고, RawSource item은
metadata-only로 내려갔다. node_3는 원문을 보지 못하고 상위 요약만 사용했으며,
Vessel 재료와 document evidence 채널을 섞어 말해 node_4가 반려했다.

## 목표

- RawSource item에 code-copied `raw_text`와 문자 수를 별도 필드로 보존한다.
- 원문 포함 상태를 `included_raw_original_text`로 명시한다.
- focused R-only payload에서는 raw 원문이 있으면 원문을 우선 공급한다.
- 보조 summary 전문은 focused payload에서 생략하고 count만 남긴다.

## 구현 경계

- raw text는 read packet에 이미 복사된 원문을 그대로 잇는다.
- code는 원문을 요약하거나 중요 문장을 선택하지 않는다.
- full Node3 brief와 모든 summary/provenance는 DataStore에 유지한다.
- node_3는 원문 의미를 해석하고 답변 본문을 작성한다.

## 하지 않는 것

- Vessel 원문을 read_doc/read_code_file/document context로 이름 바꾸지 않는다.
- node_4 evidence-channel guard를 약화하지 않는다.
- 원문을 임의 문자 상한으로 자르지 않는다.
- 상위 summary record를 삭제하지 않는다.

## 완료 조건

- RawSource material item에 원문 전문과 정확한 문자 수가 들어간다.
- raw item provenance에 source_text data ID가 보존된다.
- node_3 LLM payload는 내부 ID 없이 raw text를 볼 수 있다.
- raw-primary focused payload는 보조 summary count를 남기고 원문을 우선한다.
- pytest, quick-smoke, 완전 통합 qwen-turn을 실행한다.
