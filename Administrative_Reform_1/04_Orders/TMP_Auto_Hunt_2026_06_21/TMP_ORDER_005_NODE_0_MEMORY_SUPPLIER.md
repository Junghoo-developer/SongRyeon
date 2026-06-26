# TMP ORDER 005: Node 0 Memory Supplier

**상태**: 임시 발주서  
**목표**: 0 기억공급관의 호출 모드와 출력 형식을 정한다.  
**실행 권한**: 없음.

## 배경

0은 단일 첫 노드가 아니라 턴 곳곳에 끼어드는 LLM 기억공급 노드다. 사용자 입력 직후, 라우팅 직후, 루프 복귀 직전, 1이 2로 넘기기 직전에 호출된다.

## 호출 모드

```text
pre_route_report:
사용자 입력 직후 1에게 상황을 보고한다.

targeted_memory_supply:
1의 라우팅 이유와 대상 특성에 맞춰 기억을 공급한다.

loop_return_summary:
루프가 끝난 뒤 1이 보기 좋게 trace를 압축한다.

final_trace_for_2:
1이 2로 보내기 직전에 이번 턴 trace와 성패 판정을 정리한다.
```

## 출력

```text
MemoryPacketFrom0
- target
- purpose
- recent_context
- current_turn_flow
- candidate_queries
- loop_result_summary
- known_limits
- trace_evidence_ids
- insufficient_signal
```

## 중요한 규칙

1. 0은 기억을 지어내지 않는다.
2. 접근할 수 없는 기억은 `insufficient_signal`로 선언한다.
3. 1의 라우팅 이유가 0의 기억 절단 기준이 된다.
4. 2에게 넘기는 최종 trace에는 턴 성패 판정이 포함될 수 있다.

## 완료 기준

- 0의 호출 모드가 정의되어 있다.
- 각 모드가 언제 호출되는지 설명되어 있다.
- 0의 출력이 대상별로 구분되어 있다.

## 제외

- 실제 LLM 프롬프트 작성.
- 코드 구현.
