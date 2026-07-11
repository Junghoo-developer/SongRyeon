# ORDER 238 실행 기록

- 날짜: 2026-07-10
- 결과: 구현 및 회귀 검증 완료
- 변경: selected material의 node kind, 원문 존재, 문자 수, child count를 code absolute fact card로 공급했다.
- 변경: 원문 RawSource의 granularity는 `raw`만, child 0의 action에서는 `deeper`를 제외했다.
- 검증: 좁은 pytest 6개와 quick-smoke 통과.
- live 결과: validator는 모순을 정직하게 막았지만 Qwen이 긴 input에서 좁은 상태표를 따르지 못했다.
- 후속: ORDER 239에서 RawSource focused input으로 해결했다.
