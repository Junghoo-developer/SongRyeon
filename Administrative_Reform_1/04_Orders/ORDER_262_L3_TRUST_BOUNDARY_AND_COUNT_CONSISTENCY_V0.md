# ORDER 262: L3 Trust Boundary And Count Consistency v0

## 1. 배경

ORDER 261은 코드 부분 구간을 범위와 원문이 결합된 재료로 node_3에 공급하고,
L3 revision이 새 구간을 읽은 뒤 의미 적합성을 다시 판단하게 했다.

그러나 live 감사에서 다음 문제가 확인됐다.

1. L3 LLM이 사용자 질문과 무관한 코드 내용을 `matched`라고 말해도,
   파일 경로와 원문 수량만 맞으면 `achieved`로 승격될 수 있다.
2. L3의 문서/코드 goal-match 조회가 현재 L run이 아니라 같은 턴의 DataStore 전체를 훑는다.
3. node_3와 node_4에 공급되는 코드 구간 원문의 전체 입력 예산이 없다.
4. revision L3가 `achieved`여도 node_0 return summary는 초기 L3의 `partial`을 복사한다.
5. node_2 schema repair는 특정 오류에서만 사용자 과업 계약을 잠근다.
6. `read_code_file` 고유 파일 수와 호출/구간 수가 사용자-facing 문구에서 혼동된다.

## 2. 목표

L3의 의미 판단은 LLM 책임으로 유지하되, 그 판단이 실제 공급 재료에 대응한다는
구조적 출처 결속을 추가한다. 동시에 current-run 범위, 전체 코드 원문 예산,
최신 revision 전달, schema repair 잠금, count 명칭을 절대정보 기준으로 정렬한다.

## 3. 구현 범위

1. L3가 `semantic_goal_match_status=matched`를 반환할 때 다음을 함께 반환한다.
   - code가 공급한 안전한 `material_ref`
   - 해당 재료에서 그대로 복사한 짧은 `evidence_excerpt`
2. code는 material ref가 실제 공급 목록에 있는지와 excerpt가 해당 원문 preview에
   실제 존재하는지만 검증한다. excerpt의 의미가 맞는지는 code가 판단하지 않는다.
3. L3의 explicit reference, read_doc, read_code_file, preview 조회를 현재
   `input_data_ids` 범위로 제한한다.
4. node_3 코드 원문은 24,000자 전체 예산을 사용한다.
   - 구간 중간을 자르지 않는다.
   - node_2가 선택한 evidence role 순서를 우선한다.
   - 예산을 넘기는 구간은 원문 전체를 제외하고 좌표와 제외 이유를 남긴다.
5. L3 의미 판정용 코드 preview도 같은 24,000자 전체 예산을 사용하며 최신 구간을
   우선 보존한다.
6. `l3_result` 상태 record를 선택했다는 이유만으로 모든 코드 원문을 node_3에
   자동 주입하지 않는다. 코드 원문은 정확한 `read_code_file` evidence ref를 선택해야 한다.
7. node_0 L return summary와 문서 장부는 초기/수정 L3 중 실제 최신 achievement frame을 사용한다.
8. node_2 repair는 최초 payload의 과업 계약 필드가 개별적으로 유효하면 schema 오류 종류와
   무관하게 그 과업 계약을 잠근다.
9. 사용자-facing count는 다음처럼 분리한다.
   - `read_code_file` 고유 파일 수
   - `read_code_file` 호출/구간 수

## 4. 정보 분류

- material ref, source data mapping, exact excerpt 존재 여부: 절대정보
- current L run source 범위와 원문 문자 예산 적용 결과: 절대정보/명시 정책
- L3 의미 일치 상태와 이유: 혼합정보
- node_2 evidence role과 과업 계약: LLM 상대/혼합정보
- 최신 revision 선택과 count 표시: 절대정보

## 5. 금지

- 함수명/키워드 일치로 code가 의미 관련성을 판정하는 휴리스틱
- excerpt의 의미를 code가 해석하거나 맞다고 확정하는 처리
- 코드 구간 중간 절단
- 예산을 넘긴 원문/trace/DataStore record 삭제
- L/R 라우팅, W/R loop, scheduler, 외부 DB 변경
- node_4 guard 약화

## 6. 완료 조건

1. 존재하지 않는 material ref 또는 원문에 없는 excerpt를 사용한 L3 `matched`는 schema 실패한다.
2. 같은 턴의 다른 L run 원문은 현재 L3 goal-match/count/preview에 섞이지 않는다.
3. node_3 코드 원문 합계가 24,000자를 넘지 않고, 제외 구간은 전체 좌표로 기록된다.
4. L3 status 선택만으로 모든 코드 원문이 자동 공급되지 않는다.
5. 최신 revision `achieved`가 L return summary와 node_3 brief에 보존된다.
6. evidence ref 오류 repair에서도 유효한 사용자 과업 계약이 바뀌지 않는다.
7. 동일 파일 두 구간을 읽으면 `고유 파일 1 / 호출·구간 2`로 표시된다.
8. `python -m compileall songryeon_core main.py` 통과.
9. `python -m pytest` 통과.
10. `python main.py smoke-test` 통과.

