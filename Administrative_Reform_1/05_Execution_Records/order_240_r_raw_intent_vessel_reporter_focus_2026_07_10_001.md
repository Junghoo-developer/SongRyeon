# ORDER 240 실행 기록

- 날짜: 2026-07-10
- 결과: 구현 및 회귀 검증 완료
- 변경: R1 required granularity를 사용자가 요구한 deepest material floor로 정의했다.
- 변경: Node3 허용 근거에 Vessel R channel을 추가하고 R-only focused payload를 만들었다.
- 검증: 관련 pytest 10개와 quick-smoke 통과.
- live 결과: R1=`raw`, 6단계 RawSource 도달, Node3 raw count=1을 확인했다.
- 남은 실패: RawSource text가 Node3 item에는 아직 metadata-only였고 Node4가 channel 혼동을 반려했다.
- 후속: ORDER 241에서 원문 text를 실제 Node3 말 재료로 연결했다.
