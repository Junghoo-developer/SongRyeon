# ORDER_203 Force Vessel R Route For Live Verification 실행 기록

## 실행 일시

2026-07-06

## 문제

`--enable-vessel-r-route`는 Vessel R route를 허용하지만 강제하지 않는다.

ORDER_202 live 확인 중 Qwen node_1 router가 route=L을 선택해, Vessel R material이 node_3까지 전달되는 경로를 직접 검증하지 못했다.

## 판단

자연어 router를 급하게 수정하면 휴리스틱 덧칠이 될 위험이 있다.

따라서 live 검증용으로 명시적인 developer flag를 추가하고, 이 결정은 LLM 판단이 아니라 code policy decision으로 기록한다.

## 구현

- `--force-vessel-r-route` CLI 옵션을 추가했다.
- `run_fake_user_turn`, `run_qwen_user_turn`, `run_dry_turn`에 force flag를 연결했다.
- node_1 code router가 `route=R`을 생성할 수 있게 했다.
- `RoutingDecisionFrame` validator가 강제 R policy를 LLM R policy와 구분해 허용하도록 했다.
- fake runtime 테스트를 추가했다.

## 검증 결과

```powershell
python -m compileall songryeon_core main.py
# 통과

python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py
# 4 passed

python -m pytest tests/test_order_198_r_vessel_return_packet.py tests/test_order_199_r_vessel_answer_demo_route.py tests/test_order_201_r2_granularity_and_vessel_r_display.py
# 11 passed

python main.py qwen-turn --help
# --force-vessel-r-route 옵션 노출 확인

python main.py smoke-test
# SMOKE_TEST_OK
```

## 참고

Neo4j가 연결되지 않은 CLI 환경에서 `fake-turn --force-vessel-r-route`를 실행하면 route=R 강제 frame은 기록되지만, Vessel R material은 adapter unavailable/read failed로 닫힐 수 있다. 실제 live 검증은 사용자의 로컬 `.env.vessel.local.ps1`을 주입한 PowerShell 세션에서 수행한다.
