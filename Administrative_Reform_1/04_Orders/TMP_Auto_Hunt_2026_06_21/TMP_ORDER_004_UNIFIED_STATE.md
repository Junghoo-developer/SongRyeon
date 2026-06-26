# TMP ORDER 004: UnifiedState

**상태**: 임시 발주서  
**목표**: 0 이외의 노드와 루프가 공유하는 공용 state를 정의한다.  
**실행 권한**: 없음.

## 배경

0은 특수 state를 본다. 반면 1, 2, 3, L루프는 공용 state를 통해 현재 턴의 작업 상태를 공유한다.

## 만들 것

`UnifiedState`의 최소 필드를 정의한다.

```text
UnifiedState
- turn_id
- user_input
- current_route
- routing_reason
- trace_event_ids
- active_schema
- metainfo_boundary_id
- current_loop
- latest_failure_signal
```

## 필드 설명

```text
turn_id:
이번 턴을 구분하는 ID.

current_route:
1이 현재 선택한 라우팅 대상. 예: 2 또는 L.

active_schema:
현재 노드에 강제되는 스키마 정보. 스키마가 필요한지, 무엇인지, 통과했는지 기록한다.
```

## 완료 기준

- 0.state와 UnifiedState의 경계가 설명되어 있다.
- 모든 일반 노드가 최소한 무엇을 공유하는지 정리되어 있다.
- 스키마 적용 여부를 담는 칸이 있다.

## 제외

- 실제 상태 저장소 구현.
