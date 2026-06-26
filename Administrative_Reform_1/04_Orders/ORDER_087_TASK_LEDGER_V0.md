# ORDER 087: Task Ledger v0

## 상태

구현 완료.

이 발주서는 아버지의 scheduler/task queue 구상을 바로 복잡한 병렬 실행으로 밀지 않고, 현재 순차 런타임을 task 단위 장부로 먼저 기록하기 위한 최소 구현이다.

## 배경

송련은 이미 노드와 루프가 나뉘어 있다.

현재 흐름은 대체로 다음과 같다.

```text
user
-> 0
-> 1
-> L
-> 0
-> 1
-> 0
-> 2
-> 3
-> 4
```

이 구조는 아직 순차 실행이다.

하지만 장기적으로는 다음 질문이 생긴다.

```text
어떤 작업은 동시에 실행해도 되는가?
어떤 작업은 반드시 앞 작업 결과를 기다려야 하는가?
어떤 노드는 어떤 모델/GPU/API worker에게 맡겨야 하는가?
실패한 작업은 어디서 다시 잡아야 하는가?
```

이 질문에 답하려면 먼저 노드 실행을 task로 볼 수 있어야 한다.

## 목표

현재 런타임의 실행 순서를 바꾸지 않고, 이미 생성된 `NodeMovement`를 `TaskFrame`과 `TaskResultFrame`으로 복사해 보존한다.

즉, Task Ledger v0의 목표는 다음이다.

```text
현재 순차 동선
-> task 장부
-> 미래 scheduler/task queue/worker 배정의 발판
```

## 구현 범위

### 1. 스키마

`TaskFrame`을 추가한다.

이 frame은 task의 선언에 해당한다.

주요 필드:

- `task_id`: task 고유 ID
- `turn_id`: 이 task가 속한 턴
- `step_index`: 현재 순차 실행에서 몇 번째 task인지
- `node_id`: 실행된 노드 또는 루프
- `task_kind`: node, loop 같은 실행 단위 종류
- `mode`: 실제 실행 모드
- `depends_on_task_ids`: 의존 task 목록
- `input_trace_ids`, `input_data_ids`: task 입력 근거
- `expected_output_trace_ids`, `expected_output_data_ids`: task가 만들 것으로 기록된 출력
- `assigned_model_id`: 배정된 모델 또는 코드 실행자
- `assigned_worker_id`: v0 worker 이름
- `scheduling_policy`: v0에서는 `sequential_v0`
- `status`: task 상태

`TaskResultFrame`을 추가한다.

이 frame은 task의 결과에 해당한다.

주요 필드:

- `result_id`: 결과 frame 고유 ID
- `task_id`: 대응 task ID
- `turn_id`: 이 결과가 속한 턴
- `status`: 실행 결과
- `output_trace_ids`, `output_data_ids`: 실제 출력
- `failure_type`, `failure_reason`: 실패 정보
- `committed_by`: 장부 반영 주체

### 2. 런타임 장부 기록

`record_task_ledger_from_movements`를 추가한다.

이 함수는 현재 턴의 `NodeMovement` 목록을 읽고, 각 movement에 대응하는 task/result record를 `DataStore`에 만든다.

v0의 의존 관계는 단순하다.

```text
첫 task: depends_on_task_ids = []
두 번째 task부터: depends_on_task_ids = [직전 task_id]
```

이는 병렬 실행을 아직 하지 않는다는 뜻이다.

### 3. 사용자 출력

터미널 runtime view에 task ledger 요약을 추가한다.

예:

```text
- task ledger: tasks=13 / results=13 / policy=sequential_v0 / worker=local_sync_worker
  - task:turn_dry_001:001 node_0:pre_route_report status=completed model=CODE:RULE_STUB
  - task:turn_dry_001:002 node_1:routing status=completed model=LLM:qwen3:14b
```

이 출력은 사용자가 "지금 송련이 어떤 노드 동선을 task로 봤는지" 확인하기 위한 학습/디버깅 표면이다.

### 4. smoke-test

smoke-test는 다음을 확인한다.

- task frame 수가 movement 수와 일치한다.
- task result 수가 movement 수와 일치한다.
- 모든 task가 `sequential_v0` 정책을 가진다.
- 모든 task가 `local_sync_worker` worker를 가진다.
- v0 의존 관계가 순차적으로 이어진다.

## 권한 경계

Task Ledger v0은 scheduler가 아니다.

다음을 하지 않는다.

- 실행 순서를 바꾸지 않는다.
- 병렬 실행하지 않는다.
- worker를 실제로 띄우지 않는다.
- GPU나 API 모델을 실제로 배정하지 않는다.
- trace/data commit 권한을 분산하지 않는다.

Task Ledger v0은 현재 실행 결과를 정직하게 장부화하는 단계다.

## 메타정보 원칙

Task Ledger v0이 기록하는 정보는 대부분 절대정보다.

예:

- 어떤 movement가 있었는가
- 어떤 trace/data ID를 입력과 출력으로 가졌는가
- 현재 장부상 몇 번째 task인가
- 어떤 scheduling policy로 기록됐는가

단, `assigned_model_id`는 실제 모델 호출 기록과 연결될 때만 강한 절대정보가 된다.

v0에서는 사람이 보기 위한 배정 라벨 성격도 있으므로, 나중에 실제 scheduler가 생기면 모델 배정 정책과 실제 호출 기록을 더 엄격히 연결해야 한다.

## 구현 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/runtime/task_ledger.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/runtime/user_turn.py`
- `songryeon_core/runtime/smoke_test.py`
- `main.py`

## 검증 기준

다음 명령이 통과해야 한다.

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
python main.py dry-run
python main.py fake-turn "송련의 task ledger가 무엇인지 보여줘" --pretty --force-l
```

## 다음 확장 후보

아직 바로 구현하지 않는다.

후보만 남긴다.

```text
1. SchedulerFrame 추가
2. task queue 자료구조 추가
3. L loop 내부 search/read task 분리
4. 독립 task 병렬 실행 가능 여부 표시
5. node별 model/worker 배정 정책 분리
6. local GPU worker와 API worker를 함께 쓰는 실행 정책
```

## 현재 결론

Task Ledger v0은 송련을 Agent Runtime OS로 키우기 위한 첫 코드 씨앗이다.

지금은 오직 "현재 순차 동선을 task로 볼 수 있게 만드는 것"만 성공 기준으로 삼는다.

