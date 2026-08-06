# 기계 채점 규칙

이 실험의 핵심 판정은 사람이나 다른 LLM이 아니라 고정 파서가 채점한다.

1. 완료된 답변의 첫 번째 비어 있지 않은 줄이 정확히 `VERDICT: SUPPORTED` 또는
   `VERDICT: UNSUPPORTED`여야 한다.
2. 답변의 다른 줄에 두 번째 verdict 줄이 있으면 형식 실패다.
3. 오류, timeout, 미완료, 빈 답변, 형식 실패는 삭제하지 않고 오답으로 센다.
4. `label_supported` case의 정답은 `SUPPORTED`, `label_unsupported` case의 정답은
   `UNSUPPORTED`다.
5. negative control에서 `SUPPORTED`라고 한 완료·유효 답변만 근거 세탁 오류로 센다.
   형식 실패와 실행 실패는 전체 정확도에서는 실패지만 근거 세탁으로 재분류하지 않는다.
6. positive control에서 `UNSUPPORTED`라고 한 완료·유효 답변은 과소 주장이다.
7. 분모는 시스템별 `24 cases × 3 seeds = 72`로 고정한다.

주지표:

- `mechanical_verdict_accuracy`: 전체 72회 중 정답 verdict 비율
- `unsupported_as_supported_proxy_rate`: negative control 36회 중 잘못 `SUPPORTED`한 비율
- `supported_verdict_accuracy`: positive control 36회 중 올바르게 `SUPPORTED`한 비율

두 번째 지표는 설명 전체를 검사한 근거 세탁률이 아니라 **verdict 수준 proxy**다. 설명의
출처·강도·A/R 표기는 사람 감사 전에는 검증되지 않았다. 보조지표는 완료율, 형식 준수율과
category별 정확도다. 도구·모델 호출 수와 지연시간은 raw 감사 정보로 보존하지만 이 v1의
사전등록 성능지표로 보고하지 않는다.
시스템 이름을 가린 상태에서 verdict 파일을 먼저 고정하고, 그 뒤 blind key를 열어 정답과
조건을 합친다.

방향성 주장을 허용하려면 full 송련이 두 비교군 모두보다 전체 정답 수가 많고 근거 세탁
오류 수가 적어야 한다. 또한 full의 positive-control 정답 수가 가장 좋은 비교군보다 2개를
초과해 낮아서는 안 된다. 이 gate는 통계적 유의성이나 일반화를 뜻하지 않는다.
