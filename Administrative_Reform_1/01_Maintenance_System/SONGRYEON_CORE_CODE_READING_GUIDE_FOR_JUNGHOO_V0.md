# 송련 Core 실제 코드 독해 교재 v0

- 대상: 송련 Core 개발자 정후
- 기준 체크포인트: `a2dc780`
- 작성일: 2026-07-23
- 목적: 코드를 외우는 것이 아니라, 한 턴이 어디서 시작해서 어떤 근거를 남기고 어떻게 공개되는지 설명할 수 있게 한다.

---

## 0. 이 교재를 2시간 동안 사용하는 법

이 문서를 처음부터 끝까지 한 번에 외우려고 하지 않는다.

1. 먼저 `전체 지도`를 10분 동안 읽는다.
2. 각 장의 `진짜 코드`를 소리 내어 읽는다.
3. 코드 아래의 `한 줄씩 읽기`와 원문을 번갈아 본다.
4. 각 장 끝의 `내 말로 설명하기`에 답한다.
5. 마지막 20분에는 터미널에서 직접 파일을 열고 같은 코드를 찾는다.

오늘의 합격 기준은 다음 한 문장을 자기 말로 설명하는 것이다.

> 송련은 LLM의 답을 바로 공개하지 않고, 사건 장부와 데이터 장부를 남긴 뒤,
> 0이 근거 좌표를 공급하고, 1이 경로를 선택하고, 2가 근거의 역할을 정리하며,
> 3이 답변을 쓰고, 4와 CODE guard가 공개 가능 여부를 검사한다.

---

## 1. 전체 지도

### 1.1 사용자 입력 한 번의 큰 흐름

```text
사용자
  |
  v
main.py
  |
  v
run_qwen_user_turn()
  |
  v
run_dry_turn()  <- 현재 한 턴의 중앙 배선
  |
  +-> TraceStore: 무엇이 일어났는가
  +-> DataStore : 실제 결과물은 무엇인가
  |
  v
0 기억공급관
  |
  v
1 라우터
  |
  +-> L: 현재 디스크의 문서/코드 조사
  +-> R: Vessel 그래프 기억 탐색
  +-> 2: 이미 공급된 근거로 보고 준비
  |
  v
2 메타정보 경계 및 답변 근거 모드 선택
  |
  v
3 최종 보고문 작성
  |
  v
4 LLM 검사 + CODE 절대검사
  |
  v
공개 또는 차단
```

### 1.2 노드를 사람 역할로 바꾸어 말하기

| 구성요소 | 사람 역할 | 핵심 질문 |
| --- | --- | --- |
| TraceStore | 사건 일지 담당 | 무슨 일이 어떤 순서로 일어났나? |
| DataStore | 증거 보관 담당 | 그 사건이 만든 실제 데이터는 무엇인가? |
| 0 | 자료 운반 담당 | 다음 담당자가 볼 근거 좌표는 무엇인가? |
| 1 | 길 안내 담당 | 디스크 조사, 그래프 기억, 바로 보고 중 어디로 갈까? |
| L1 | 조사 목표 담당 | 무엇을 얼마나 확인해야 성공인가? |
| L2 | 도구 선택 담당 | 어떤 도구로 무엇을 찾고 읽을까? |
| L3 | 조사 결과 판정 담당 | 목표가 달성됐나, 더 조사해야 하나? |
| 2 | 근거 분류 담당 | 어떤 근거를 어떤 역할로 3에게 줄까? |
| 3 | 사용자 보고 담당 | 근거와 한계를 드러내며 어떻게 답할까? |
| 4 | 공개 전 검사 담당 | 받은 근거보다 더 말했거나 숫자를 틀렸나? |

### 1.3 가장 중요한 구분

```text
TraceEvent = 사건의 영수증
DataRecord = 영수증이 가리키는 실제 물건
```

예를 들어 `read_doc` 도구가 문서를 읽었다고 하자.

- TraceEvent에는 누가, 언제, 어떤 도구를 실행했고 어떤 data ID를 만들었는지가 남는다.
- DataRecord에는 읽은 문서 경로, 원문, 글자 수 같은 실제 payload가 남는다.

Trace만 있고 DataRecord가 없으면 사건은 있었지만 결과 본체를 확인할 수 없다.
DataRecord만 있고 Trace가 없으면 결과는 있지만 누가 왜 만들었는지 추적하기 어렵다.
송련이 둘을 함께 쓰는 이유다.

---

## 2. 자료의 신분증: DataRef와 TraceEvent

### 2.1 진짜 코드: DataRef

파일: `songryeon_core/core/schema_parts/base.py`

```python
@dataclass
class DataRef:
    """시스템이 확인할 수 있는 데이터 하나를 가리키는 절대정보 참조."""

    data_id: str
    data_type: str
    exists: bool = True
    created_at: str | None = None
    source_trace_id: str | None = None
```

### 2.2 한 줄씩 읽기

1. `@dataclass`: 반복되는 생성자 코드를 Python이 대신 만든다.
2. `DataRef`: 실제 본체가 아니라 본체를 가리키는 표지판이다.
3. `data_id`: 데이터 하나의 고유 주소다.
4. `data_type`: 문서 원문, 도구 결과, LLM 판단 같은 종류를 구분한다.
5. `exists`: 코드가 데이터 존재를 확인했는지 나타낸다.
6. `created_at`: 생성 시각을 모르면 거짓 시각을 만들지 않고 `None`으로 둔다.
7. `source_trace_id`: 이 데이터의 존재를 확인하게 해준 사건 장부 주소다.

