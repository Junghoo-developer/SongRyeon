# ORDER_203 Force Vessel R Route For Live Verification v0

## 목표

Vessel R live route를 Qwen 실사용 경로에서 직접 검증할 수 있도록 개발자 전용 강제 R 진입 옵션을 추가한다.

## 배경

ORDER_200 이후 `--enable-vessel-r-route`는 node_1이 route=R을 선택할 수 있게 허용한다. 하지만 이 플래그는 R을 강제하지 않는다.

ORDER_202 이후 확인해야 할 것은 node_3가 Vessel R material을 받았을 때 내부 graph node ID를 최종 답변에 노출하지 않는지다. 그런데 Qwen router가 route=L을 고르면 Vessel R material 경로를 직접 검증할 수 없다.

따라서 live 검증을 위해 `--force-vessel-r-route` 개발자 옵션을 둔다.

## 구현 범위

1. `fake-turn`, `qwen-turn`, `qwen-chat` 공용 옵션에 `--force-vessel-r-route`를 추가한다.
2. 이 옵션이 켜지면 node_1 LLM router를 건너뛰고 code policy decision으로 `route=R`을 기록한다.
3. 강제 R route frame에는 다음을 명시한다.
   - `route_source=CODE:POLICY_STUB`
   - `llm_routing_status=not_run`
   - `route_rule_id=force_vessel_r_route_policy`
   - `policy_flag=force_vessel_r_route`
4. `--force-vessel-r-route`는 Vessel R runtime을 effective enabled 상태로 만든다.
5. `--force-l`과 `--force-vessel-r-route`를 동시에 켜면 실패한다.

## 금지

- 자연어 router prompt를 휴리스틱으로 덧칠하지 않는다.
- Qwen이 R을 고른 것처럼 위장하지 않는다.
- R traversal depth/Neo4j schema/node_3/node_4 정책을 바꾸지 않는다.
- `--enable-vessel-r-route`의 의미를 “강제 R”로 바꾸지 않는다.

## 검증

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py
python main.py fake-turn "Vessel R 강제 테스트" --force-vessel-r-route --pretty
```

## 완료 기준

- 강제 R route가 CODE policy decision으로 기록된다.
- Vessel R material이 node_3까지 전달된다.
- node_4가 pass한다.
- 기존 `--enable-vessel-r-route` 경로가 깨지지 않는다.
