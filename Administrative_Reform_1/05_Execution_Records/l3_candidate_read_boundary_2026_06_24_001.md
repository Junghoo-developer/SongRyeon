# l3 candidate read boundary 2026-06-24 001

## 배경

L1은 여러 문서 열람과 연관성 분석을 L루프 목표로 비교적 잘 잡기 시작했다.

하지만 L3가 다음을 혼동했다.

- `controller_decision=stop_success`
- 검색 후보 수
- 실제 읽은 문서 수
- 문서 간 연관성 분석 가능 여부

이 때문에 검색 후보가 있고 루프가 종료되었다는 사실을
"여러 문서를 읽고 관계 분석까지 성공했다"는 식으로 과대 해석할 위험이 있었다.

## 구현

L3 LLM input payload에 명시적인 절대 count를 추가했다.

```text
evidence_counts.preserved_candidate_count
evidence_counts.unique_search_result_document_count
evidence_counts.read_document_count
read_doc_ids
search_result_doc_ids
```

L3 프롬프트에는 다음 규칙을 추가했다.

- `controller_decision`은 루프 종료 신호이지 목표 달성 증거가 아니다.
- `candidate_count`는 보존 후보 수이지 읽은 문서 수가 아니다.
- 실제 원문 열람 근거는 `read_document_count`, `read_doc_ids`, `read_document_previews`뿐이다.
- 여러 문서 열람, 무작위/탐색, 비교, 연관성 분석이 목표라면 읽은 문서가 2개 미만일 때 거시목표를 `achieved`로 두지 않는다.
- 검색 후보만 있으면 후보 확보는 말할 수 있지만, 원문 열람이나 분석 완료처럼 말하지 않는다.
- 미시목표가 첫 검색/조회 준비라면 거시는 partial이어도 미시는 achieved일 수 있다.

## 의미

이 변경은 코드가 의미판정을 대신하는 것이 아니다.

L3가 이미 받은 근거의 종류를 더 분명히 보고,
후보 확보와 원문 열람과 분석 완료를 섞지 않도록 프롬프트와 입력 자료를 정리한 것이다.

## 검증

- `python -m compileall songryeon_core`
- `python main.py smoke-test`

두 검증을 통과했다.