### 2.3 진짜 코드: TraceEvent

파일: `songryeon_core/core/schema_parts/trace_data.py`

```python
@dataclass
class TraceEvent:
    """일 하나가 벌어질 때마다 남기는 trace 기록 조각."""

    event_id: str
    turn_id: str
    timestamp: str
    actor: str
    event_type: str
    input_ref: list[str] = field(default_factory=list)
    output_ref: list[str] = field(default_factory=list)
    raw_content_ref: str | None = None
    schema_status: str = "not_checked"
```

### 2.4 한 줄씩 읽기

- `event_id`: 사건 자체의 번호다.
- `turn_id`: 어느 대화 턴에서 생긴 사건인지 묶는다.
- `timestamp`: 사건 발생 시각이다.
- `actor`: 사건을 만든 주체다. 예: `node_1`, `L2`, `tool`.
- `event_type`: 입력, 라우팅, 도구 호출, 도구 결과 같은 사건 종류다.
- `input_ref`: 이 사건이 참고한 trace/data 주소다.
- `output_ref`: 이 사건이 새로 만든 data 주소다.
- `raw_content_ref`: 긴 원문을 직접 넣지 않고 원문 위치를 가리킬 수 있다.
- `schema_status`: 구조 검사를 통과했는지를 코드가 기록한다.

### 2.5 왜 절대정보인가?

`TraceEvent`의 필드는 “문서가 유익하다” 같은 해석이 아니다.

```text
어떤 ID가 있었다.
어느 턴에서 생겼다.
누가 만들었다.
어떤 데이터를 입력받고 출력했다.
스키마 검사를 통과했다.
```

이 값들은 코드가 확인할 수 있으므로 절대정보다.

### 2.6 내 말로 설명하기

1. `event_id`와 `data_id`는 왜 둘 다 필요한가?
2. `schema_status=passed`는 내용이 진실이라는 뜻인가?
3. `created_at=None`을 허용하는 것이 왜 정직한가?

정답 방향:

- 사건 번호와 결과물 번호는 가리키는 대상이 다르다.
- 스키마 통과는 모양이 맞다는 뜻이지 의미가 참이라는 뜻이 아니다.
- 모르는 시각을 코드가 꾸며내지 않기 때문이다.

---

## 3. 두 장부: TraceStore와 DataStore

### 3.1 진짜 코드: DataStore의 핵심

파일: `songryeon_core/core/data_store.py`

```python
class DataStore:
    def __init__(self, records=None) -> None:
        self._records: list[DataRecord] = []
        self._record_index: dict[str, DataRecord] = {}

        for record in records or []:
            self.add_record(record)

    def add_record(self, record: DataRecord) -> DataRecord:
        if record.data_id in self._record_index:
            raise ValueError(f"duplicate data_id: {record.data_id}")
        self._validate_record(record)
        self._records.append(record)
        self._record_index[record.data_id] = record
        return record
```

### 3.2 한 줄씩 읽기

1. `_records`는 생성 순서를 보존한다.
2. `_record_index`는 ID로 빠르게 찾는다.
3. 같은 ID를 두 번 등록하려 하면 즉시 실패한다.
4. 저장 전에 `_validate_record()`로 최소 구조를 확인한다.
5. 검증된 record만 순서 목록과 검색용 사전에 함께 넣는다.

```text
list = 역사를 순서대로 보기 좋다.
dict = 특정 ID를 빠르게 찾기 좋다.
```

### 3.3 진짜 코드: TraceStore의 live hook

파일: `songryeon_core/core/trace_store.py`

```python
class TraceStore:
    def __init__(self, events=None, *, on_event=None) -> None:
        self._events: list[TraceEvent] = []
        self._event_index: dict[str, TraceEvent] = {}
        self._on_event = on_event

    def add_event(self, event: TraceEvent, *, notify: bool = True) -> TraceEvent:
        if event.event_id in self._event_index:
            raise ValueError(f"duplicate trace event_id: {event.event_id}")

        self._validate_event(event)
        self._events.append(event)
        self._event_index[event.event_id] = event
        if notify and self._on_event is not None:
            self._on_event(event)
        return event
```

### 3.4 한 줄씩 읽기

- `_events`와 `_event_index`의 관계는 DataStore와 같다.
- `_on_event`는 사건이 생길 때 화면에 즉시 알리는 함수다.
- `notify=False`이면 과거 기록 복원 시 옛 사건을 새 사건처럼 띄우지 않는다.
- 중복 event ID는 전체 추적을 흔들기 때문에 바로 실패한다.

송련은 충돌을 피하려고 중복 ID를 조용히 덮어쓰지 않는다. 덮어쓰면 오래된 근거와
새 근거가 섞였는데도 사람이 모를 수 있기 때문이다.

### 3.5 내 말로 설명하기

> 왜 송련은 list 하나만 쓰거나 dict 하나만 쓰지 않는가?

답:

> 사건 순서와 ID 검색이라는 서로 다른 필요를 동시에 만족하기 위해서다.

---

## 4. 사용자 턴의 입구: run_qwen_user_turn

### 4.1 진짜 코드

파일: `songryeon_core/runtime/user_turn.py:160`

