# SongRyeon Core v1

송련 코어 v1은 **LLM이 만든 내용과 코드가 확인한 사실을 구분해 기록하고,
그 기록을 제한된 에이전트 시야로 제공하는 구조**를 먼저 만드는 중입니다.

현재 단계에는 기억, 외부 지식 색인, 읽기 전용 파일 도구, 네 노드 라우팅과
로컬 Ollama `qwen3:14b`로 한 턴을 끝까지 실행하는 데모가 있습니다.

송련이 보장하려는 범위는 세상 모든 정보의 진실성이 아닙니다. 내장 실행
경로에서 **LLM이 코드로 확인 가능한 실행 사실을 직접 작성하거나 바꾸지
못하게 하는 것**이 현재의 경계입니다. 모델과 사용자의 해석은 끝까지
상대정보로 남습니다.

프로젝트는 [MIT License](LICENSE)로 공개합니다. 모델과 로컬 런타임의
출처는 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), 재현 환경은
[`docs/reproducibility.md`](docs/reproducibility.md)에 기록합니다.

## 폴더 구조

```text
SongRyeon_Core_v1/
├─ memory/
│  ├─ settings.py       # 원본 경로와 에이전트 시야 정책
│  ├─ record.py         # 7필드 원자 기록 생성
│  ├─ store.py          # memory.jsonl 누적 저장
│  ├─ agent_view.py     # 공개 5필드, 최초 8,000자와 턴 기준점
│  ├─ tool_records.py   # 도구 원문과 Node1 선택 기록
│  ├─ tool_source.py    # 숨김 원문 ID·turn·A 무결성 재검사
│  ├─ gate_records.py   # Node1 라우팅과 Node2·Node4 적용 기록
│  ├─ conversation_records.py # 사용자 입력·Node3 답변·최종 선택
│  ├─ model_records.py  # 숨김 모델 prompt·response 원본
│  └─ memory.jsonl      # 에이전트 기억의 원본 로그
├─ agent_tools/
│  ├─ result.py         # 모든 파일 도구의 공통 결과 형식
│  └─ files.py          # .py 이름 보기와 안전한 원문 열람
├─ nodes/
│  ├─ retention.py      # 짧은 원문 선택, 긴 원문 청크와 정확한 복사
│  ├─ recovery.py       # 전부 omit됐을 때 복구할 후보 번호
│  ├─ actions.py        # Node1 도구/라우팅 행동
│  ├─ review.py         # Node2·Node4 permit/reject
│  ├─ schemas.py        # 네 노드 JSON Schema
│  └─ parsing.py        # 모델 JSON의 엄격한 검증
├─ llm/
│  ├─ client.py         # 표준 라이브러리 Ollama HTTP 연결
│  └─ structured.py     # 제한 재요청과 모델 원문 기록
├─ prompts/
│  ├─ shared.py         # 공통 A/R 규칙
│  └─ node1.py ... node4.py # 노드별 최소 역할
├─ runtime/
│  ├─ state.py          # 턴 카운터와 결과 형식
│  ├─ tool_flow.py      # Node1 도구 3회와 원문 선택 흐름
│  ├─ retention_recovery.py # Node2 직전 전부 omit 복구
│  ├─ gates.py          # Node2·Node4 반려 3회와 라우팅
│  ├─ node_calls.py     # 각 노드의 모델 호출
│  └─ runner.py         # 네 노드 전체 턴
├─ demo/
│  └─ cli.py            # 사용자 입력과 진행 화면
├─ knowledge/
│  ├─ settings.py       # DB·문서 경로와 허용 파일 종류
│  ├─ source_files.py   # 파일 탐색·UTF-8 읽기·hash 계산
│  ├─ database.py       # SQLite 저장과 조회
│  ├─ memory_log.py     # 지식 한 버전을 원본 로그에 보존
│  ├─ indexer.py        # 파일·DB·원본 로그의 동기화 순서
│  ├─ documents/        # 외부 문서를 넣는 곳
│  └─ knowledge.db      # 검색용 지식 색인
├─ tests/
│  └─ ...               # 실제 책임 폴더와 같은 구조의 테스트
├─ evals/
│  ├─ schema.py          # 비교평가 입력·결과의 모델 독립 형식
│  ├─ evaluator.py       # A 실행사실·근거 없는 코드 주장 판정
│  └─ summary.py         # 시스템별 완료율·정확도·비용 집계
├─ docs/
│  ├─ minimal_agent_loop.md # 결정론적 기반의 자세한 설명
│  ├─ demo_walkthrough.md   # 실제 데모를 읽는 학습 순서
│  ├─ evaluation_plan.md    # 비교 실험의 고정 규칙
│  └─ reproducibility.md    # 실행 환경과 모델 식별 정보
├─ metadata/            # 예전 import가 깨지지 않게 남긴 호환 파일
├─ pyproject.toml       # 패키지·CLI·pytest 설정
└─ README.md
```

