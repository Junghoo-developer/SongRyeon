# ORDER 267 External Workspace Read-Only Boundary 실행 기록

## 1. 실행 일자

- 2026-07-18

## 2. 작업 배경

SongRyeon Core는 자체 저장소의 내부 문서와 코드를 조사할 수 있었지만, 사용자가
선택한 일반 업무 폴더를 제품 경계 안에서 안전하게 연결하는 기능은 없었다.
기존 심야 소스 manifest도 송련 전용 경로와 glob에 묶여 있어 이를 일반 업무 폴더
기능이라고 부를 수 없었다.

이번 작업은 새 검색 엔진이나 자동 수집기를 만드는 대신, 기존 L루프에 명시적으로
선택된 폴더를 읽기 전용으로 연결하는 최소 경계를 구현했다.

## 3. 구현 내용

### 3.1 code-owned workspace manifest

`WorkspaceManifestFrame`이 다음 절대정보를 기록한다.

- workspace root와 사람이 보는 label
- 지원 파일의 상대 경로, source kind, 확장자, 크기, UTC 수정 시각, SHA-256
- 후보 파일 수와 종류별 수
- 제외 파일/폴더 수와 명시적 제외 이유 수
- `read_only`, `local_model_only`, `automatic_graph_ingest_status=not_run`

manifest는 TraceStore/DataStore에 기록되고 node_0 pre-route memory packet에는 manifest
좌표와 count가 복사된다. node_1에는 root 절대경로나 hash 전문이 아니라 활성 workspace의
label, 후보 수, 종류, 확장자, 접근 방식만 공급된다.

### 3.2 읽기 전용 L루프 연결

사용자가 workspace를 선택하면 L루프의 문서 root와 코드 root가 같은 workspace로
정렬된다.

- 문서 도구: `.md`, `.txt`
- 코드/설정 도구: `.py`, `.json`, `.toml`, `.yaml`, `.yml`

manifest의 후보 수는 실제 원문 읽기 수가 아니다. 실제 읽기는 기존 tool result 장부로
별도 기록된다. 어떤 파일이 질문과 관련 있는지는 L1/L2/L3의 LLM 판단으로 남겼고,
code는 파일명 단어로 관련성을 추측하지 않는다.

### 3.3 보안과 제품 경계

- `.env`와 명시된 비밀키 이름/접미사를 제외한다.
- `.git`, 가상환경, cache, build 산출물 폴더를 명시 정책으로 제외한다.
- workspace 밖 경로와 symbolic-link 탈출을 차단한다.
- 파일을 복사, 수정, 삭제, 이동하지 않는다.
- `--workspace`는 fake/Qwen 로컬 명령에만 제공한다.
- OpenAI/Codex/hybrid 외부 API 명령에는 workspace 옵션을 열지 않는다.
- workspace가 활성화된 Qwen HTTP endpoint는 loopback 주소만 허용하고 원격 주소는
  LLM 호출 전에 차단한다.
- Neo4j와 심야정부에는 자동 적재하지 않는다.

## 4. 사용자 진입점

LLM 호출 없이 먼저 경계를 확인한다.

```powershell
python main.py workspace-check "C:\path\to\work"
```

로컬 Qwen 대화에 연결한다.

```powershell
python main.py qwen-chat --workspace "C:\path\to\work"
```

매번 옵션을 쓰지 않으려면 `SONGRYEON_WORKSPACE_ROOT`를 로컬 환경에 설정한 뒤
`python main.py`로 실행할 수 있다.

## 5. 성능 문제와 수정

첫 구현은 각 파일마다 모든 부모 경로를 반복 확인했다. 저장소 전체 pytest가 약
604초 후 timeout 되었고, graph fast-test도 약 90초가 걸렸다.

이를 하나의 `os.walk` 순회에서 제외 폴더와 symbolic-link 디렉터리를 미리 잘라내는
방식으로 바꿨다. 보안 경계를 유지하면서 graph fast-test는 29.85초로 줄었고 전체
pytest도 완료됐다. 검증 지연을 기능 비용으로 숨기지 않고 실행 기록에 남긴다.

## 6. 검증 결과

```text
python -m compileall songryeon_core main.py
-> passed

python -m pytest tests/test_order_267_external_workspace_read_only_boundary.py -q
-> 7 passed, 1 skipped

python main.py fast-test --profile graph --skip-compileall
-> FAST_TEST_OK
-> 148 passed in 29.85s

python -m pytest
-> 485 passed, 1 skipped, 5 deselected in 144.01s

python main.py smoke-test
-> SMOKE_TEST_OK in 156.7s

python main.py competition-demo
-> SONGRYEON_COMPETITION_DEMO_OK
-> LOCAL PASS
-> HONEST FALLBACK PASS
-> CODE GUARD PASS
```

Windows 로컬 환경에서는 symbolic-link 생성 권한이 없어 해당 pytest 하나가 skip됐다.
실제 차단 코드는 구현되어 있으며 symbolic link를 만들 수 있는 CI/Linux 환경에서는
같은 테스트가 실행 대상이다.