```python
def run_qwen_user_turn(
    *,
    user_input: str,
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
    search_top_k: int = DEFAULT_SEARCH_TOP_K,
    max_query_attempts: int = DEFAULT_MAX_QUERY_ATTEMPTS,
    max_read_doc_calls: int = DEFAULT_MAX_READ_DOC_CALLS,
    force_l_route: bool = False,
    force_vessel_r_route: bool = False,
    same_turn_l_reroute_enabled: bool = False,
    max_l_runs_per_turn: int = 1,
    same_turn_r_reroute_enabled: bool = False,
    max_r_runs_per_turn: int = 2,
    ...
) -> dict[str, object]:
```

### 4.2 이 함수가 받는 것

| 인자 | 뜻 |
| --- | --- |
| `user_input` | 사용자가 입력한 질문 |
| `endpoint` | Ollama 같은 모델 서버 주소 |
| `model_id` | 사용할 모델 이름 |
| `timeout_seconds` | 모델 한 번 호출의 최대 대기 시간 |
| `max_tool_calls` | L루프의 전체 도구 호출 한도 |
| `search_top_k` | 검색 후보를 몇 개까지 받을지 |
| `max_query_attempts` | 검색 질의를 몇 번까지 시도할지 |
| `max_read_doc_calls` | 원문 읽기를 몇 번까지 허용할지 |
| `force_l_route` | 테스트를 위해 L 경로를 강제로 선택 |
| `force_vessel_r_route` | 테스트를 위해 R 경로를 강제로 선택 |

`검색 횟수`, `후보 수`, `원문 읽기 횟수`는 서로 다른 예산이다. 후보를 12개
찾았다고 원문 12개를 읽은 것이 아니다.

### 4.3 진짜 코드: 같은 adapter를 각 노드에 연결

```python
result = run_dry_turn(
    user_input=user_input,
    node_1_router_adapter=adapter,
    memory_relevance_selector_adapter=adapter,
    l1_goal_adapter=adapter,
    l_tool_scope_adapter=adapter,
    l2_query_planner_adapter=adapter,
    l3_result_adapter=adapter,
    node_2_boundary_adapter=adapter,
    node_3_reporter_adapter=adapter,
    node_4_gatekeeper_adapter=adapter,
    ...
)
```

`adapter`는 LLM 호출법을 통일한 부품이다. 현재 Qwen 실행에서는 같은 로컬 모델이
여러 역할을 번갈아 수행한다. 같은 모델을 써도 각 노드의 prompt, 입력, schema,
권한이 다르므로 역할은 분리된다.

```text
배우 한 명(Qwen)이 길 안내원, 조사 계획자, 결과 검사자, 보고자 역할을
각기 다른 대본과 양식으로 연기한다.
```

### 4.4 진짜 코드: 실패를 숨기지 않는 경계

```python
try:
    result = run_dry_turn(...)
except Exception as exc:
    diagnostics = _structure_failure_diagnostics(exc)
    return {
        "status": "structure_failed",
        "reason": exc.__class__.__name__,
        "error": str(exc),
        **diagnostics,
    }
```

정상 실행은 `try` 안에서 수행한다. 예외가 나면 예외 이름과 메시지를 남기고
`structure_failed`로 닫는다. 이것은 오류가 안 나는 프로그램이 아니라, 오류가
났을 때 거짓 성공을 말하지 않는 프로그램을 만드는 코드다.

### 4.5 내 말로 설명하기

> 같은 Qwen 모델을 모든 노드에서 쓰는데 왜 여러 노드라고 부를 수 있는가?

답:

> 역할별 prompt, 입력 근거, 출력 schema, 권한이 다르기 때문이다.

---

## 5. 한 턴의 중앙 배선: run_dry_turn

### 5.1 진짜 코드

파일: `songryeon_core/runtime/dry_run.py:133`

```python
def run_dry_turn(...):
    """한 턴의 구조 흐름을 trace/data로 실행한다.

    이름은 dry_run으로 남아 있지만, adapter를 넘기면 Qwen/fake LLM 노드도 함께 돈다.
    그래서 이 함수는 현재 MVP의 중앙 배선도에 가깝다.
    """

    if force_l_route and force_vessel_r_route:
        raise ValueError("force_l_route and force_vessel_r_route cannot both be true")

    turn_id = turn_id or DEFAULT_TURN_ID
    trace_store = TraceStore(on_event=live_trace_sink)
    data_store = DataStore()
    zero_state = ZeroState(
        recent_raw_conversation=list(recent_raw_conversation or []),
        previous_turn_capsules=list(previous_turn_capsules or []),
    )
    unified_state = create_unified_state(turn_id, user_input)
```

### 5.2 한 줄씩 읽기

1. L과 R을 동시에 강제하면 모순이므로 실패한다.
2. turn ID가 없으면 기본 ID를 만든다.
3. TraceStore를 만들면서 live 화면 hook을 연결한다.
4. DataStore는 이번 턴의 실제 payload를 담는다.
5. ZeroState에는 최근 대화 원문과 이전 턴 캡슐을 복사해 넣는다.
6. UnifiedState에는 일반 노드들이 공유할 현재 턴 상태를 만든다.

`list(recent_raw_conversation or [])`는 바깥 list를 직접 공유하지 않고 이번 턴의
복사본을 만든다.

### 5.3 run_dry_turn이 큰 이유

현재 약 2,700줄이며 다음을 모두 연결한다.

- 사용자 입력 기록
- 0의 기억 공급
- 1의 라우팅
- L/R 실행
- 상위 루프 재실행 정책
- 2의 경계와 handoff
- 3의 보고
- 4의 검사
- 최종 trace/data 반환

즉 알고리즘 하나라기보다 여러 부품을 연결하는 배전반이다.

