# ORDER 241 실행 기록

- 날짜: 2026-07-10
- 결과: 구현 및 회귀 검증 완료
- 변경: Node3VesselRMaterialItem에 `raw_text`, 문자 수, `included_raw_original_text` 상태를 추가했다.
- 변경: focused payload는 RawSource 원문을 우선하고 보조 summary 전문은 count만 남겼다.
- 검증: 관련 pytest 12개와 quick-smoke 통과.
- live 결과: Node3 input에 ORDER_090 원문과 raw status가 실제 포함됐다.
- 남은 실패: Node3가 문서의 예시를 현재 실행 사건으로 바꿔 말했고 Node4가 needs_revision 처리했다.
- 후속: ORDER 242에서 proposal/current modality와 gate grounding을 정렬했다.
