# 2026 오픈소스 개발자대회 결과보고서 골격

이 문서는 최종 제출 양식에 옮기기 전, 주장과 증거가 어긋나지 않게 만드는 작성 기준선이다.
빈칸은 실제 제출 시점의 측정값으로 채우고, 검증하지 않은 수치는 쓰지 않는다.

## 1. 프로젝트 한 문장

SongRyeon Core는 작은 로컬 모델이 무엇을 검색했고 실제로 무엇을 읽었는지 보여주고,
코드가 확인한 사실과 모델 해석을 분리하며, 명시적인 근거 역할 충돌을 공개 전에 차단하는
문서·코드 조사 에이전트다.

태그라인:

> 더 똑똑한 답변보다, 무엇을 읽었고 어디까지 믿을 수 있는지 보여주는 로컬 에이전트.

## 2. 문제 사례

### 문제

일반적인 LLM 에이전트는 검색 후보, 실제 원문 읽기, 모델 해석을 한 문장에 섞을 수 있다.
예를 들어 검색 결과에 이름만 등장한 문서를 실제로 읽었다고 표현하면, 사용자는 답변의
근거 범위를 확인하기 어렵다.

### 통제 사례

- 검색 후보: 5개
- 실제 `read_doc`: 2개
- 미열람 후보: 3개
- 통제된 모델 주장: 미열람 후보 하나를 실제로 읽었다고 명시
- 통제된 모델 gate: `pass`
- 최종 CODE 보강 gate: `needs_revision`
- 사용자 공개: `blocked`

위 수치는 `python main.py competition-demo --json`의 code-owned 장부에서 가져온다.

## 3. 해결 구조: 권한 분리

| 책임 | 담당 | 예시 |
| --- | --- | --- |
| 존재·수량·실행 여부 확인 | 코드/도구 | 후보 수, 실제 read_doc 수, trace ID, schema 통과 여부 |
| 문서 의미 해석과 답변 작성 | LLM 노드 | 요약, 평가, 설명, 답변 문장 |
| 명시적 구조 충돌 검사 | CODE guard | 미열람 후보를 읽었다는 주장, grounding count 불일치 |
| 최종 책임 | 사용자/검수자 | 공개 여부와 실제 업무 적용 결정 |

내부의 절대·상대·혼합 정보 분류는 이 권한 분리를 추적하는 메타정보 체계다. 첫 화면에서는
이를 “코드가 확인함 / 모델이 해석함 / 공개 가능 / 수정 필요”로 번역해 보여준다.

## 4. 통제 비교 실험

한 명령에서 다음 세 조건을 같은 코드베이스로 재현한다.

1. `LOCAL`: 외부 API와 Neo4j 없이 로컬 보고·검사 경로 완료.
2. `HONEST FALLBACK`: 깨진 모델 JSON을 정상 판단처럼 숨기지 않고
   `CODE:FALLBACK`, `semantic=failed`, `parse_failed`로 기록.
3. `CODE GUARD`: 통제된 모델이 잘못된 문서 역할을 주장하고 gate를 통과시켜도,
   code-owned 장부와 대조해 공개 차단.

이 실험은 실제 모델 성능 우열 비교가 아니라 실패·출처·차단 경계의 재현 실험이다.

## 5. 측정 지표

최종 제출 직전에 아래 명령을 다시 실행하고 날짜, commit, 결과를 기록한다.

```powershell
python main.py competition-demo --json
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

| 지표 | 제출 값 |
| --- | --- |
| 검증 commit | `<commit>` |
| 검증 날짜 | `<YYYY-MM-DD>` |
| competition-demo | `<status>` |
| 외부 API 호출 | `0` |
| Neo4j 연결 | `0` |
| pytest | `<passed / deselected>` |
| smoke-test | `<status>` |
| CODE GUARD 후보/실제읽기/미열람 | `5 / 2 / 3` |
| CODE GUARD 최종 gate | `needs_revision` |

## 6. 재현성

최소 재현 환경:

1. 저장소 복제.
2. Python 개발 의존성 설치.
3. `python main.py competition-demo` 실행.
4. 필요하면 `--json`으로 절대 필드 확인.

선택 기능인 Qwen/Ollama, OpenAI/Codex, Neo4j Vessel은 첫 심사 재현의 필수 조건이 아니다.
각 선택 기능의 설정과 실패 상태는 `DEMO.md`와 `THIRD_PARTY_LICENSES.md`에 분리한다.

## 7. 오픈소스 구성

- 프로젝트 코드: MIT License.
- 모델 가중치: 저장소에 미포함.
- 제3자 구성요소: `THIRD_PARTY_LICENSES.md`에 역할, 번들 여부, 검증 상태 기록.
- CI: compileall -> pytest -> smoke-test 순서.

## 8. 한계

현재 증명 가능한 범위:

- 검색 후보와 실제 원문 읽기의 분리.
- code-owned count와 생성자 상태의 추적.
- 명시적 문서 역할 충돌과 일부 구조적 count 충돌의 공개 차단.
- fallback이 LLM 판단인 척하지 않도록 기록.

현재 증명하지 않는 범위:

- 모든 환각의 탐지 또는 제거.
- 일반 의미 진실성 자동 판정.
- 모든 질문에 대한 답변 정확성.
- 선택 기능인 Neo4j/R traversal과 외부 모델의 무설정 재현.
- 사람의 최종 검수와 책임 대체.

## 9. 3분 영상 구성

정확한 대본은 `DEMO.md`의 `Three-Minute Reviewer Script`를 따른다.

1. 30초: 문제와 제품 한 문장.
2. 30초: `competition-demo` 실행.
3. 30초: LOCAL.
4. 30초: HONEST FALLBACK.
5. 40초: CODE GUARD의 5/2/3 장부와 차단.
6. 20초: 재현 명령과 한계.

## 10. 제출 전 주장 검사

- [ ] “모든 환각을 막는다”라고 쓰지 않았다.
- [ ] 결정론적 테스트를 실제 모델 성능 비교라고 부르지 않았다.
- [ ] 검색 후보 수를 읽은 문서 수라고 쓰지 않았다.
- [ ] 로컬에서 확인하지 않은 CI/pytest 수를 적지 않았다.
- [ ] 선택 기능을 기본 필수 기능처럼 표현하지 않았다.
- [ ] 제3자 라이선스 미확인 항목을 확정 표현하지 않았다.