`Agent_memory.py`, `knowledge_store.py`, `knowledge_log.py`도 예전 코드를 위한
호환 파일입니다. 새 기능은 이 파일에 추가하지 않고 각각
`agent_view.py`, `indexer.py`, `memory_log.py`에 작성합니다.

## 기억이 흐르는 순서

```text
입력
  ↓
memory/record.py
7필드 원자 기록 생성
  ↓
memory/store.py
memory/memory.jsonl에 원본 누적
  ↓
memory/agent_view.py
숨김 기록 제외 + 공개 4필드에 파생 memory_index 추가
턴 시작 시 최신 8,000자의 가장 오래된 원자를 기준점으로 고정
턴 중에는 기준점부터 새 공개 원자까지 계속 유지
  ↓
에이전트가 실제로 보는 기억
```

중요한 구분은 다음과 같습니다.

- `memory.jsonl`은 ID, 시각, 턴까지 가진 **원본**입니다.
- `load_agent_memory()`는 턴을 시작할 때 최신 8,000자 구간을 고릅니다.
- `memory_index`는 원본 JSONL의 줄 번호에서 파생하며 원본 7필드에는
  저장하지 않습니다.
- 데모 턴은 그 구간의 가장 오래된 원자 ID를 내부 기준점으로 고정하며,
  턴이 끝날 때까지 기준점을 앞으로 옮기지 않습니다.
- 모든 노드는 현재 턴 시작 `memory_index`와 직전 사용자 입력 하나를
  별도로 받아 과거 판단을 현재 지시로 오해하지 않게 합니다.
- `knowledge_*`, `tool_raw_*`, `model_raw_*` 기록은 원본에 보존되지만
  시야에서는 숨습니다.
- 테스트는 임시 폴더를 사용하므로 실제 `memory.jsonl`과 `knowledge.db`를
  변경하지 않습니다.
- 실제 `memory/memory.jsonl`은 개인정보가 섞일 수 있어 Git과 배포
  패키지에서 제외합니다.

## 추천 학습 순서

처음에는 아래 순서대로 읽으면 데이터가 이동하는 방향을 따라갈 수 있습니다.

1. `tests/memory/test_record.py`와 `memory/record.py`
2. `tests/memory/test_store.py`와 `memory/store.py`
3. `tests/memory/test_agent_view.py`와 `memory/agent_view.py`
4. `knowledge/settings.py`와 `knowledge/source_files.py`
5. `knowledge/database.py`와 `knowledge/memory_log.py`
6. `tests/knowledge/test_indexer.py`와 `knowledge/indexer.py`
7. `tests/agent_tools/test_files.py`와 `agent_tools/files.py`
8. `tests/nodes/test_decisions.py`와 `nodes/retention.py`
9. `nodes/actions.py`와 `nodes/review.py`
10. `tests/memory/test_tool_observation.py`와 `memory/tool_records.py`
11. `tests/memory/test_tool_retention.py`와 `memory/tool_source.py`
12. `tests/runtime/test_tool_flow.py`와 `runtime/tool_flow.py`
13. `runtime/retention_recovery.py`와 `nodes/recovery.py`
14. `tests/runtime/test_gates.py`와 `runtime/gates.py`
15. `nodes/schemas.py`와 `nodes/parsing.py`
16. `llm/client.py`와 `llm/structured.py`
17. `runtime/node_calls.py`와 `runtime/runner.py`
18. `demo/cli.py`

현재 에이전트 골격의 흐름과 A/R 기록은
[`docs/minimal_agent_loop.md`](docs/minimal_agent_loop.md)에 따로 설명했습니다.
실제 데모는 [`docs/demo_walkthrough.md`](docs/demo_walkthrough.md)의 순서로
읽으면 됩니다.

## 실행 방법

먼저 프로젝트와 테스트 도구를 설치합니다.

```powershell
python -m pip install -e ".[test]"
```

프로젝트 폴더에서 전체 테스트를 실행합니다.

```powershell
python -m pytest -q
```

로컬 Ollama와 설치된 `qwen3:14b`로 한 턴을 실행합니다.

```powershell
python -m demo "nodes/review.py를 실제 도구로 읽고 역할을 설명해 줘."
```

질문을 생략하면 대화형 화면이 열립니다. 기본 실행은 실제
`memory/memory.jsonl`에 모든 원본을 추가합니다. 별도 시험 로그를 쓰려면
`--memory .\tmp\demo-memory.jsonl`을 지정합니다.

실제 소스 코드와 `knowledge/documents/`의 문서를 동기화할 때만 아래 명령을
사용합니다. 이 명령은 실제 `knowledge.db`와 `memory.jsonl`을 갱신합니다.

```powershell
python -m knowledge
```

개별 `.py` 파일을 직접 실행하기보다 `python -m ...` 형태를 사용하면
패키지 import가 어느 운영체제에서도 같은 방식으로 동작합니다.

기여할 때는 [`CONTRIBUTING.md`](CONTRIBUTING.md)의 문제→테스트→최소 변경
순서를 따릅니다. 평가 숫자는 고정 fixture와 원시 결과로 재현되기 전에는
README에 싣지 않습니다.