### 5.4 내 말로 설명하기

> `run_dry_turn`은 똑똑한 판단 함수인가, 배선 함수인가?

답:

> 주된 역할은 배선이다. 의미 판단은 각 LLM 노드에 맡기고 호출 순서와 데이터
> 전달을 관리한다.

---

## 6. 0 기억공급관: 내용을 쓰지 않고 좌표를 운반한다

### 6.1 진짜 코드

파일: `songryeon_core/nodes/node_0_memory_supplier.py:81`

```python
def supply_memory(
    *,
    target: str,
    mode: str,
    zero_state: ZeroState,
    trace_store: TraceStore,
    turn_id: str,
    insufficient_signal_id: str | None = None,
) -> MemoryPacketFrom0:
    """0 기억공급관의 규칙 기반 기억 패킷을 만든다."""

    if mode not in NODE_0_MODES:
        raise ValueError(f"unknown node_0 mode: {mode}")

    trace_ids = [event.event_id for event in trace_store.events_for_turn(turn_id)]
    for trace_id in zero_state.current_turn_trace_ids:
        if trace_id not in trace_ids:
            trace_ids.append(trace_id)

    return MemoryPacketFrom0(
        target=target,
        trace_evidence_ids=trace_ids,
        insufficient_signal_id=insufficient_signal_id,
    )
```

### 6.2 한 줄씩 읽기

1. `target`: 기억 봉투를 받을 노드다.
2. `mode`: 0이 어떤 상황에서 불렸는지 나타낸다.
3. 허용되지 않은 mode이면 즉시 막는다.
4. 현재 턴의 사건 ID를 모은다.
5. ZeroState가 따로 들고 있던 trace를 중복 없이 합친다.
6. 의미 요약 대신 `trace_evidence_ids`라는 좌표 목록을 넘긴다.
7. 기억 부족이 있으면 실패 신호 ID도 함께 넘긴다.

현재 `supply_memory()`는 코드 함수다. 코드가 의미를 이해한 척하며 “이 기억이
중요하다”고 쓰면 상대정보를 절대정보처럼 위장하게 된다. 관련성 판단이 필요하면
별도 LLM selector가 판단하고 생성자와 출처를 남긴다.

### 6.3 TurnStateCapsule

```python
@dataclass
class TurnStateCapsule:
    turn_id: str
    node_movements: list[NodeMovement]
    trace_event_ids: list[str]
    user_input_trace_id: str | None
    final_response_trace_id: str | None
```

캡슐은 이전 턴을 이해한 요약이 아니라, 과거 사건과 원문을 다시 찾기 위한 색인
카드다.

### 6.4 내 말로 설명하기

> 0은 기억을 생성하는가, 공급하는가?

답:

> 기본적으로 출처가 있는 기억 좌표를 공급한다. 의미 판단이 필요하면 별도 LLM
> 판단 기록으로 분리한다.

---

## 7. 1 라우터: 필요한 근거 표면을 비교한다

### 7.1 진짜 코드

파일: `songryeon_core/nodes/node_1_router.py:126`

```python
allowed_routes = ["L", "2"]
route_meanings = {
    "L": "fresh disk/source document/code/artifact lookup for evidence that is not ingested or whose current file state must be verified",
    "2": "direct metainfo boundary and final reporting when supplied context is enough",
}
if allow_r_route_experimental:
    allowed_routes.append("R")
    route_meanings["R"] = _r_route_meaning(resolved_r_execution_mode)
```

한국어로 풀면 다음과 같다.

- `L`: 현재 디스크의 문서·코드·파일 상태를 새로 확인해야 할 때
- `R`: 이미 Vessel 그래프에 적재된 기억을 계층적으로 탐색할 때
- `2`: 이미 손에 들어온 근거만으로 답변 준비가 가능할 때

### 7.2 진짜 코드: 라우팅 정책

```python
"route_selection_policy": {
    "policy_id": "NODE1_ROUTE_EVIDENCE_SURFACE_COMPARISON_V0",
    "decision_basis": "Compare what evidence surface the user is asking for before selecting a route.",
    "not_a_keyword_rule": True,
    "code_semantic_routing_status": "not_run",
    "llm_must_explain": (
        "Write route_reason by naming why the selected route's evidence "
        "surface fits better than the other available loop routes."
    ),
},
```

### 7.3 한 줄씩 읽기

1. `policy_id`: 어떤 정책으로 판단했는지 추적한다.
2. `decision_basis`: 사용자가 요구한 근거가 어디에 있는지 비교하라고 한다.
3. `not_a_keyword_rule`: 코드 키워드 매칭 정책이 아니라고 명시한다.
4. `code_semantic_routing_status`: 코드가 의미 라우팅을 한 척하지 않는다.
5. `llm_must_explain`: LLM은 선택 이유를 남겨야 한다.

### 7.4 진짜 코드: 실패 경계

```python
llm_result = LLMNodeExecutor(adapter).run(
    node_id="node_1",
    prompt=prompt,
    input_payload=input_payload,
    payload_validator=lambda payload: _validate_llm_routing_payload(...),
)

if llm_result.failure_type != "none" or llm_result.validation.payload is None:
    raise Node1RouterLLMFailure(...)
```

모델이 문장을 그럴듯하게 써도 schema가 틀리면 실패다. Qwen strict 실행에서는 이
실패를 조용한 코드 판단으로 숨기지 않는다.

### 7.5 내 말로 설명하기

> “최신”이라는 단어가 있으면 무조건 R인가?

답:

