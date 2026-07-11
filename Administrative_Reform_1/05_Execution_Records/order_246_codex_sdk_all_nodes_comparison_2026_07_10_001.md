# ORDER 246 실행 기록

- 날짜: 2026-07-10
- 결과: ChatGPT Pro 기반 Codex SDK all-node 한 턴 성공
- 발주서: `ORDER_246_CODEX_SDK_ALL_NODES_COMPARISON_ADAPTER_V0.md`

## 구현

- `codex-sdk-turn`, `codex-sdk-chat` 명령을 추가했다.
- 같은 `CodexSDKAdapter` app-server를 한 송련 턴 동안 공유한다.
- 각 송련 LLM node는 별도 ephemeral Codex thread를 사용한다.
- API key fallback 없이 ChatGPT auth type만 허용한다.
- 빈 임시 cwd, read-only sandbox, deny-all approval을 사용한다.
- node 결과 transport는 `payload_json` wrapper schema로 고정한다.
- 기록된 command/file/MCP/web/image tool item이 있으면 응답을 채택하지 않는다.
- 성공/실패 모두 adapter와 임시 폴더를 닫는다.

## 실제 all-node 시험

- 입력: `송련 Core가 무엇인지 두 문장으로 설명해줘`
- 모델: `gpt-5.4`
- reasoning effort: low
- status: ok
- route sequence: `L -> 2`
- Codex turns: attempted 10 / completed 10 / accepted 10
- SDK tool activity: 0
- trace/data: 64 / 104
- node_4: pass
- 실행 시간: 약 138.5초
- total tokens: 206,074

최종 답변은 송련 Core를 모델 자체를 키우는 엔진이 아니라 근거·count·trace·실패
상태·gate를 드러내는 runtime 구조로 설명했고, 직접 정의 문서 확보가 부족하다는
한계도 함께 표시했다.

## 자동 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 245-246 좁은 pytest: `5 passed`
- 전체 pytest: `406 passed, 5 deselected`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

## 남은 위험

- 짧은 질문도 Codex agent 기본 문맥 때문에 token/시간 overhead가 매우 크다.
- read-only/deny-all과 사후 tool activity guard를 적용했지만, 현 MVP는 Codex의
  agent runtime을 호출하므로 raw model API와 동일한 비교는 아니다.
- `codex-sdk-chat`은 수동 비교용이며 자동 기본 경로로 사용하지 않는다.
