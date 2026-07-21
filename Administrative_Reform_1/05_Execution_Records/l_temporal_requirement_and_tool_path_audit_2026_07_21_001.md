# L 시간 요구 판단과 시간 특화 도구 경로 감사 2026-07-21

- 작업 종류: 정적 코드 감사
- 코드 변경: 없음
- 결론: 설계 방향은 타당하지만 현재 배선만으로는 구현되지 않음

## 1. 사용자 제안

1. L1이 이번 L루프에서 시간 정보가 중요한지 판단한다.
2. 이 판단은 LLM 의미 판단으로 기록한다.
3. L2는 L1 판단과 도구 상황을 보고 시간 특화 도구를 사용할지 결정한다.
4. 시간 도구는 시각·버전·hash 같은 CODE 확인 가능 절대정보를 반환한다.

## 2. 현재 L1

`L1GoalFrame`에는 목표, 문서 요구 관계, 원문 요구량, 예산 요청이 있지만 시간 요구
전용 필드는 없다. L1 prompt에도 현재성, 시간 범위, 시간 근거 요구 계약이 없다.

L1 LLM payload에는 사용자 질문과 memory packet의 trace/data ID가 들어간다. 그러나
해당 ID가 가리키는 timestamp나 workspace manifest 본문은 역참조해서 공급하지 않는다.
따라서 현재 L1은 사용자 질문 문장을 보고 시간 중요도를 의미 판단할 수는 있지만,
실제 파일 시각이나 source version을 근거로 판단할 수는 없다.

메타정보 분류 경계는 다음과 같다.

- 현재 사용자 입력 trace 하나에만 대응한 시간 중요도 판단: relative
- 사용자 입력, 기억 packet, workspace manifest 등 여러 record를 함께 본 판단: mixed
- 따라서 시간 판단을 항상 relative로 고정하려면 입력과 source anchor를 현재 사용자
  입력 하나로 제한해야 한다.

## 3. 현재 L2와 중간 scope 단계

L2는 L1 goal, 사용자 입력, ToolCatalog, L tool scope, budget partition을 입력으로 받는다.
따라서 L1의 시간 요구와 실제 도구 목록을 보고 도구를 선택하는 책임을 맡기기에 구조상
적절하다. 이 선택 이유는 여러 절대정보 묶음에 근거하므로 mixed가 맞다.

다만 실제 실행 순서는 다음과 같다.

```text
L1 -> 예산 계획 -> ToolCatalog -> LToolScope -> 예산 분할 -> L2
```

`LToolScope`가 L2보다 먼저 허용 도구군을 필터링한다. 현재 도구군은 문서, 코드 검사,
runtime record뿐이고 시간 도구군이나 capability tag가 없다. 따라서 시간 도구를 추가할
때 LToolScope가 이를 가리지 않도록 해야 한다. 가장 안전한 책임 분리는 다음과 같다.

- L1: 시간 근거가 필요한지 판단
- LToolScope: 시간 도구가 L2에게 보일 수 있는 권한만 보존
- L2: 실제 시간 도구 사용 여부와 구체 도구 선택

LToolScope가 시간 필요성을 다시 의미 판단하면 L1/L2와 책임이 중복된다.

## 4. 현재 존재하는 시간 절대정보

### 사용할 수 있는 기반

`WorkspaceManifestFrame`에는 다음 절대정보가 이미 있다.

- manifest `observed_at`
- 파일별 `modified_at_utc`
- 파일별 `content_hash`
- 상대경로, source kind, 크기

그래프 source ingest와 lineage에는 다음 값이 있다.

- `observed_at`
- `source_last_modified_at`
- source version과 content hash
- validity/invalidation 계보

### L루프에서 직접 쓰지 못하는 부분

