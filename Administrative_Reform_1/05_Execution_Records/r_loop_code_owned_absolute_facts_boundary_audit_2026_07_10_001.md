# R-loop code-owned absolute facts 경계 감사

- 날짜: 2026-07-10
- 범위: R1 목표/예산, R2 후보 선택, R3 충분성 검사
- 성격: 코드 수정 없는 추가 감사
- 기준: 절대정보는 코드가 기록하고, LLM은 의미 목표·선택·충분성만 판단한다.

## 1. 결론

R-loop에는 이번 L3에서 발견된 것처럼 LLM이 후보 수나 읽기 수를 다시 세어
authoritative count를 덮는 치명적인 경계는 확인되지 않았다.

- R1의 상한 예산과 packet count는 code 입력이다.
- R2는 실제 graph ID 대신 `surface_001`, `node_001` 형식의 공식 번호표를 선택한다.
- code가 R2 번호표를 실제 graph ID로 복원하고 후보 소속을 검증한다.
- R3의 child ID/count, summary depth, source leaf count는 code가 frame에 쓴다.
- R3 LLM은 충분성, 정보 농도 문제, 가지 문제, 다음 행동만 판단한다.

따라서 R-loop는 현재 즉시 고쳐야 할 절대 count 오염보다, 불필요한 내부 ID를
입력에서 더 줄이는 후속 정리 후보가 남아 있는 상태다.

## 2. 잘 잠긴 경계

### R1 목표와 예산

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:1620`
- 현재 분류: packet count와 최대 예산은 absolute, 검색 목표와 최소 예산 선택은 mixed.
- 판단: 적절하다.
- 근거: R1은 후보 본문과 후보 ID를 받지 않고 구조 primer와 count만 받는다.
  최소 탐색 깊이·최소 읽기 수는 사용자 질문을 바탕으로 한 정책 판단이므로 LLM
  책임으로 둘 수 있고, code validator가 최대값을 넘지 못하게 막는다.
- 수정 위험도: 낮음.
- 조치: 유지.

### R2 공식 번호표 선택

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:4404`, `:4445`, `:2554`
- 현재 분류: 후보 표와 번호표 대응은 absolute, 후보 선택 이유는 mixed.
- 판단: 적절하다.
- 근거: actual graph ID와 summary text를 후보 카드에서 제거하고, R2는 공식 ref만
  선택한다. code는 ref를 실제 ID로 복원한 뒤 현재 후보 목록 및 선택 surface 소속을
  모두 검사한다.
- 수정 위험도: 낮음.
- 조치: 유지.

### R3 구조 사실과 의미 판단 분리

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:2120`, `:2624`, `:3148`
- 현재 분류: child ID/count, depth, leaf count는 absolute. 충분성·가지·농도 판단은 mixed.
- 판단: 적절하다.
- 근거: R3 output에 count나 child ID를 생성시키지 않는다. frame의 구조 필드는
  selected record에서 code가 복사하며, 자식이 없으면 `deeper`를 validator가 막는다.
- 수정 위험도: 낮음.
- 조치: 유지.

## 3. 발견 사항

### [중간] R1이 code anchor ID를 직접 복사한다

- 위치: `songryeon_core/prompts/r1_vessel_goal_setter_v0.md:15`,
  `songryeon_core/loops/r_loop_vessel_one_step.py:2551`
- 현재 분류: LLM 출력 frame 안의 absolute copy field.
- 실제로 맞아 보이는 분류: code-owned absolute field.
- 이유: `user_question_anchor_id`는 의미 판단이 아니라 code가 이미 만든 동일성 표다.
  LLM이 틀리면 validator가 정직하게 실패시키므로 잘못 저장되지는 않지만, 불필요한
  schema failure가 생길 수 있다.
- 수정 위험도: 중간. R1 schema와 기존 테스트 계약을 함께 바꿔야 한다.
- 조치: 별도 발주서 논의 후 code assembly로 옮길 수 있다.

### [중간] R2의 “actual graph ID 숨김” 선언과 입력 payload가 완전히 일치하지 않는다

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:1812`, `:1833`, `:1834`, `:1837`
- 현재 분류: provenance용 absolute ID가 LLM 입력에도 노출됨.
- 실제로 맞아 보이는 분류: DataStore에는 absolute로 보존하되 R2 LLM 보기에서는 제외.
- 이유: 선택 후보의 actual graph ID는 실제로 숨겨지지만, `current_graph_node_id`,
  `read_packet_id`, R1 frame의 source IDs는 여전히 입력에 있다. 선택 결과 검증에는
  필요하지 않은 문자열이며 prompt의 “actual graph IDs hidden” 문장과도 어긋난다.