> 아니다. 현재 파일 상태를 확인해야 하면 L이고, 이미 그래프에 적재된 시간축 기억을
> 탐색해야 하면 R이다.

---

## 8. L루프: 목표, 도구, 결과 판정을 분리한다

### 8.1 진짜 코드

파일: `songryeon_core/loops/l_loop.py:143`

```python
def run_l_loop(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    memory_packet: MemoryPacketFrom0,
    search_query: str,
    document_root: str | Path = "Administrative_Reform_1",
    code_root: str | Path | None = None,
    l1_goal_adapter: LLMAdapter | None = None,
    l2_query_planner_adapter: LLMAdapter | None = None,
    l3_result_adapter: LLMAdapter | None = None,
    max_tool_calls: int = 5,
    max_query_attempts: int = 3,
    search_top_k: int = 3,
    max_read_doc_calls: int = 1,
    ...
) -> LLoopResult:
```

### 8.2 역할 나누기

```text
L1: 성공 조건과 필요한 근거 종류를 정한다.
L2: 허용된 도구 목록과 예산 안에서 실행 계획을 고른다.
도구: 검색하고 읽고 시간 메타데이터를 검사한다.
L3: 실제 결과가 목표에 충분한지 판정한다.
controller: 더 돌지, 멈출지 구조적으로 결정한다.
```

### 8.3 진짜 코드: 예산 입력 검증

```python
if max_tool_calls < 1:
    raise ValueError("max_tool_calls must be at least 1")
if max_query_attempts < 1:
    raise ValueError("max_query_attempts must be at least 1")
if search_top_k < 1:
    raise ValueError("search_top_k must be at least 1")
if max_read_doc_calls < 1:
    raise ValueError("max_read_doc_calls must be at least 1")
```

예산을 넘었는데 숫자를 조용히 줄이는 silent clamp를 하지 않는다. 잘못된 계약은
실패로 드러낸다.

### 8.4 진짜 코드: L1 뒤에 CODE 예산 정책

```python
l1 = run_l1_goal_setter(...)

budget_plan_trace_id, budget_plan_data_id, budget_plan_frame = (
    record_l_loop_budget_plan(
        l1_event=l1,
        base_search_top_k=search_top_k,
        base_max_tool_calls=max_tool_calls,
        base_max_read_doc_calls=max_read_doc_calls,
        base_max_query_attempts=max_query_attempts,
        ...
    )
)

search_top_k = budget_plan_frame.approved_search_top_k
max_tool_calls = budget_plan_frame.approved_max_tool_calls
max_read_doc_calls = budget_plan_frame.approved_max_read_doc_calls
max_query_attempts = budget_plan_frame.approved_max_query_attempts
```

L1은 필요량을 판단하고, CODE 정책은 시스템 상한 안에서 승인값을 만든다. 실제
실행에는 승인값만 사용한다.

### 8.5 진짜 코드: 실제 도구 목록을 먼저 만든다

```python
tool_registry = build_document_tool_registry(
    document_root,
    code_root=codebase_root,
)
tool_catalog_trace_id = record_tool_catalog(...)
catalog_record = data_store.require_record(catalog_id)
available_tools = catalog_payload.get("tools")
```

L2에게 세상의 모든 도구 이름을 상상하라고 하지 않는다. CODE가 실제 등록된 도구
목록을 만들고, L2는 그 목록 안에서만 고른다.

### 8.6 검색 후보와 실제 원문 읽기

```text
search_docs 결과 후보 = 제목/경로/검색 점수
read_doc 결과 = 실제 문서 원문
inspect_source_time_metadata = 원문이 아닌 파일 시간/크기/hash
```

후보가 12개여도 `read_doc=0`이면 원문을 읽지 않은 것이다. 시간 메타데이터를
확인했어도 원문을 읽었다고 말하면 안 된다.

### 8.7 현재 알려진 live 학습 포인트

ORDER 285에서 시간 도구 결과는 node_3까지 정상 전달됐다. 다만 L1이
`minimum_read_documents=0`과 `artifact_requirement_mode=exact_one`을 함께 내는
계약 모순이 관측됐다. prompt 안내만으로 완전히 막히지 않았기 때문에 후속 구조
validator 후보로 남아 있다.

### 8.8 내 말로 설명하기

1. 검색 후보 10개와 실제 읽은 문서 10개는 왜 다른가?
2. L1이 예산을 요청하면 왜 CODE가 다시 승인하는가?
3. 시간 메타데이터 검사는 왜 `read_doc` count에 들어가면 안 되는가?

---

## 9. 2번 노드: 근거를 분류하고 3번의 자세를 정한다

### 9.1 진짜 코드: 메타정보 경계

파일: `songryeon_core/nodes/node_2_metainfo_boundary.py:39`

```python
def build_metainfo_boundary(
    *,
    trace_store: TraceStore,
    turn_id: str,
    data_store: DataStore | None = None,
    node2_input_frame_id: str | None = None,
) -> MetainfoBoundary:
    """현재 턴 trace에서 확인 가능한 절대정보만 모아 MetainfoBoundary를 만든다."""

    if node2_input_frame_id is not None and data_store is not None:
        return _build_boundary_from_node2_input_frame(...)

    return _build_boundary_from_turn_trace(...)
```

가능하면 node_2에게 명시적으로 공급된 input frame만 경계로 삼는다. 경계는 답이
참인지 결정하는 곳이 아니라, 어떤 근거가 존재하며 어느 종류인지 정리하는 곳이다.

