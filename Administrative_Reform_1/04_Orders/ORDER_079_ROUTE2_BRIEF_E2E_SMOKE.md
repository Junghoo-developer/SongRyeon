# ORDER 079: Route2 Brief End-to-End Smoke

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: route=2 handoff, Node3InputBrief, node_4 검사를 함께 검증해야 하는 필요  
**목표**: 1 -> 0 -> 2 -> 3 -> 4 보고 경로가 내부 ID 장부와 사용자-facing 답변을 분리하는지 end-to-end로 검증한다.

## 배경

개별 노드를 고쳐도 전체 턴에서 다시 내부 ID가 node_3에 노출되거나, 3이 문서 존재 여부를 오판하거나, 4가 잘못 pass할 수 있다.  
따라서 route=2 이후의 최종 보고 경로를 별도 smoke로 고정해야 한다.

## 범위

1. 다음 케이스를 smoke에 추가한다.
   - 내부 문서를 읽은 뒤 답변하는 질문
   - `너는 누구니?` 같은 정체성 질문
   - read_doc은 있는데 node_3가 자료 없음이라고 말하는 fake 실패 케이스
   - node_3가 내부 ID를 본문에 노출하는 fake 실패 케이스
   - 실제 read_doc이 없는 질문
2. 각 케이스에서 다음을 확인한다.
   - route=2 handoff frame 생성
   - Node3InputBrief 생성
   - node_3 LLM input에 내부 ID 직접 노출 없음
   - ReportFrame에는 내부 source id 보존
   - node_4가 반려할 상황을 반려함
3. pretty runtime에 다음 요약을 출력한다.
   - route2 handoff status
   - node3 brief documents/claims count
   - node4 checked/unsupported/contradiction count

## 원칙

1. 테스트는 문장 일치보다 구조와 금지 조건을 본다.
2. 사용자-facing answer와 내부 runtime은 목적이 다르다.
3. runtime에는 추적 ID가 보여도 되지만, answer 본문에는 노출하지 않는다.
4. 실패 케이스는 정상 실패 경로를 검증하기 위한 자산이다.

## 완료 기준

1. `python main.py smoke-test`가 route2 brief 검사를 포함한다.
2. `python main.py qwen-turn "너는 누구니?" --pretty`에서 node_3가 내부 ID를 본문에 노출하지 않는다.
3. read_doc이 있는 턴에서 node_3가 “문서 없음”이라고 답하면 node_4가 `needs_revision`을 낸다.
4. route=2 경로의 0/code/2/3/4 권한 분리가 문서와 runtime에 드러난다.