첫 수동 `workspace-check .`에서 이름이 `ci-venv`인 실제 Python 가상환경이 후보에
포함되는 추가 빈틈을 발견했다. 정확한 폴더명 목록만 보지 않고 Python이 생성한
`pyvenv.cfg` 구조 표지를 확인하도록 보강했다. 수정 후 다시 측정한 최종 수치는 아래에
기록한다.

```text
status = WORKSPACE_CHECK_OK
candidate_file_count = 941
workspace_document = 640
workspace_code_or_config = 301
excluded_file_count = 15
excluded_directory_count = 16
automatic_graph_ingest_status = not_run
generated_by = CODE:WORKSPACE_MANIFEST_BUILDER
```

## 7. 일부러 하지 않은 것

- PDF, Word, Excel, 이미지, binary 파싱
- 의미 기반 비밀정보 탐지
- workspace 자동 수정
- 외부 API로 workspace 원문 전송
- Neo4j/심야정부 자동 적재
- GUI 업로드
- 기존 송련 전용 source manifest 대체

## 8. 남은 위험

1. 첫 보안 정책은 명시된 파일명, 접미사, 폴더 목록만 차단한다. 일반적인 비밀정보
   탐지기라고 주장할 수 없다.
2. 매우 큰 업무 폴더에서는 manifest hash 계산 자체가 시간이 걸릴 수 있다.
3. Windows 로컬 symbolic-link 테스트는 권한 때문에 이번 기준선에서 직접 실행되지 않았다.
4. 실제 Qwen이 외부 업무 폴더에서 파일을 얼마나 잘 고르는지는 별도 live 품질 시험이
   필요하다.

## 9. 실제 Qwen workspace 시험

저장소 안의 `songryeon_core/tools` 폴더를 실제 업무 폴더 역할로 연결했다.

```text
python main.py workspace-check songryeon_core\tools
-> status = WORKSPACE_CHECK_OK
-> candidate_file_count = 15
-> workspace_code_or_config = 15
-> excluded_directory_count = 1
-> automatic_graph_ingest_status = not_run

python main.py qwen-turn "workspace_policy.py를 실제로 읽고 설명해줘..." \
  --workspace "songryeon_core\tools" --force-l --timeout 180 --pretty
-> elapsed = 214.4s
-> runtime status = model_fallback
-> route = L -> 2
-> accumulated code candidates = 15
-> actual read_code_file unique files/calls = 1/1
-> node_3 source-code contexts = 1
-> node_4 gate = pass
```

Qwen 최종 답변은 실제로 읽은 `workspace_policy.py` 원문을 바탕으로 지원 확장자와
loopback endpoint 제한을 설명했고, 후보 발견과 실제 원문 읽기를 분리해 표시했다.

동시에 다음 안정성 관찰값을 남긴다.

1. 최초 L2 plan은 `LLM_PLAN=not_available`로 code fallback을 기록했고, revision 경로에서
   `list_code_files -> read_code_file -> search_code`로 이어졌다.
2. 후속 감사 결과 원문 데이터 손실은 없었다. terminal의 일반 라벨 `L3 달성 판단`이
   revision 전 최초 `L3:achievement_frame`만 표시해 최종 상태처럼 오해하게 만들었다.
   revision 2·3회차와 node_0 누적 return summary에는
   `original_material_acquired`와 코드 원문 1개가 보존됐고, node_2/node_3도 그 누적값을
   사용했다. 수정 대상은 근거 장부가 아니라 terminal의 최초/최신 표시 구분이다.
3. 사용자 입력의 `workspace_policy.py를`처럼 한글 조사가 경로 바로 뒤에 붙으면 현재
   path token 검사가 `를`도 영숫자로 취급해 명시 경로 감지 결과가 빈 목록이 된다.
   같은 문장을 `workspace_policy.py 를`로 띄우면 정확 경로가 감지되는 것을 작은 재현으로
   확인했다. 이 때문에 최초 code path 직행 fallback이 작동하지 못했다.
4. 최초 L2와 revision L3의 예외는 상위 L루프에서 넓은 `except Exception`으로 fallback
   처리된다. LLM call record는 남을 수 있지만 terminal에는 정확한 failure type이 연결되지
   않아 이번 출력만으로 parse/schema/adapter 중 무엇이 실패했는지 확정할 수 없다.
5. 이번 경로는 최초 L2/L3과 3회의 revision L2/L3, 후속 node_1, node_2 두 판단,
   node_3, node_4 등 최소 15회의 Qwen 호출을 시도하는 구조였다. 따라서 214.4초는 단일
   파일 읽기 자체보다 여러 순차 LLM 호출이 누적된 결과로 보는 것이 맞다.
6. 15개 파일 workspace에서 한 파일을 읽고 답하는 데 214.4초가 걸렸다. 기능 존재와
   제품 응답 속도는 분리해 평가해야 한다.

## 10. 판정

ORDER 267의 읽기 전용 외부 workspace 경계와 로컬 검증은 완료됐다. 이제 새 기능을
더 늘리기보다 대표 업무 폴더를 대상으로 live 안정성, 실패 정직성, 실제 원문 읽기
비율을 측정할 단계다.
