# 송련 코어

송련 코어는 로컬에서 실행되는 작은 에이전트 런타임 실험 프로젝트다.

이 프로젝트의 핵심 질문은 하나다.

> LLM 기반 에이전트가 자신이 무엇을 코드로 확인했고, 무엇을 해석했으며, 어떤 근거 묶음으로 판단했는지 정직하게 설명할 수 있을까?

송련 코어는 모든 출력 문장을 같은 종류로 취급하지 않는다.
대신 런타임 정보를 다음처럼 나눈다.

- **절대정보**: 코드, 스키마, 파일, trace event, data record로 존재와 값을 확인할 수 있는 정보.
- **상대정보**: 하나의 특정 source record 또는 field에 직접 대응하는 의미 판단.
- **혼합정보**: 하나의 source로 못 박으면 부정확한, 여러 source 묶음에 근거한 종합 판단.

이 저장소는 일부러 작게 만든 연습판이다.
더 큰 개인 비서나 에이전트를 만들기 전에, trace, 근거, 라우팅, LLM 판단을 어떻게 정직하게 다룰지 실험하는 코어다.

## 왜 만들었나

많은 에이전트 데모는 처음 보면 그럴듯하다.
하지만 조금만 파고들면 이런 질문이 나온다.

- 이 말은 코드가 확인한 사실인가, LLM이 해석한 말인가?
- 최종 답변은 어떤 내부 단계에서 나온 것인가?
- LLM 라우터가 실패했는데 코드 fallback이 조용히 대신 판단한 것은 아닌가?
- L 루프가 두 번 돌았을 때 최신 run을 보고 있는가, 예전 기록을 보고 있는가?
- 최종 답변에 나온 숫자는 LLM이 센 것인가, 코드가 센 것인가?

송련 코어는 이런 문제를 schema, trace record, runtime label, smoke-test로 분리해서 다룬다.

## 현재 가능한 것

- `node_0`, `node_1`, `L loop`, `node_2`, `node_3`, `node_4` 기반 런타임 골격.
- TraceStore와 DataStore를 통한 사건/데이터 출처 추적.
- 내부 문서 검색과 근거 수집을 위한 L 루프.
- 최종 보고서의 grounding count를 code가 고정 생성.
- 라우터 fallback 정직성 기록.
- same-turn L reroute guard.
  - 기본값은 L 1회.
  - 정책을 켜면 L 2회.
  - 3회차 이상은 차단.
- 최근 턴 capsule과 raw conversation alignment packet.
- 상대정보/혼합정보 분리 및 smoke-test.
- pretty runtime 출력에서 생성자, 정보 등급, source ID, 의미 판단 상태 표시.

## 폴더 구조

- `songryeon_core/core/`: schema, trace store, data store, registry, failure signal.
- `songryeon_core/state/`: zero state, unified state, turn capsule helper.
- `songryeon_core/nodes/`: node 구현.
- `songryeon_core/loops/`: L loop runtime과 loop policy.
- `songryeon_core/tools/`: 문서 도구, hash embedding 검색, tool result distillation.
- `songryeon_core/llm/`: LLM adapter, fake adapter, Qwen/Ollama adapter.
- `songryeon_core/runtime/`: dry run, user turn, terminal view, smoke test, replay.
- `songryeon_core/prompts/`: node별 prompt 파일.
- `Administrative_Reform_1/`: 설계 문서, 지도, 발주서, 실행 기록.
- `main.py`: CLI 진입점.

## 빠른 실행

기본 smoke-test는 Python 표준 라이브러리만으로 실행된다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

기대 결과:

```text
SMOKE_TEST_OK
```

실제 LLM 없이 deterministic fake turn 실행:

```powershell
python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇인지 알려줘" --pretty
```

dry run 실행:

```powershell
python main.py dry-run
```

## 선택 기능: 로컬 LLM

Qwen 경로는 선택 기능이다.
Ollama와 호환 모델이 있으면 다음처럼 실행할 수 있다.

```powershell
pip install ollama
python main.py qwen-ping --timeout 60
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇인지 알려줘" --timeout 120 --pretty
```

`QWEN_LOCAL_ENDPOINT`를 OpenAI 호환 로컬 HTTP endpoint로 지정해서 쓸 수도 있다.

## 설계 원칙

1. 절대정보는 코드가 쓴다.
2. 의미 판단은 LLM이 쓴다.
3. 혼합정보는 source bundle을 드러낸다.
4. 코드는 LLM인 척하지 않는다.
5. LLM 판단을 코드 사실처럼 보여주지 않는다.
6. 휴리스틱은 숨기지 않고 명시적 정책으로 둔다.
7. smoke-test 없는 데모 감성에 속지 않는다.

## 현재 기준선

2026-06-26 기준:

- `python -m compileall songryeon_core main.py` 통과.
- `python main.py smoke-test` 통과.
- 하나의 source field에 직접 대응하는 claim은 relative info로 테스트됨.
- source bundle 기반 planner claim은 mixed info로 유지됨.
- node_3 report grounding count는 code가 공급함.
- node_4는 위험하거나 count가 맞지 않는 report를 차단할 수 있음.

## 참고

이 프로젝트는 production assistant가 아니다.

송련 코어는 provenance, runtime honesty, agent self-reporting을 공부하기 위한 학습형 아키텍처 프로토타입이다.
겉보기에 화려한 데모보다, 기록이 남고 검증 가능한 작은 MVP를 우선한다.
