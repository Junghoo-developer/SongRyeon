# ORDER 266: Competition Reviewer Demo And Product Positioning v0

## 1. 배경

SongRyeon Core는 2026 오픈소스 개발자대회 출품을 앞두고 있다. 기존 `fake-turn`,
pytest, smoke-test는 개발 기준선으로는 유용하지만, 심사자가 첫 3분 안에 프로젝트의
차이를 확인하기에는 출력과 내부 용어가 많다.

또한 현재 코드 가드는 모든 환각이나 의미 오류를 해결하지 않는다. 코드가 확정할 수 있는
문서 역할, 실제 원문 읽기 여부, count와 같은 구조적 충돌을 검사한다. 이 경계를 과장하지
않고 재현 가능한 한 화면으로 보여줄 필요가 있다.

## 2. 목표

SongRyeon Core를 다음 문장으로 설명하고, 한 명령으로 세 가지 신뢰 경계를 재현한다.

> 작은 로컬 모델이 무엇을 검색했고 실제로 무엇을 읽었는지 보여주고, 코드가 확인한
> 사실과 모델 해석을 분리하며, 명시적 근거 역할 충돌을 공개 전에 차단하는 조사 에이전트.

실행 명령:

```powershell
python main.py competition-demo
```

## 3. 구현 범위

1. 외부 API와 Neo4j 없이 결정론적으로 실행되는 세 장면을 제공한다.
   - LOCAL: fake adapter로 전체 node_1 -> node_4 경로를 통과한다.
   - HONEST FALLBACK: node_2 모델 출력이 깨진 JSON일 때 code fallback과 실패 상태를 숨기지 않는다.
   - CODE GUARD: 검색 후보 5개 중 2개만 실제로 읽고, 통제된 모델이 미열람 후보를 읽었다고
     주장하며 pass를 반환해도 문서 역할 code guard가 `needs_revision`으로 바꾼다.
2. 기본 출력은 약 20줄의 심사용 화면으로 제한하고 `--json` 구조 출력을 제공한다.
3. README 첫 화면은 내부 노드 용어보다 다음 사용자 언어를 먼저 쓴다.
   - 코드가 확인함
   - 모델이 해석함
   - 공개 가능
   - 수정 필요
4. `DEMO.md`에 3분 시연 대본과 각 장면이 증명하는 범위를 기록한다.
5. 제출 보고서 골격과 제3자 구성요소 공개 문서를 현재 의존성 기준으로 정리한다.

## 4. 절대/상대 정보 경계

- 후보 수, 실제 `read_doc` 수, 미열람 후보 수, fallback 생성자, gate 상태는 code-owned 절대정보다.
- 모델이 문서를 읽었다고 쓴 문장은 통제된 LLM 출력 역할의 테스트 데이터다.
- code guard는 명시적 문서 역할 충돌만 검사한다.
- 데모는 실제 모델 품질 비교, 일반 환각 탐지, 답변 진실성 전체 검증을 증명하지 않는다.

## 5. 금지

- L/R/기억/그래프 기능 확장
- 실제 외부 API 또는 Neo4j를 필수 조건으로 만들기
- 의미 판단을 code fallback으로 생성하기
- 모델 성능 비교처럼 결정론적 테스트를 표현하기
- 모든 환각을 차단한다고 주장하기
- 전체 trace/data 장부를 삭제하기

## 6. 완료 조건

1. `python main.py competition-demo`가 세 장면 PASS와 전체 성공 상태를 출력한다.
2. `python main.py competition-demo --json`이 같은 결과를 구조화 출력한다.
3. CODE GUARD 장면에 후보 5개, 실제 원문 읽기 2개, 미열람 후보 3개가 표시된다.
4. 통제된 LLM gate의 pass와 최종 code-augmented gate의 needs_revision이 함께 보존된다.
5. README 한글/영문, `DEMO.md`, 제출 보고서 골격, 제3자 고지가 서로 모순되지 않는다.
6. `python -m compileall songryeon_core main.py` 통과.
7. `python -m pytest` 통과.
8. `python main.py smoke-test` 통과.
9. 검증 전에는 커밋하거나 원격으로 push하지 않는다.
