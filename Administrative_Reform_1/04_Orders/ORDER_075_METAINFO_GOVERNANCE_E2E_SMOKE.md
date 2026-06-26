# ORDER 075: Metainfo Governance End-to-End Smoke

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 월권 제거와 LLM 노드 삽입 뒤 전체 체계를 검증해야 하는 필요  
**목표**: Node1, L1, L2, L3, Node2, Node3, Node4가 메타정보 관리법을 지키는지 end-to-end로 검증한다.

## 배경

각 노드를 따로 고쳐도 전체 턴에서 다시 정보 등급이 섞일 수 있다.  
따라서 최종 목표는 단일 기능 통과가 아니라 전체 런타임 정직성이다.

## 범위

1. qwen-turn smoke를 만든다.
2. qwen-chat pretty 출력 smoke를 만든다.
3. export artifact replay smoke를 만든다.
4. 다음 케이스를 포함한다.
   - 정상 내부 문서 질문
   - 문서가 부족한 질문
   - 라우팅이 애매한 질문
   - Node3가 boundary 밖 claim을 넣는 fake 실패 케이스
   - 도구 결과가 0개인 케이스
   - LLM schema 실패 fallback 케이스
5. 각 케이스에서 다음을 검사한다.
   - LLM이 쓴 문장과 코드가 쓴 라벨이 구분되는가
   - 모든 mixed info가 source id를 갖는가
   - Node4가 필요한 경우 reject하는가
   - 최종 출력이 승인된 draft인지 실패 보고인지 명확한가

## 원칙

1. smoke test는 사용자가 신뢰할 수 있는 최소 안전망이다.
2. 테스트가 보기 힘들면 실패 원인을 사람이 읽기 좋게 출력한다.
3. LLM 비결정성 때문에 정확한 문장 일치는 피하고, 구조와 라벨을 검사한다.
4. Qwen 호출 실패와 schema 실패는 정상 실패 경로로 다룬다.

## 완료 기준

1. `python main.py smoke-test`가 전체 메타정보 governance 검사를 포함한다.
2. `python main.py qwen-turn "... " --pretty`에서 최종 답변의 승인 상태가 보인다.
3. replay에서 LLM call, tool result, metainfo boundary, gatekeeper decision이 이어진다.
4. 사용자가 코드 산출물과 LLM 산출물을 헷갈리지 않는다.