### 9.2 절대/상대/혼합의 코드 관점

```text
절대정보:
  코드가 존재, 값, 횟수, ID, 경로, schema 상태를 확인 가능

상대정보:
  하나의 절대 record/field에 대응하는 LLM 해석

혼합정보:
  여러 절대정보 묶음에 근거하거나 하나로 못 박기 부적절한 LLM 해석
```

출처가 있다고 모두 혼합정보가 아니다. 하나에 대응하면 상대정보이고, 여러 근거
묶음이면 혼합정보다.

### 9.3 진짜 코드: 답변 근거 후보를 고정

```python
available_evidence_sources = _answer_basis_available_evidence_sources(...)

evidence_source_id_by_ref = {
    str(source["evidence_ref"]): str(source["source_data_id"])
    for source in available_evidence_sources
}

allowed_answer_basis_source_data_ids = _unique_strings(
    [
        str(source["source_data_id"])
        for source in available_evidence_sources
        if isinstance(source.get("source_data_id"), str)
    ]
)
```

1. CODE가 실제 사용 가능한 근거 목록을 만든다.
2. LLM에게 안전한 `evidence_ref`를 보여준다.
3. 내부에서 ref를 실제 source data ID와 대응한다.
4. LLM이 허용 목록 밖 ID를 지어내면 validator가 실패시킨다.

### 9.4 답변 모드 3개

| 모드 | 뜻 |
| --- | --- |
| `absolute_first` | 코드가 확인한 사실 중심으로 좁고 정밀하게 말함 |
| `relative_allowed` | 특정 근거에 대응하는 해석을 유연하게 포함 |
| `mixed_or_uncertain` | 여러 근거가 섞였거나 정보가 부족함을 전제로 말함 |

LLM이 실패하면 CODE가 의미적으로 모드를 대신 고르지 않는다. 대신
`mixed_or_uncertain`, `CODE:FALLBACK`, `semantic_judgement_status=failed`로
판단 실패를 드러낸다.

### 9.5 내 말로 설명하기

> 2번은 근거가 부족하면 L이나 R로 되돌리는 노드인가?

답:

> 현재 핵심 역할은 근거 분류와 3번용 brief 조립이다. 모든 부족 상황을 자동
> 복구하는 라우터로 과장하면 안 된다.

---

## 10. 3번 노드: CODE가 숫자를 쓰고 LLM이 본문을 쓴다

### 10.1 진짜 코드: grounding block

파일: `songryeon_core/nodes/node_3_reporter.py:147`

```python
def build_node3_grounding_block(
    brief_frame: Node3InputBriefFrame,
    *,
    llm_payload: dict[str, object] | None = None,
) -> str:
    payload = llm_payload or node3_brief_llm_payload(brief_frame)
    total_raw_text_count, code_range_text_count = _llm_raw_text_counts(payload)
    return "\n".join(
        [
            "근거 기준:",
            f"- 실제 read_doc 도구 원문 읽기: {brief_frame.actual_tool_read_doc_count}개",
            f"- node_3 공급 문서 context: {brief_frame.supplied_document_context_count}개",
            (
                "- 파일 시간 메타데이터 검사: "
                f"{brief_frame.temporal_metadata_inspection_count}개 / "
                f"성공 {brief_frame.successful_temporal_metadata_count}개"
            ),
            f"- node_3 LLM 원문 text: {total_raw_text_count}개",
            ...
        ]
    )
```

원문을 몇 개 읽었는지는 LLM에게 세라고 하지 않는다. CODE가 frame의 정수 필드를
읽어 문장을 만든다.

```text
문서 개수 = 코드가 셀 수 있는 절대정보
문서 의미 설명 = LLM이 작성할 상대/혼합정보
```

### 10.2 진짜 코드: CODE 블록과 LLM 본문 합치기

```python
def assemble_node3_report_markdown(
    *,
    brief_frame: Node3InputBriefFrame,
    body_markdown: str,
) -> str:
    grounding_block = build_node3_grounding_block(brief_frame)
    body = _strip_accidental_grounding_block(body_markdown)
    if not body:
        return grounding_block
    if not grounding_block:
        return body
    return f"{grounding_block}\n\n{body}"
```

1. CODE가 고정 grounding block을 만든다.
2. LLM이 자기 grounding block을 또 만들었으면 제거한다.
3. LLM 본문이 비었으면 CODE 블록만 반환한다.
4. 근거가 필요 없는 대화면 본문만 반환할 수 있다.
5. 둘 다 있으면 CODE 블록 위에 LLM 본문을 붙인다.

핵심:

> CODE는 의미 본문을 대신 쓰지 않고, LLM은 절대 count를 임의로 쓰지 않는다.

### 10.3 내 말로 설명하기

> node_3가 “문서 5개를 읽었다”고 직접 쓰지 못하게 한 이유는?

답:

> 읽은 문서 수는 코드가 확정할 수 있는 절대정보이고 실제로 과거 count mismatch가
> 발생했기 때문이다.

---

## 11. 4번 노드: LLM 검사와 CODE 검사를 겹쳐 쓴다

### 11.1 진짜 코드: LLM gatekeeper 입력

파일: `songryeon_core/nodes/node_4_gatekeeper.py:38`