- WorkspaceManifest는 사용자가 `--workspace`를 지정한 경우에만 생성된다.
- L1/L2에는 manifest ID가 전달될 수 있지만 manifest의 시간 필드 본문은 공급되지 않는다.
- `list_docs`, `read_doc`, `search_docs` 결과에는 source 수정 시각이 없다.
- `list_code_files`, `read_code_file` 결과에도 source 수정 시각이 없다.
- 문서 snapshot은 content hash 기반 변경 감지는 하지만 관측 시각과 파일 수정 시각을
  L 검색 후보에 노출하지 않는다.
- Trace/DataStore의 `created_at`은 이번 실행 record가 만들어진 시각이지, 원본 문서가
  최신이라는 증거가 아니다.
- Git commit/history를 읽는 L 도구는 없다.
- R/Vessel의 시간축 정보는 이미 존재하지만 L ToolCatalog에는 연결되지 않는다.

## 5. 도구 실행 경로의 현재 한계

현재 다음 부분은 지원 도구 이름을 고정 집합으로 다룬다.

- `ToolCatalogItem`: capability tag가 없음
- `L2QueryFrame`과 `L2QueryPlanFrame`: 시간 도구 이름과 query mode가 없음
- L 초기 tool executor: 문서/코드 도구만 분기 실행
- revision tool executor: 동일한 고정 도구만 허용
- tool result distiller: 기존 여섯 종류 결과만 처리
- L3: read_doc/read_code_file 원문과 search 후보 중심으로 성공 여부를 계산
- node_0/node_2/node_3: 시간 근거 packet/count/status가 없음

따라서 시간 도구 하나를 registry에 등록하는 것만으로는 완성되지 않는다. 실행, 요약,
revision read, L3 목표 검사, downstream 전달까지 계약이 필요하다.

## 6. 권장 구현 순서

### 1단계: 시간 요구 계약

L1에 최소한 다음 의미 판단을 추가한다.

- `temporal_requirement_status=required|not_required|uncertain`
- `temporal_evidence_goal`
- `temporal_requirement_reason`
- 현재 사용자 입력 trace에 대응하는 source anchor

이 단계에서는 시간 도구를 실행하지 않고 판단 기록과 fallback 정직성만 검증한다.

### 2단계: 시간 capability와 절대정보 도구

- ToolCatalog에 시간 capability를 명시한다.
- workspace/source manifest 기반 읽기 전용 시간 metadata 도구를 만든다.
- 도구는 정렬 결과, 경로, 수정 시각, 관측 시각, hash만 반환한다.
- 어떤 시각을 중요하게 볼지는 CODE가 추측하지 않는다.

### 3단계: L2 선택과 원문 읽기 연결

- L2가 L1 시간 요구, ToolCatalog, budget을 보고 시간 도구 사용 여부를 판단한다.
- 시간 후보와 실제 원문 읽기를 구분한다.
- revision L2가 허용된 시간 후보의 정확한 문서/코드 경로를 선택해 원문을 읽게 한다.
- L3는 시간 metadata 확보와 원문 확보를 별도 절대상태로 기록한다.

## 7. 남은 사용자 결재

1. `최신`의 기본 기준을 source 수정 시각, 송련 관측 시각, graph ingest 시각 중 무엇으로
   볼지, 또는 L1이 질문마다 선택하게 할지.
2. 시간 도구가 현재 디스크만 볼지, Git history까지 볼지.
3. `required`인데 L2가 시간 도구를 쓰지 않았을 때 구조 실패, partial, 명시적 충돌 중
   어떤 상태로 닫을지.
4. 현재 디스크 시간 조사는 L, 이미 적재된 과거 이력 탐색은 R이라는 경계를 유지할지.

## 8. 최종 판정

사용자 제안은 SongRyeon의 권한 분리에 잘 맞는다. 다만 기존 `LToolScope`와 책임을
겹치지 않게 해야 하며, 시간 절대정보가 있다는 사실과 L루프가 그것을 실제로 공급받는
것은 구분해야 한다. 현재는 기반 데이터는 일부 존재하지만 L1 판단, L2 선택, 시간 도구,
L3/downstream 전달이 아직 연결되지 않았다.