- 수정 위험도: 중간. repair payload와 이전 단계 memory view까지 함께 확인해야 한다.
- 조치: 즉시 기능 패치보다 R2 LLM view projection 발주서가 적합하다.

### [낮음] R1에도 packet 내부 ID가 의미 입력과 함께 들어간다

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:1639`, `:1678`
- 현재 분류: provenance absolute ID가 LLM 입력에 포함됨.
- 실제로 맞아 보이는 분류: runtime/DataStore에만 보존할 absolute field.
- 이유: R1은 packet count와 구조 primer만 있으면 목표를 세울 수 있다. packet ID를
  출력하지 않으므로 현재 오염은 없지만 입력 토큰과 주의 분산을 늘린다.
- 수정 위험도: 낮음.
- 조치: R payload projection 작업 때 함께 제거 가능.

### [낮음/설계 논의] 비-raw 재료의 current granularity는 아직 LLM이 고른다

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:2439`, `:3169`
- 현재 분류: R3 mixed 판단 안의 enum.
- 실제로 맞아 보이는 분류: 정책 정의에 따라 mixed 또는 code-owned absolute policy result.
- 이유: RawSource 원문이 있으면 code가 `raw` 하나만 허용한다. 하지만 summary node는
  summary depth가 이미 code fact여도 low/medium/high mapping을 LLM이 고를 수 있다.
  depth-to-granularity 공식 정책이 아직 없다면 현재 처리가 맞고, 정책을 정의하면
  code가 고정할 수 있다.
- 수정 위험도: 중간.
- 조치: 휴리스틱으로 즉시 고정하지 말고 granularity 정책을 먼저 결재한다.

### [낮음] R3 의미 입력에 실제 child/provenance ID가 남아 있다

- 위치: `songryeon_core/loops/r_loop_vessel_one_step.py:2161`, `:2190`, `:3241`
- 현재 분류: absolute 구조/provenance 입력.
- 실제로 맞아 보이는 분류: code frame에는 보존하되 LLM에는 구조 count와 안전 ref만 공급.
- 이유: R3는 ID를 출력하지 않아 authoritative 오염은 없지만, 긴 Neo4j ID와 source ID는
  충분성 이유문을 산만하게 만들 수 있다.
- 수정 위험도: 중간. child preview와 raw source 원문 경계를 깨지 않게 줄여야 한다.
- 조치: R3 compact semantic view 후속 후보.

## 4. 권고 순서

1. ORDER 249를 먼저 검증해 L3/node_2의 실제 실패를 닫는다.
2. R-loop는 현재 기능을 수정하지 않는다.
3. 후속 필요 시 `R1 anchor code assembly + R1/R2/R3 semantic payload projection`을
   하나의 작은 발주서로 설계한다.
4. summary depth와 information granularity의 대응 정책은 별도 인간 결재 없이는
   code 규칙으로 만들지 않는다.

## 5. 금지 확인

- 단어 휴리스틱 추가 없음
- R1/R2/R3 의미 판단을 code가 대신하지 않음
- R route, traversal budget, Neo4j graph 변경 없음
- validator 약화 없음