```python
brief_payload = node3_brief_llm_payload(brief_frame)
llm_result = LLMNodeExecutor(adapter).run(
    node_id="node_4",
    prompt=prompt,
    input_payload={
        "rendered_markdown": rendered_markdown[:5000],
        "node3_input_brief": brief_payload,
        "checks": [
            "사용자 질문의 핵심 행동을 실제 보고문이 수행했는지 확인한다.",
            "absolute_grounding_facts와 본문이 충돌하는지 확인한다.",
            "검색 후보 문서를 읽은 문서처럼 말하는지 확인한다.",
            "최근 기억이 선택된 범위를 벗어나는지 확인한다.",
        ],
    },
    payload_validator=_validate_gatekeeper_payload,
)
```

4는 최종 답변과 3이 실제로 받은 brief를 함께 본다. 보고문이 사용자 과업을
수행했는지, 근거 밖의 주장을 했는지 의미적으로 검사한다.

### 11.2 진짜 코드: 4가 실패하면 pass하지 않는다

```python
if llm_result.failure_type == "none" and llm_result.validation.payload is not None:
    gate_status = str(payload.get("gate_status") or "").strip()
else:
    gate_status = "failed"
    reason = f"node_4 LLM gatekeeper failed: {llm_result.failure_type}"
    revision_targets = [reason]
```

LLM 검사기가 고장 났는데 “아마 괜찮겠지”라고 공개하지 않는다.

### 11.3 진짜 코드: CODE count guard

```python
code_count_violations = _grounding_count_violations(
    rendered_markdown=rendered_markdown,
    brief_frame=brief_frame,
)
if code_count_violations:
    if gate_status == "pass":
        gate_status = "needs_revision"
    gate_generation_source = (
        f"{gate_generation_source}+CODE:GROUNDING_COUNT_GUARD"
    )
    reason = _append_reason(
        reason,
        "CODE_STATUS:grounding_count_mismatch",
    )
```

1. 보고문 숫자와 brief 숫자를 코드가 비교한다.
2. LLM 4가 `pass`라고 해도 숫자가 다르면 `needs_revision`으로 바꾼다.
3. 누가 판정을 바꿨는지 `CODE:GROUNDING_COUNT_GUARD`를 붙인다.
4. 실패 이유도 구조화된 코드로 남긴다.

### 11.4 문서 역할 guard

```python
document_role_guard = _document_evidence_role_code_guard(
    rendered_markdown=rendered_markdown,
    brief_frame=brief_frame,
)
if document_role_guard["status"] == "needs_revision":
    if gate_status == "pass":
        gate_status = "needs_revision"
```

이 guard는 검색 후보를 실제로 읽은 원문이라고 과장하는 명시적 역할 충돌을 막는다.

### 11.5 과장하면 안 되는 부분

CODE guard가 현재 잘하는 일:

- count 불일치
- 허용되지 않은 ID
- 검색 후보와 실제 원문 읽기 역할 혼동
- 일부 내부 ID 누출
- 구조화된 상태 이름 충돌

현재 일반적으로 보장하지 못하는 일:

- 복잡한 자연어 문장 전체의 진실성
- 세상 모든 사실의 최신성
- 문서 내용 자체가 거짓인지 판별
- 미묘한 논리 오류 전부 탐지

### 11.6 내 말로 설명하기

> node_4 LLM이 pass라고 했는데 CODE가 needs_revision으로 바꿀 수 있는가?

답:

> 숫자나 명시적 근거 역할처럼 코드가 확정할 수 있는 구조적 충돌이라면 가능하다.
> 의미 판단 전체를 코드가 대신하는 것은 아니다.

---

## 12. 실제 사례로 한 턴 따라가기

질문:

```text
ORDER_284 문서 파일의 수정 시각을 확인해줘.
파일 원문을 읽었는지와 시간 메타데이터만 검사했는지를 구분해서 말해줘.
```

### 12.1 기대 실행

1. 0이 현재 trace 좌표를 1에게 공급한다.
2. 1이 현재 디스크 파일 확인이 필요하므로 L을 선택한다.
3. L1이 시간 근거가 필요하다고 판단한다.
4. L2가 `inspect_source_time_metadata`를 선택한다.
5. CODE 도구가 경로, 관측 시각, 수정 시각, 크기, hash를 기록한다.
6. L3가 시간 근거 확보 상태를 판단한다.
7. 0이 L 결과 좌표를 1/2에게 전달한다.
8. 2가 시간 메타데이터를 답변 근거로 선택한다.
9. 3의 CODE grounding block이 각 count를 분리한다.
10. 3 LLM이 수정 시각을 설명한다.
11. 4가 숫자와 본문의 역할 충돌을 검사한다.

### 12.2 구분해야 하는 세 절대정보

```text
actual_tool_read_doc_count
supplied_document_context_count
temporal_metadata_inspection_count
```

예:

```text
read_doc=0
supplied context=1
temporal inspection=1
```

- `read_doc=0`: read_doc 도구로 원문을 읽지 않았다.
- `context=1`: 별도 context pack이 문서 내용을 공급했다.
- `temporal=1`: 시간 메타데이터 전용 도구가 파일을 검사했다.

### 12.3 live에서 발견된 잔여 문제

시간 근거 전달은 성공했지만, 후속 실행에서 L1은 다음 두 필드를 함께 출력했다.

```text
minimum_read_documents = 0
artifact_requirement_mode = exact_one
```

첫 필드는 원문 읽기가 필요 없다는 뜻이고, 둘째 필드는 명시 문서 원문 확보를
요구하는 방향으로 사용됐다. 이 모순 때문에 revision에서 원문을 추가로 읽었다.

학습 결론:

