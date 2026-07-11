# ORDER 243: Autonomous R Route Reality And Downstream Honesty v0

## 상태

- Status: implemented and verified
- Date: 2026-07-10
- Scope: node_1 L/R capability reality / explicit ORDER syntax / L3 goal match / Node3-4 grounding integrity

## 배경

ORDER 242 강제 R 시험은 RawSource 원문까지 6단계로 내려가 최종 Node4 pass를
확인했다. 같은 질문에서 force flag를 제거하자 node_1은 R이 RawSource 원문을
보지 못한다고 판단하고 L을 선택했다. L은 ORDER_090 원문을 읽지 못했지만 L3가
특정 문서 요청이 없었다고 판정해 achieved로 닫았다. Node3는 두 번째 근거 블록을
만들어 실제 read_doc 3개를 0개라고 썼고 Node4도 이를 통과시켰다.

## 목표

- node_1 capability card를 현재 R RawSource 원문 능력과 맞춘다.
- R의 이미 적재된 원문과 L의 fresh/un-ingested source lookup을 분리한다.
- 명시 ORDER 문법이 `ORDER_090`과 `ORDER 090`을 모두 동일한 구조 참조로 인식한다.
- L3는 explicit artifact resolver의 absolute result를 특정 문서 목표 검사에 사용한다.
- Node3는 위치와 무관하게 accidental grounding block을 제거한다.
- Node4는 두 개 이상의 grounding heading을 code guard로 반려한다.

## 구현 경계

- node_1의 최종 L/R 의미 선택은 LLM 책임으로 유지한다.
- code는 `ORDER 090`을 정해진 명시 참조 문법으로만 canonicalize한다.
- L3 code guard는 resolver가 기록한 selected document와 실제 read result를 비교한다.
- grounding 제거/중복 검사는 고정 heading 구조만 다루고 답변 의미를 판정하지 않는다.

## 하지 않는 것

- 사용자 키워드로 code가 R을 강제하지 않는다.
- 임베딩 점수나 문서 의미를 code가 대신 판단하지 않는다.
- L3/Node4 LLM guard를 약화하거나 자동 pass로 만들지 않는다.
- R/L 예산, Neo4j 데이터, same-turn reroute 횟수를 바꾸지 않는다.

## 완료 조건

- R capability card가 ingested RawSource original text를 명시한다.
- `ORDER 090`이 unique explicit artifact reference로 resolve된다.
- 해당 문서를 읽지 않은 L 결과는 achieved로 확정되지 않는다.
- 본문 중간 accidental grounding block이 제거된다.
- 두 번째 grounding heading이 남으면 Node4 code guard가 needs_revision 처리한다.
- compileall, pytest, smoke-test를 통과한다.
- force flag 없는 동일 live 질문에서 node_1이 R을 선택하는지 재시험한다.
