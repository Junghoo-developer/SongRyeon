# ORDER 117: CI And Development Routine Lock v0

## 상태

발주서 초안.

ORDER_114 이후 구현한다.
ORDER_115/116과 병행 가능하지만, 최종 잠금은 그 이후가 좋다.

## 배경

현재 GitHub Actions는 다음만 실행한다.

```text
python -m compileall songryeon_core main.py
python main.py smoke-test
```

pytest 체계가 들어오면 CI와 README의 개발 루틴도 함께 바뀌어야 한다.

그렇지 않으면 로컬에서는 pytest를 돌리는데 CI는 smoke만 돌거나, 반대로 문서에는 pytest가 있는데 CI가 설치하지 않는 불일치가 생긴다.

## 목표

개발 루틴을 다음 기준으로 잠근다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

그리고 이 기준을 CI, README, PUBLICATION_CHECKLIST, 유지 문서에 반영한다.

## 구현 범위

### 1. GitHub Actions 갱신

파일:

```text
.github/workflows/smoke-test.yml
```

권장 단계:

```yaml
- Install test dependencies
- Compile Python files
- Run pytest
- Run smoke tests
```

pytest는 dev/test dependency로 설치한다.

### 2. 문서 갱신

후보 파일:

```text
README.md
README.ko.md
PUBLICATION_CHECKLIST.md
Administrative_Reform_1/01_Maintenance_System/DEVELOPMENT_CYCLE_POLICY_v0.md
```

기록할 개발 루틴:

1. 작은 변경 전후로 대상 pytest 실행
2. 구조 변경 후 전체 pytest 실행
3. release/public 기준선 전 smoke-test 실행
4. Qwen live test는 별도 수동 테스트로 분리

### 3. 테스트 계층 이름 정리

권장 분류:

```text
compileall: 문법/임포트 최소 검사
pytest: 단위/도메인 회귀 검사
smoke-test: 통합 기준선 검사
qwen-turn/qwen-chat: 수동 live LLM 검사
```

### 4. ORDER_112 재개 조건 명시

ORDER_112 같은 기능 구현은 다음을 만족한 뒤 재개한다.

- pytest baseline 존재
- schema split 계획 또는 최소 1차 완료
- smoke decomposition 시작
- CI가 pytest와 smoke-test를 모두 실행

## 금지

- CI에서 Qwen/Ollama live test를 기본 필수로 넣지 않는다.
- smoke-test를 제거하지 않는다.
- pytest만 통과하면 충분하다고 문서화하지 않는다.
- 기능 확장과 CI 잠금을 무리하게 한 커밋에 섞지 않는다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

CI 확인:

- GitHub Actions에서 compileall 통과
- pytest 통과
- smoke-test 통과

완료 보고에는 다음을 적는다.

- 갱신한 CI 파일
- test dependency 설치 방식
- 갱신한 문서 목록
- 로컬 검증 결과
- CI 결과
- ORDER_112 재개 가능 여부