> prompt를 더 강하게 쓰는 것만으로 구조 모순이 항상 사라지지는 않는다.
> LLM이 만든 필드끼리의 관계도 CODE validator로 검사할 필요가 있다.

---

## 13. 심사위원에게 설명할 수 있어야 하는 10문장

1. 송련은 무엇을 검색했고 실제로 무엇을 읽었는지 별도 count로 기록합니다.
2. TraceStore는 사건을, DataStore는 사건이 만든 실제 payload를 보관합니다.
3. 0번은 의미를 창작하지 않고 근거 좌표를 다음 노드에 공급합니다.
4. 1번은 필요한 근거가 디스크, 그래프, 현재 context 중 어디에 있는지 판단합니다.
5. L루프는 목표 설정, 도구 선택, 결과 판정을 L1/L2/L3로 분리합니다.
6. 도구 예산은 LLM 요청을 그대로 믿지 않고 CODE 정책이 승인합니다.
7. 2번은 절대·상대·혼합정보 경계를 만들고 3번의 답변 자세를 선택합니다.
8. 3번의 절대 count 블록은 CODE가 만들고 의미 본문은 LLM이 씁니다.
9. 4번이 통과시켜도 CODE가 확인 가능한 숫자나 문서 역할이 충돌하면 공개를 막습니다.
10. 모든 환각을 해결한다고 주장하지 않고 현재 검증 가능한 구조적 범위를 명시합니다.

---

## 14. 오늘 직접 해볼 코드 읽기 실습

### 실습 1: 함수 찾기

```powershell
rg -n "^def run_qwen_user_turn" songryeon_core/runtime/user_turn.py
rg -n "^def run_dry_turn" songryeon_core/runtime/dry_run.py
rg -n "^def supply_memory" songryeon_core/nodes/node_0_memory_supplier.py
rg -n "^def route_next_with_llm" songryeon_core/nodes/node_1_router.py
```

### 실습 2: TraceStore와 DataStore 비교

1. 두 저장소가 list와 dict를 함께 쓰는 이유는?
2. 중복 ID가 들어오면 어떻게 되는가?
3. JSON 저장 시 한글이 보존되는 이유는?

힌트:

```python
json.dumps(..., ensure_ascii=False, indent=2)
```

### 실습 3: 실패 읽기

`run_qwen_user_turn()`에서 `except Exception` 아래를 읽고 다음을 찾는다.

- 사용자에게 표시되는 상태 이름
- 예외 종류
- 예외 메시지
- 실패 노드와 prompt diagnostics

### 실습 4: 절대 count의 소유자

`build_node3_grounding_block()`을 읽고 답한다.

> 읽은 문서 수는 node_3 LLM이 쓰는가, CODE가 frame에서 복사하는가?

### 실습 5: 4번의 권한 경계

`run_node4_gatekeeper()`에서 다음을 찾고 각각 무엇을 막는지 적는다.

```text
CODE:GROUNDING_COUNT_GUARD
CODE:DOCUMENT_EVIDENCE_ROLE_GUARD
```

---

## 15. 자가 시험

### 문제 1

검색 결과 후보가 12개이고 `actual_tool_read_doc_count=2`라면 읽은 문서는?

A. 12개  
B. 2개  
C. 14개  
D. LLM이 판단한다

### 문제 2

node_4 LLM이 `pass`를 냈지만 grounding count가 brief와 다르다. CODE 처리는?

A. pass 유지  
B. 답변 의미를 새로 작성  
C. needs_revision으로 변경  
D. 숫자를 무작위로 고침

### 문제 3

하나의 문서를 보고 “이 문서는 유지보수에 유익하다”고 판단했다. 분류는?

A. 절대정보  
B. 상대정보  
C. 혼합정보  
D. trace event

### 문제 4

여러 문서와 코드를 함께 보고 “현재 구조는 대회 시연에 적합하다”고 판단했다.

A. 절대정보  
B. 상대정보  
C. 혼합정보  
D. schema status

### 문제 5

`schema_status=passed`가 보장하는 것은?

A. 모든 내용이 진실이다  
B. 출력 구조가 요구한 schema를 통과했다  
C. 최신 인터넷 사실과 일치한다  
D. 인간 검수가 필요 없다

### 정답

1. B
2. C
3. B
4. C
5. B

---

## 16. 다음 학습 순서

1. `node_2_handoff.py`
   - 어떤 근거가 node_3 payload에 실제로 들어가는가
2. `l3_result_keeper.py`
   - operation check와 semantic check의 차이
3. `r_loop_vessel_one_step.py`
   - CoreEgo에서 RawSource까지 계층 탐색하는 방법
4. `schemas.py`와 `schema_parts/`
   - 모든 class를 외우지 않고 실제 사용 frame만 역추적
5. pytest
   - 성공 코드보다 실패 조건을 빠르게 이해하는 방법

---

## 17. 마지막 요약

송련 Core의 핵심은 노드 수가 많다는 것이 아니다.

```text
LLM이 판단할 것
CODE가 확인할 것
둘 사이를 연결하는 출처
실패했을 때 공개하지 않을 조건
```

코드를 읽을 때 항상 다음 네 질문을 붙인다.

1. 이 값은 누가 만들었는가?
2. 절대정보인가, 상대정보인가, 혼합정보인가?
3. 근거 trace/data ID는 어디에 있는가?
4. 실패하면 성공처럼 보일 가능성은 없는가?

이 네 질문으로 코드를 읽을 수 있다면 10만 줄을 외우지 않아도 송련의 설계를
자기 말로 설명하고 고칠 수 있다.
