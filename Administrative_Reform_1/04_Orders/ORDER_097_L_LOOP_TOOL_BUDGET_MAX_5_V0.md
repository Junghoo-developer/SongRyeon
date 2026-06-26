# ORDER 097: L Loop Tool Budget Max 5 v0

## 목적

L루프의 기본 도구 호출 예산과 정책 상한을 5회로 맞춘다.

이번 발주서는 L루프 실행 횟수 재라우팅 정책을 바꾸지 않는다.
`same_turn_l_reroute`의 최대 실행 횟수는 `ORDER_096` 기준을 유지한다.

## 변경 범위

- 런타임 기본 `max_tool_calls`를 5로 올린다.
- L 예산 정책의 `MAX_TOOL_CALLS_CEILING`을 5로 둔다.
- 직접 `run_l_loop()`를 호출할 때의 기본값도 5로 맞춘다.
- smoke-test의 기본 도구 예산 기대값을 5로 갱신한다.

## 정책

코드는 도구 예산 숫자만 조정한다.

다음은 이번 범위가 아니다.

- 같은 턴 L 재진입 횟수 증가.
- `read_doc` 정책 상한 증가.
- `search_top_k` 정책 상한 증가.
- L1/L2/L3 의미 판단 변경.

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```
