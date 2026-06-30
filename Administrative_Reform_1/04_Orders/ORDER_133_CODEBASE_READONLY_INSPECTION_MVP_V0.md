# ORDER_133_CODEBASE_READONLY_INSPECTION_MVP_V0

## 상태

발주서.

## 목표

SongRyeon Core가 내부 문서만이 아니라 실제 코드 파일 구조도 읽을 수 있게 하는 첫 read-only MVP를 구현한다.

이번 작업의 목표는 "코딩하는 에이전트"가 아니다.
목표는 "코드베이스를 읽고, 어떤 파일을 실제로 확인했는지 근거와 한계를 드러내며 설명할 수 있는 에이전트"의 최소 기반이다.

## 배경

최근 live 테스트에서 사용자가 다음과 같이 물었다.

```text
그럼 네가 코딩에 얼마나 쓸모를 발휘할 수 있을지 가늠하게 알아서 네 코드 파일이 어떻게 구성됐는지 최대한 자세히 알아와봐
```

송련은 이 질문을 L로 라우팅했지만, 실제 코드 파일을 직접 읽지 못하고 내부 문서와 발주서 중심으로 답하려 했다.
node_4가 근거 불일치를 감지해 최종 답변을 막은 것은 좋은 실패였지만, 코딩 보조로 발전하려면 코드 파일 자체를 읽는 read-only 도구가 필요하다.

## 구현 범위

### In Scope

1. read-only code inspection tool 추가.
   - `list_code_files`
   - `search_code`
   - `read_code_file`

2. 각 도구는 코드 원문 또는 코드 파일 목록에서 확인 가능한 절대정보만 반환한다.
   - 파일 경로
   - 확장자
   - 크기
   - 라인 수
   - 검색 match 위치
   - 읽은 코드 원문
   - truncation 여부

3. 도구 결과는 기존 TraceStore/DataStore tool result 흐름을 사용한다.

4. 도구는 read-only로만 등록한다.

5. L2가 코드 구조 질문에서 코드 도구를 선택할 수 있게 최소 prompt/schema/tool registry를 확장한다.

6. smoke/pytest는 다음을 확인한다.
   - 코드 도구가 workspace 내부 파일만 읽는다.
   - path traversal을 차단한다.
   - `search_code`가 검색 결과를 절대정보로 반환한다.
   - `read_code_file`이 실제 원문과 line count를 반환한다.
   - 코드 도구는 파일 수정 기능을 갖지 않는다.

### Out Of Scope

- 파일 수정
- patch 생성
- apply_patch 자동 실행
- 테스트 자동 실행 계획 생성
- 코드 리뷰 의미 판단 자동화
- dependency graph 고급 분석
- AST 기반 구조 분석
- W/R loop
- scheduler
- 외부 DB/vector DB
- 장기기억 DB
- same-turn L reroute 횟수 변경

## 정보 분류

### 절대정보

code tool이 직접 확인한 값.

예:

```text
file_path
extension
size_bytes
line_count
match_line
match_text
read_text
truncated
```

### 상대정보

특정 코드 파일 하나에 대해 LLM이 만드는 의미 해석.

예:

```text
이 파일은 LLM runtime 설정을 담당하는 것으로 보인다.
```

### 혼합정보

여러 코드 파일, 문서, trace, 실행 기록을 함께 보고 만드는 판단.

예:

```text
현재 코드베이스는 문서 검색 런타임에는 강하지만 실제 코드 수정 에이전트로는 아직 미완성이다.
```

## 금지선

코드 도구는 절대 파일을 수정하지 않는다.

코드는 다음을 하면 안 된다.

```text
"이 파일은 중요하다" 같은 의미 판단
"이 구조가 좋다/나쁘다" 같은 평가
"이 파일을 수정해야 한다" 같은 제안
```

그런 판단은 node/L3/node_2/node_3 같은 LLM 판단 경계에서 source를 드러내고 수행한다.

## 완료 조건

1. `python -m compileall songryeon_core main.py`
2. `python -m pytest`
3. `python main.py smoke-test`

추가 기대:

- 코드 파일 구조 질문에서 L2가 `search_code` 또는 `read_code_file`을 선택할 수 있다.
- 코드 도구 result가 TraceStore/DataStore에 남는다.
- runtime 출력이나 node_3 brief에는 적어도 코드 도구가 실행됐다는 사실이 보존된다.
- 최종 답변이 코드 파일을 읽은 척하려면 실제 code tool result가 있어야 한다.

## 후속 후보

ORDER_134 후보:

```text
CODEBASE_STRUCTURE_PACKET_TO_NODE3_BRIEF
```

ORDER_135 후보:

```text
CODE_REVIEW_READONLY_RISK_FRAME
```

ORDER_136 이후 후보:

```text
PROPOSED_PATCH_FRAME_WITHOUT_APPLYING
```

실제 코드 수정 에이전트는 read-only 코드 구조 파악과 코드 리뷰 프레임이 안정된 뒤에 연다.
