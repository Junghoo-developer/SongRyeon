# ORDER 073: Node3 LLM Reporter

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 현재 최종 답변이 코드 렌더러라 대화형 송련으로 보기 어려운 문제  
**목표**: Node3가 Node2가 허용한 정보만 사용해 LLM 보고문을 작성하게 한다.

## 배경

현재 `[answer]`는 코드가 DataStore를 읽어 만든 렌더링 결과다.  
정직하긴 하지만 대화형 에이전트의 최종 발화는 아니다.

Node3를 LLM reporter로 바꾸되, Node2 boundary 밖의 주장을 새로 만들 수 없게 해야 한다.

## 범위

1. `ReportFrame`을 LLM report용으로 확장한다.
2. Node3 prompt를 작성한다.
3. 입력에는 다음을 포함한다.
   - Node2 boundary
   - 허용된 absolute info
   - 허용된 mixed info
   - excluded claim 목록
   - 사용자 입력
   - 보고 스타일 모드
4. LLM 출력에는 다음을 둔다.
   - `report_markdown`
   - `used_info_ids`
   - `uncertainty_notes`
   - `refusal_or_limitations`
   - `source_data_ids`
5. 코드는 report text를 새로 쓰지 않고 그대로 보존한다.
6. Node4 통과 전에는 최종 사용자 답변으로 확정하지 않는다.

## 원칙

1. Node3는 Node2 boundary 밖의 내용을 추가하지 않는다.
2. 문서 발췌는 문서 발췌로 표시한다.
3. LLM 보고문은 LLM 보고문이라고 표시한다.
4. 불확실성은 숨기지 않는다.

## 완료 기준

1. Node3 LLM call이 기록된다.
2. 최종 답변 후보가 `ReportFrame`에 저장된다.
3. 사용된 info id 목록이 존재한다.
4. Node4가 없거나 실패하면 최종 출력은 draft임을 표시한다.
5. smoke test가 boundary 밖 claim 삽입을 감지한다.

