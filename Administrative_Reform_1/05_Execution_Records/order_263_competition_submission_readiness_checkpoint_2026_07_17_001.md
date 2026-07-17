# ORDER 263 Competition Submission Readiness Checkpoint 실행 기록

## 1. 실행 일자

- 2026-07-17

## 2. 감사 기준

- `2026년 오픈소스 개발자대회 운영규정` 로컬 원본
  - `C:/Users/peter/Downloads/b3b4491a-3bbe-454e-a1d8-6ed475b01b14.pdf`
- 오픈소스 포털의 2026 대회 일정 및 제출물 안내
  - 결과보고서
  - 3분 시연영상
  - 공개 소스코드
- 현재 로컬 Git 상태와 공개 GitHub `main` 상태

## 3. 감사 결론

SongRyeon Core는 로컬 Qwen 경로, 모델 없는 결정론적 데모, MIT 라이선스,
출처 장부, 자동 테스트를 갖고 있어 대회 주제와 기본 공개 요건에 맞는다.

새 기능을 더 넣는 것보다 다음 위험이 더 컸다.

1. 공개 `main`이 로컬 구현보다 크게 뒤처져 있었다.
2. README 기준선이 2026-07-03 / 279 tests로 낡아 있었다.
3. 전체 `--pretty` 출력은 첫 심사 시연에 너무 길었다.
4. 현재 작업 브랜치에는 공개 `main`의 제3자 라이선스 고지 파일이 없었다.
5. 최신 원격 CI는 push 전이므로 통과했다고 말할 수 없었다.

## 4. 구현 내용

1. `--compact` 표시 모드를 fake/qwen turn과 qwen chat 경로에 추가했다.
   - 기존 절대정보 감사판과 최종 답변을 재사용한다.
   - 전체 장부와 trace/data 원본은 result에 보존한다.
   - 새로운 의미 답변을 code가 만들지 않는다.
2. 한글/영문 README에 모델·Neo4j 없는 첫 실행 명령을 추가했다.
3. DEMO 문서에 심사자용 3분 확인 경로를 추가했다.
4. `THIRD_PARTY_LICENSES.md`를 현재 작업 브랜치에 포함했다.
5. Qwen3-14B는 저장소에 가중치를 포함하지 않으며, 공식 모델 카드의 Apache 2.0
   고지와 실제 설치 artifact 재확인 의무를 함께 적었다.
6. README와 릴리즈 노트 기준선을 최신 로컬 검증값으로 갱신했다.
7. 실제 `.env`, `.env.vessel.local.ps1`, cache 디렉터리가 Git에서 제외됨을 확인했다.

## 5. 자동 검증

```text
python -m compileall songryeon_core main.py
passed

python -m pytest tests/test_order_263_competition_submission_readiness.py -q
1 passed

python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --compact
status=ok / node_4=pass / deterministic fake disclosure present

python main.py quick-smoke
QUICK_SMOKE_OK

python -m pytest
476 passed, 5 deselected in 135.49s

python main.py smoke-test
SMOKE_TEST_OK

tracked high-confidence secret pattern scan
NO_HIGH_CONFIDENCE_TRACKED_SECRET_MATCHES
```

## 6. 공개 상태 주의

- 실행 기록 작성 시점의 로컬 HEAD는 공개 `origin/main`보다 22커밋 앞서 있었다.
- `origin/main`도 현재 작업 브랜치보다 라이선스 관련 2커밋 앞서 있었다.
- 따라서 두 흐름을 합치고 push한 뒤 GitHub Actions를 별도로 확인해야 한다.
- 원격 CI 확인 전에는 이 체크포인트의 CI가 통과했다고 기록하지 않는다.

## 7. 중단 판정

이 체크포인트 뒤에는 새 기능 확장을 멈춘다.
다음 대회 작업은 2026-07-23 공개 예정인 세부 평가 기준을 읽고,
결과보고서와 3분 시연영상의 증거 구성을 준비하는 일이다.
