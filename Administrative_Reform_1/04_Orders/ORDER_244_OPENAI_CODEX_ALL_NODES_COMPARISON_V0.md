# ORDER 244: OpenAI Codex All-Nodes Comparison v0

## 상태

- Status: implemented; live response blocked by API quota
- Date: 2026-07-10
- Scope: external OpenAI Responses adapter / all-node injection / Qwen comparison

## 배경

현재 송련 Core의 실제 LLM 경로는 로컬 Qwen/Ollama adapter를 공통
`LLMAdapter` 경계에 주입한다. 모델 자체의 한계와 송련 구조의 효과를 분리하려면
같은 노드, 프롬프트, schema, 도구 예산에 더 큰 외부 모델을 주입한 비교가 필요하다.

## 목표

- OpenAI Responses API adapter를 기존 공통 LLM 경계에 추가한다.
- node_1, memory selector, L1/L2/L3, node_2/3/4와 선택된 R 경로가
  하나의 외부 adapter를 공유하게 한다.
- 전체 턴 전 `openai-ping` 한 번으로 키/모델/API 연결을 좁게 확인한다.
- Qwen 명령과 OpenAI 명령을 분리해 의도하지 않은 외부 과금을 막는다.
- 키 원문은 trace, DataStore, terminal, 실행 기록에 남기지 않는다.
- API 호출 수와 token usage는 코드가 확인한 절대정보로 표시한다.

## 명령 경계

- `openai-ping`: API 1회 연결 검사
- `openai-turn`: 외부 adapter로 한 턴 실행
- `openai-chat`: 같은 adapter를 사용하면서 최근 대화/capsule 세션을 잇는 수동 실험

기본 모델은 `gpt-5.3-codex`이며 사용자가 `--model-id`로 명시 변경할 수 있다.

## 정직성 경계

- OpenAI 실패를 Qwen이나 code 의미 fallback으로 조용히 대체하지 않는다.
- 키 설정 여부만 boolean으로 기록하고 키 문자열은 기록하지 않는다.
- 외부 모델이 쓴 판단의 `generated_by=LLM:*` 경계는 기존 node별 기록을 유지한다.
- OpenAI 모델의 출력 품질과 송련 구조의 성과를 동일한 것으로 단정하지 않는다.

## 하지 않는 것

- 기존 Qwen/Ollama 기본 경로 제거
- node prompt/schema/라우팅 정책 변경
- L/R 예산 또는 same-turn reroute 변경
- Codex SDK로 파일 수정 권한 부여
- 웹 검색, shell, 코드 쓰기 도구를 외부 모델에 개방
- API 키를 코드나 Git 추적 파일에 저장

## 완료 조건

- key missing 상태가 정직하게 `config_missing`으로 닫힌다.
- adapter가 Responses API JSON mode를 사용하고 `store=false`를 보낸다.
- usage count가 키/원문 없이 집계된다.
- `openai-ping`이 실제 계정에서 성공 또는 구조화된 API 실패를 반환한다.
- 좁은 pytest, compileall, 기존 quick-smoke가 통과한다.
- 가능한 경우 짧은 `openai-turn`을 한 번 실행해 all-node 연결을 확인한다.

## 2026-07-10 구현 결과

- 공통 adapter, 세 CLI 명령, key 비노출, usage 집계를 구현했다.
- 외부 호출 없는 all-node 주입 검증은 통과했다.
- 실제 `gpt-5.3-codex` ping은 OpenAI 서버까지 도달했으나 계정이
  `insufficient_quota`를 반환해 모델 답변 생성과 live all-node 턴은 보류했다.
- API billing/quota가 열린 뒤 같은 ping을 재실행하고 성공할 때만
  `openai-turn` 비교를 진행한다.
