# Three Step Practice Cycle v0

## 목적

이 문서는 앞으로 SongRyeon Core를 다룰 때 사용할 반복 학습 루프다.

핵심은 다음 세 가지다.

```text
뚜렷한 목표 지정
MVP 구현
학습 회고
```

## 0. 시작 전에 멈춤 확인

새 작업을 시작하기 전에 먼저 묻는다.

```text
지금 꼭 코딩해야 하는가?
문서화만으로 충분한가?
이 작업은 현재 기준선을 망칠 위험이 있는가?
사용자가 이 작업을 학습할 준비가 되어 있는가?
```

코딩하지 않아도 되는 턴이면 문서나 회고로 닫는다.

## 1. 목표 지정

목표 지정 문서는 짧아도 된다.

필수 항목:

- 목표
- 이번 MVP에서 사용자가 확인할 변화
- 건드릴 파일
- 새로 생길 스키마/trace/data
- LLM 판단 영역
- 코드 강제 영역
- 완료 기준
- 이번에 하지 않을 것

예시:

```text
목표: node_4가 반려한 답변을 최종 출력하지 않게 한다.
확인 변화: gate_status=needs_revision이면 safe blocking answer가 출력된다.
건드릴 파일: runtime/terminal_view.py, runtime/user_turn.py, smoke_test.py
LLM 판단: node_4 gatekeeper의 pass/needs_revision 판단
코드 강제: needs_revision이면 원문 답변 출력 금지
완료 기준: smoke에서 fake rejected answer가 최종 answer로 나오지 않는다.
하지 않을 것: 자동 재작성 루프는 만들지 않는다.
```

## 2. MVP 구현

MVP는 “가장 작은 살아있는 단위”다.

구현 순서:

```text
스키마
-> 노드/도구 함수
-> runtime 배선
-> pretty 출력
-> smoke
-> 실행 기록
```

이 순서를 깨도 되지만, 깨면 이유를 남긴다.

## 3. 학습 회고

구현 후 회고는 사용자가 다음에 직접 설명할 수 있게 쓰는 문서다.

필수 질문:

- 이번 작업 전에는 무엇이 문제였나?
- 어떤 파일을 바꿨나?
- 데이터가 어떤 순서로 흘렀나?
- LLM이 쓴 문장과 코드가 만든 절대정보는 무엇인가?
- 남은 위험은 무엇인가?
- 다음에 읽을 파일은 무엇인가?

## 현재 추천 다음 사이클

현재 기준선에서 가장 자연스러운 다음 사이클:

```text
목표 지정: node_4 remand blocking
MVP 구현: rejected report를 최종 answer로 출력하지 않기
학습 회고: gatekeeper가 검사만 하는 것과 runtime이 강제하는 것의 차이 설명
```

그 다음 후보:

```text
W1ProblemTriageFrame
W1 LLM node/prompt
W runtime wiring
W smoke/runtime view
```

## 학습자가 처음 볼 파일

처음 학습할 때는 다음 순서로 본다.

```text
1. README.md
2. 01_Maintenance_System/DEVELOPMENT_CYCLE_POLICY_v0.md
3. 03_Maps/02_Function_Maps/CODE_STRUCTURE_MAP_v1.md
4. runtime/user_turn.py
5. runtime/dry_run.py
6. runtime/terminal_view.py
```

`schemas.py`는 중요하지만 크다.

처음부터 전부 외우려 하지 말고, 현재 고치려는 frame만 찾아 읽는다.
