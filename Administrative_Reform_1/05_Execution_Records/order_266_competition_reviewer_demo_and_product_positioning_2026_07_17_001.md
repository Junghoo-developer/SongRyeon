# ORDER 266 Competition Reviewer Demo And Product Positioning 실행 기록

## 1. 실행 일자

- 2026-07-17

## 2. 작업 배경

다른 작업 스레드에서 `competition-demo` 초안이 시작됐으나 CODE GUARD 장면이
`pass`로 끝나며 표적 테스트 2개가 실패한 상태로 Core 총괄에 인계됐다.

인계 시 미커밋 변경:

- `main.py`
- `songryeon_core/runtime/competition_demo.py`
- `tests/test_order_265_competition_demo.py`

ORDER 265는 이미 GitHub Actions Node 24 유지보수에 사용됐으므로 새 작업 번호는
ORDER 266으로 확정했다.

## 3. 원인 감사

Node4의 `CODE:DOCUMENT_EVIDENCE_ROLE_GUARD`는 정상 동작했다. 실패 원인은 시연 입력이었다.

- 초안 검색 후보: 5개
- 초안 실제 `read_doc`: 5개
- 초안 미열람 후보: 0개

미열람 후보가 없었으므로 통제된 node_3 adapter가 역할 충돌 문장을 만들 수 없었고,
code guard가 차단할 모순도 없었다.

## 4. 살린 것

1. `python main.py competition-demo` 한 명령 진입점.
2. 외부 API와 Neo4j 없이 도는 결정론적 세 장면.
3. 짧은 기본 화면과 `--json` 구조 출력.
4. 실제 `run_dry_turn`과 node_2/node_3/node_4 경계를 통과하는 통합 시연.

## 5. 고친 것

CODE GUARD 시연의 code-owned 예산을 다음처럼 명시했다.

- `search_top_k=5`
- `max_read_doc_calls=2`

따라서 장부는 후보 5개, 실제 원문 읽기 2개, 미열람 후보 3개를 결정론적으로 만든다.
통제된 node_3 adapter는 미열람 후보 하나를 실제로 읽었다고 명시하고, 통제된 node_4
LLM 판단은 `pass`를 반환한다. 이후 기존 code guard가 최종 gate를 `needs_revision`으로
바꾸고 공개 상태를 `blocked`로 닫는다.

`public_answer=blocked`는 gate 값만 다시 이름 붙인 것이 아니다. 실제
`render_chat_answer()`를 실행해 `FINAL_BLOCKED_BY_GATEKEEPER` 표시가 생성된 경우에만
기록한다.

테스트 파일은 번호 충돌을 피하려고 `test_order_266_competition_demo.py`로 옮겼다.

## 6. 버린 것과 금지한 주장

- Node4 helper만 직접 호출하는 더 작은 단위 시연은 채택하지 않았다. 실제 통합 장부를
  통과하는 시연을 유지했다.
- L/R/기억/Neo4j 기능은 확장하지 않았다.
- 결정론적 테스트를 실제 Qwen 성능 비교라고 표현하지 않았다.
- 일반 환각 탐지 또는 의미 진실성 전체 검증이라고 주장하지 않았다.
- 검색 후보 수를 읽은 문서 수로 표현하지 않았다.

## 7. 공개 문서 정리

- README 한글/영문 첫 화면을 “감사 가능한 로컬 문서·코드 조사 에이전트”로 정렬.
- 내부 용어보다 “코드가 확인함 / 모델이 해석함 / 공개 가능 / 수정 필요”를 먼저 표시.
- `DEMO.md`에 3분 심사 대본 추가.
- `COMPETITION_SUBMISSION_REPORT_OUTLINE.md`에 결과보고서 골격과 주장 금지 목록 추가.
- `THIRD_PARTY_LICENSES.md`에 번들 여부, 요구 버전과 로컬 관측 버전, 라이선스 확인
  상태를 분리해 기록.

라이선스 감사에서 `openai-codex==0.1.0b3`의 설치 wheel metadata에는 라이선스가
기재되지 않은 것을 확인했다. 공식 Codex CLI 저장소의 Apache-2.0을 이 별도 Python
배포물에 자동 적용하지 않고, 재배포 전 재검증 대상으로 남겼다.

## 8. 검증 결과

```text
python main.py competition-demo
-> SONGRYEON_COMPETITION_DEMO_OK
-> LOCAL PASS
-> HONEST FALLBACK PASS
-> CODE GUARD PASS
-> candidates/read/unread = 5/2/3
-> final_gate = needs_revision
-> public_answer = blocked

python main.py competition-demo --json
-> passed = true
-> external_api_calls = 0
-> neo4j_connections = 0

python -m pytest tests/test_order_266_competition_demo.py tests/test_order_130_document_evidence_role_claim_guard.py -q
-> 6 passed in 32.41s

python -m compileall songryeon_core main.py
-> passed

python -m pytest
-> 478 passed, 5 deselected in 282.98s

python main.py smoke-test
-> SMOKE_TEST_OK in 254.8s

python main.py fast-test --profile graph
-> FAST_TEST_OK
-> 148 passed in 51.50s
```

## 9. 남은 일

1. push 뒤 GitHub Actions 원격 결과를 확인한다.
2. 3분 영상은 `DEMO.md` 대본대로 실제 녹화한다.
3. 제출 직전 결과보고서의 commit, 날짜, 검증 수치를 다시 측정해 채운다.
4. `openai-codex` Python 배포물을 제출물에 실제로 묶을 경우 정확한 배포 라이선스를
   다시 확인한다.

## 10. 판정

ORDER 266 구현과 로컬 검증은 완료됐다. 새 기능 확장보다 제출 증거, 영상, 보고서의
재현성과 표현 정확도를 유지하는 단계로 전환한다.
