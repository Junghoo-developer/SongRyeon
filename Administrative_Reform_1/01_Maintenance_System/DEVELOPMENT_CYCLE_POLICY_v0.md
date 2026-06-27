# Development Cycle Policy v0

## 상태

이 문서는 영구 유지 체계 문서다.

SongRyeon Core는 앞으로 다음 3단계 주기를 기본 개발 단위로 삼는다.

```text
1. 뚜렷한 목표 지정
2. MVP 구현
3. 학습 회고
```

## 왜 필요한가

이번 연습판은 처음부터 목표가 완전히 고정되어 있지 않았지만, 운 좋게 다음 성과를 얻었다.

- Qwen 14B 로컬 호출
- 내부 문서 검색 L루프
- trace/data 기록
- LLM/코드/도구 생성 정보 구분
- 절대/상대/혼합 정보 라벨
- pretty runtime 출력
- node_4 gatekeeper 기초

그러나 다음부터는 운에 기대지 않는다.

새 기능은 반드시 명확한 목표, 작은 MVP, 학습 회고를 통과해야 한다.

## 1단계: 뚜렷한 목표 지정

코딩 전에 반드시 다음 질문에 답한다.

```text
이번 작업의 목표는 무엇인가?
이번 작업으로 사용자가 직접 확인할 수 있는 변화는 무엇인가?
이번 작업이 건드리는 노드/루프/도구/문서는 무엇인가?
절대정보, 상대정보, 혼합정보 중 무엇을 새로 만들거나 바꾸는가?
LLM이 판단해야 하는 부분과 코드가 강제해야 하는 부분은 무엇인가?
완료 기준은 무엇인가?
이번 턴에서 하지 않을 것은 무엇인가?
```

목표 지정이 불명확하면 코딩하지 않는다.

대신 철학, 유지 체계, 지도, 발주서 중 맞는 계층에 정리한다.

## 2단계: MVP 구현

MVP 구현은 다음 원칙을 따른다.

1. 발주서 또는 명확한 작업 문서가 있어야 한다.
2. 한 번에 하나의 주요 권한 경계만 바꾼다.
3. 스키마를 먼저 만들고, 그 다음 노드/런타임 배선을 만든다.
4. LLM 판단과 코드 강제를 분리한다.
5. 코드 fallback은 의미 판단인 척하지 않고 `CODE_STATUS`를 드러낸다.
6. pretty runtime에서 사용자가 꼭 봐야 할 내부 처리를 확인할 수 있어야 한다.
7. smoke test 또는 재현 명령을 남긴다.

## 검증 계층

ORDER_117 이후 로컬 개발과 CI의 기본 기준선은 다음 순서다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

계층 이름:

```text
compileall: 문법/임포트 최소 검사
pytest: 단위/도메인 회귀 검사
smoke-test: 통합 런타임 기준선 검사
qwen-turn/qwen-chat: 수동 live LLM 검사
```

작은 변경 전후에는 관련 pytest를 먼저 실행한다.
구조 변경 후에는 전체 `python -m pytest`를 실행한다.
release/public 기준선 전에는 `python main.py smoke-test`까지 실행한다.
Qwen/Ollama live test는 로컬 수동 검사로 분리하고 CI 필수 조건으로 넣지 않는다.

ORDER_112 같은 기능 구현은 다음 조건을 만족한 뒤 재개한다.

- pytest baseline 존재
- schema split 계획 또는 최소 1차 완료
- smoke decomposition 시작
- CI가 pytest와 smoke-test를 모두 실행

## 3단계: 학습 회고

MVP 구현 후에는 다음을 기록한다.

```text
무엇이 실제로 작동했는가?
무엇이 아직 기만적이거나 애매한가?
어떤 문장은 LLM이 썼고, 어떤 정보는 코드/도구가 만들었는가?
사용자가 직접 배워야 할 핵심 파일은 무엇인가?
다음 목표 후보는 무엇인가?
지금 멈춰도 되는가, 아니면 반드시 이어서 고쳐야 하는가?
```

회고는 `05_Execution_Records/`에 남긴다.

## 금지

1. 목표 지정 없이 새 루프를 추가하지 않는다.
2. 발주서 없이 대규모 구조 변경을 하지 않는다.
3. 코드가 LLM 의미 판단을 흉내 내지 않는다.
4. `pass` 상태를 실제 검증 성공처럼 꾸미지 않는다.
5. 내부 ID나 스키마 용어를 최종 사용자 답변에 무심코 노출하지 않는다.
6. R/W/C/M 같은 미래 루프를 이름만 먼저 live route로 열지 않는다.

## 다음 기준선

ORDER_113~117 재정립 이후 다음 기능 개발 후보는 ORDER_112다.

```text
1. ORDER_112: explicit artifact priority and whole-document packing
2. 후속 schema split 지속
3. 후속 smoke case decomposition 지속
4. 이후 W/R loop, scheduler, 외부 DB/vector DB 후보 재검토
```

다만 이 순서는 코딩 명령이 아니다.

다음 작업을 시작할 때 사용자가 목표를 다시 지정하고, 그 목표에 맞춰 필요한 발주서만 선택한다.
