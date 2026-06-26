# ORDER 057: ZeroState Read Window Policy

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 0 기억공급관의 입력 범위 확정 필요  
**목표**: 0이 최근 대화, 이전 턴 capsule, 현재 trace를 어떤 범위와 순서로 읽는지 정책화한다.

## 배경

0은 사용자 입력 직후, 라우팅 직후, 루프 복귀 직전, 2 전달 직전에 반복 호출된다.  
하지만 0이 매번 모든 기억을 읽으면 비효율적이고, 너무 적게 읽으면 맥락을 놓친다.

## 범위

1. `ZeroReadWindowFrame` 또는 동등한 설정 구조를 만든다.
2. 최근 원본 대화 N턴, 이전 capsule M개, 현재 턴 trace 범위를 명시한다.
3. 호출 mode별 read window를 다르게 설정한다.
4. 읽은 source trace/data ID를 memory packet에 남긴다.
5. read window 초과 정보는 요약이나 검색 루프로 넘긴다.

## 원칙

1. 0은 기억을 창조하지 않는다.
2. 0이 읽은 범위는 추적 가능해야 한다.
3. mode마다 필요한 기억 밀도가 다르다.

## 완료 기준

1. 0 호출마다 read window 정보가 기록된다.
2. `pre_route_report`, `targeted_memory_supply`, `loop_return_summary`, `final_trace_for_2`가 서로 다른 read policy를 가질 수 있다.
3. memory packet source ID가 read window와 일치한다.
4. smoke test가 read window 기록을 확인한다.
