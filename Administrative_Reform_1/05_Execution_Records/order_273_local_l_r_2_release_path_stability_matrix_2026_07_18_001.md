# ORDER 273 Local L/R/2 Release Path Stability Matrix 실행 기록

## 1. 실행 기준

- 실행일: 2026-07-18
- 기준 commit: `74c90ee fix: bind L3 evidence by stable excerpt refs`
- 목적: 새 기능을 추가하지 않고 route 2, L 문서, L 코드, Vessel R, 공개 차단 경로를 같은 시점에 점검
- 결과 export: `.songryeon_core_cache/order_273/`
- 비밀값: Neo4j 비밀번호와 환경변수 값은 기록하지 않음

## 2. 종합 판정

| 사례 | 판정 | 절대 결과 |
| --- | --- | --- |
| A. route 2 직접 응답 | 통과 | route=`2`, L/R 실행 0회, trace/data=`25/52`, node_4=`pass` |
| B. L 내부 문서 | 통과 | route=`L -> 2`, L 1회, 문서 원문 1개, L3=`matched/ran/none`, node_4=`pass` |
| C. L workspace 코드 | 통과 | route=`L -> 2`, `read_code_file` 고유 파일 1개, L3=`matched/ran/none`, node_4=`pass` |
| D. Vessel R | 환경 미확인 | Neo4j `localhost:7787` 연결 거부, R read packet=`read_failed`, R 뒤 L 복구는 실행됨 |
| E. 결정론적 공개 차단 | 통과 | LOCAL/HONEST FALLBACK/CODE GUARD 전부 PASS, 최종 공개 차단 확인 |

## 3. 사례별 실행 결과

### A. route 2 직접 응답

```powershell
python main.py qwen-turn "오늘 테스트를 끝낸 나에게 한 문장으로 수고했다고 말해줘." --timeout 180 --compact --export ".songryeon_core_cache\order_273\case_a_route2"
```

- route path: `1:route=2 -> 0:final_trace_for_2`
- L run: `0`
- Vessel R: `not_run`
- node_4: `pass`
- 사용자 응답은 한 문장으로 생성됨

### B. L 내부 문서 원문

```powershell
python main.py qwen-turn "내부 문서 ORDER_270을 직접 읽고 direct Ollama timeout 정책을 짧게 설명해줘." --force-l --timeout 180 --compact --export ".songryeon_core_cache\order_273\case_b_l_document"
```

- route path: `L -> 2`
- L run: `1`
- 명시 문서 원문: `read_artifact`로 1개 확보
- L 최종 decision: `stop_success`
- L3: `goal=achieved / semantic=matched / execution=ran / failure=none`
- node_4: `pass`

### C. L workspace 코드 원문

```powershell
python main.py qwen-turn "workspace_policy.py를 직접 읽고 이 파일이 외부 업무 폴더 읽기 경계를 어떻게 제한하는지 설명해줘." --workspace "songryeon_core\tools" --force-l --timeout 180 --compact --export ".songryeon_core_cache\order_273\case_c_l_workspace_code"
```

- route path: `L -> 2`
- L run: `1`
- `read_code_file` 고유 파일/호출: `1/1`
- source-code context/outline: `1/1`
- L 최종 decision: `stop_success`
- L3: `goal=achieved / semantic=matched / execution=ran / failure=none`
- node_4: `pass`

### D. Vessel R 그래프 원문

```powershell
python main.py qwen-turn "Vessel R 그래프 기억에서 ORDER 090 L Loop Budget Plan을 찾아 요약 계층을 따라 RawSource 원문까지 확인하고 핵심을 설명해줘." --force-vessel-r-route --enable-vessel-r-route --database neo4j --timeout 180 --compact --export ".songryeon_core_cache\order_273\case_d_vessel_r_order090"
```

- 실행 시간: 약 `251.8초`
- route path: `R -> L -> 2`
- Vessel R read packet: `read_failed`
- failure stage/type: `read_packet / neo4j_read_failed`
- 원인: `localhost:7787` 연결 거부
- Vessel R node_3 material: `failed / 0개`
- R 실패 후 node_1이 L을 선택했고, L은 `read_doc` 원문 1개를 확보함
- L3: `goal=achieved / semantic=matched / execution=ran / failure=none`
- node_4: `pass`
- 최종 답변은 Neo4j 연결 실패를 숨기지 않고 L 문서 근거로 답함

따라서 Vessel R의 실제 탐색 성공 여부는 **환경 미확인**이다. 다만 R 실패를 숨기지 않고
L로 복구한 경로와 최종 공개 정직성은 확인됐다.

### E. 결정론적 공개 차단

```powershell
python main.py competition-demo
```

- LOCAL: `PASS`
- HONEST FALLBACK: `PASS`
- CODE GUARD: `PASS`
- 최종: `SONGRYEON_COMPETITION_DEMO_OK`

## 4. Neo4j 기동 진단

- Neo4j Desktop 프로세스는 실행 중이었으나 `7787` listener는 없었음
- 기존 Vessel 인스턴스 설정에서 Bolt port가 `7787`인 것은 확인함
- 시스템 기본 Java 11로 직접 상태 확인 시 Neo4j 2026.05.0 class version을 읽지 못함
- Neo4j Desktop에 포함된 Java 21로 기존 인스턴스를 두 차례 기동 시도함
- 두 번 모두 내부 RAFT port `7000` bind 충돌로 종료됨
- DB 설정과 데이터는 변경하지 않았으며, 포트나 cluster 설정도 임의 수정하지 않음

이 문제는 현재 코드의 R 탐색 로직 실패와 분리해야 한다.

## 5. 새로 발견한 상태 정합성 위험

사례 D의 L 복구 과정에는 초기 `read_artifact` 실패 뒤 revision `search_docs/read_doc` 성공이
함께 존재한다. 최신 L3 결과는 다음과 같다.

- L 검색 목표: `achieved`
- semantic: `matched`
- semantic execution: `ran`
- semantic failure: `none`
- 실제 `read_doc`: `1`

그러나 turn summary의 `l_loop_final_decision`은 초기 실패의 `stop_failed`로 남아 있었다.
즉 최신 revision 성공과 이름상 최종 decision이 충돌한다. 사용자 답변은 성공했지만,
downstream과 감사 화면이 어느 값을 최종 절대 상태로 볼지 불명확하다.

## 6. 다음 발주 후보

첫 번째 코드 발주 후보는 다음으로 좁힌다.

`ORDER_274_L_REVISION_FINAL_STATUS_RECONCILIATION_AUDIT_V0`

목표:

1. `l_loop_final_decision`, 최신 continuation, 최신 L3 achievement가 어느 record에서 집계되는지 감사한다.
2. 초기 실패 뒤 revision 성공 시 최종 상태가 stale failure로 남는 원인을 찾는다.
3. validator를 약화하거나 실패를 지우지 않고, 시도 이력과 최종 결과를 분리하는 작은 설계를 제시한다.

Neo4j `7000` 포트 충돌은 별도 운영 진단 후보로 남긴다. R 코드 변경과 한 발주에 섞지 않는다.

## 7. 검증 범위

- 제품 코드 변경: 없음
- `python main.py competition-demo`: 통과
- live qwen-turn: A/B/C/D 실행
- 전체 pytest/smoke: 제품 코드 변경이 없어 이번 감사에서 재실행하지 않음
- 캐시 export는 git 추적 대상에 포함하지 않음

