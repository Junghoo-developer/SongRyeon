# 학습 시간 안전 기준선 감사 기록

- 실행일: 2026-07-23
- 시작 체크포인트: `a2dc780`
- 성격: 기능 변경 없는 저부하 안전점검
- 상태: 완료

## 1. 목적

정후가 `SONGRYEON_CORE_CODE_READING_GUIDE_FOR_JUNGHOO_V0.md`를 읽는 동안,
현재 저장소의 재현성과 문서 정합성을 확인했다.

이번 감사에서는 다음을 건드리지 않았다.

- 라우팅, 프롬프트, schema, L/R loop
- Qwen live 실행
- Neo4j/Vessel 데이터
- 외부 API
- 테스트 validator와 성공 기준

## 2. 검증 결과

```text
python -m compileall songryeon_core main.py
통과

python -m pytest tests/test_import_baseline.py tests/test_order_266_competition_demo.py -q
3 passed in 22.97s

python -m pytest -q
548 passed, 2 skipped, 5 deselected in 178.59s

python main.py smoke-test
SMOKE_TEST_OK

python main.py fast-test --profile graph
148 passed / FAST_TEST_OK

python main.py competition-demo
SONGRYEON_COMPETITION_DEMO_OK
```

skip 2개는 Windows 호스트에서 symbolic link 생성이 불가능할 때 사용하는
명시적 환경 skip이다. 테스트 실패로 처리되지 않았다.

competition demo의 세 장면도 다시 재현됐다.

1. 로컬 전체 노드 경로 완료
2. 깨진 LLM JSON을 `CODE:FALLBACK`으로 정직하게 기록
3. 읽지 않은 검색 후보를 읽었다고 주장한 보고문을 CODE guard가 차단

## 3. 문서 정합성

- Git이 추적하는 Markdown: 666개
- 검사한 로컬 상대경로 링크의 깨짐: 0개
- 학습 교재가 인용한 핵심 Python 파일의 누락: 0개
- 학습 교재 Markdown code fence: 84개, 짝 정상

README의 기준선은 2026-07-18, `498 passed`로 남아 있어 현재 코드와
맞지 않았다. 실제 전체 pytest 결과에 맞춰 한글/영문 README를
2026-07-23, `548 passed, 2 skipped, 5 deselected`로 갱신했다.

## 4. 현재 규모 참고

Git이 추적하는 Python 파일 기준:

- 전체: 287개
- `songryeon_core`: 130개
- `tests`: 155개

파일 수는 기능 완성도 점수가 아니다. 현재 기준선은 “코드 전체를 이해했다”는
증명이 아니라, 확인한 회귀검사가 통과했다는 절대정보다.

## 5. 남은 위험

이번 점검만으로 확인하지 않은 범위:

- 실제 Qwen 응답 품질과 장시간 실행 안정성
- Neo4j 인증, 적재 상태, live R traversal
- Windows에서 symbolic link를 사용할 수 있을 때의 2개 테스트
- ORDER 285에 기록된 L1 내부 계약 모순
  (`minimum_read_documents=0`과 `artifact_requirement_mode=exact_one`)

마지막 항목은 발견 사실만 보존했다. 별도 발주와 사용자 결재 없이 자동
패치하지 않았다.

## 6. 학습 포인트

1. `pytest 통과`는 검사한 계약이 보존됐다는 뜻이지 모든 의미 답변이 맞다는
   뜻이 아니다.
2. README의 숫자도 코드가 확정한 최신 실행 결과와 맞아야 한다.
3. live LLM/DB 검증과 결정론적 회귀검사는 서로 다른 증거다.
