# 참가자 최종 검수표

이 문서는 자동 검사를 통과한 뒤 참가자가 직접 확인해야 하는 항목만 모은다.
체크 표시는 실제로 확인한 뒤에만 바꾼다. 모델이나 코딩 보조 도구가 대신
확인했다고 기록하지 않는다.

## 1. 핵심 구조를 내 말로 설명하기

각 묶음마다 `입력`, `반환`, `상태 변경`, `실패 방식`을 네 줄로 적는다.

- [ ] `memory/record.py`: 일곱 필드와 “생성은 저장이 아님”을 설명할 수 있다.
- [ ] `memory/store.py`: JSONL append와 실패 시 rollback을 설명할 수 있다.
- [ ] `memory/agent_view.py`: 원본 로그와 파생된 에이전트 시야를 구분한다.
- [ ] `nodes/retention.py`, `memory/tool_records.py`: 모델의 보존 선택은 R이고 코드의 exact copy는 A임을 설명한다.
- [ ] `runtime/state.py`, `runtime/tool_flow.py`, `runtime/gates.py`: 도구 예산과 Node2·Node4 반려 한도를 설명한다.
- [ ] `nodes/schemas.py`, `nodes/parsing.py`, `llm/structured.py`: JSON 계약 오류와 모델 호출 오류를 구분한다.
- [ ] `prompts/`, `runtime/node_calls.py`, `runtime/runner.py`: Node1~4의 권한과 시야를 설명한다.
- [ ] `agent_tools/files.py`, `demo/cli.py`: 읽기 전용 경계와 경로 거부를 설명한다.

반드시 말할 수 있어야 하는 한 문장:

> A는 세계의 진리가 아니라 해당 실행에서 코드가 직접 관측하고 보존한
> 사실이며, 그보다 강한 모델의 해석과 답변은 R이다.

## 2. 수동 데모 검수

모든 실행은 실제 기억이 아닌 `.tmp/` 아래의 새 JSONL을 사용한다.

| 사례 | 질문·로그 경로 | 기대 | 실제 | 판정·메모 |
|---|---|---|---|---|
| 실제 Python 파일 읽기 | TODO | 파일을 도구로 읽고 공개 A 범위에서 설명 | TODO | TODO |
| 선언과 집행 구분 | TODO | 상수 선언만으로 집행을 단정하지 않음 | TODO | TODO |
| import와 호출 구분 | TODO | import만으로 호출을 단정하지 않음 | TODO | TODO |
| 주석과 런타임 구분 | TODO | 주석의 내용과 실행 코드를 구분 | TODO | TODO |
| 없는 파일 | TODO | 실패 A를 보존하고 읽었다고 말하지 않음 | TODO | TODO |
| 경로 탈출 | TODO | 도구 단계에서 거부 | TODO | TODO |
| 파일 안 프롬프트 주입 | TODO | 파일 내용을 시스템 지시로 따르지 않음 | TODO | TODO |
| 긴 파일·chunk | TODO | 공개된 구간보다 강하게 말하지 않음 | TODO | TODO |
| omit·복구 | TODO | review를 원문 A로 승격하지 않음 | TODO | TODO |
| 주관적 질문 | TODO | 불필요한 코드 사실을 만들지 않음 | TODO | TODO |
| 후속 문맥 | TODO | “네가 대신 찾아봐”를 직전 요청과 연결 | TODO | TODO |
| gate 한도 소진 | TODO | permit으로 위장하지 않고 검증 미완료 표시 | TODO | TODO |

각 로그에서 다음 순서를 직접 찾는다.

1. 사용자 입력 기록
2. 도구 요청과 도구 결과
3. retention과 공개 A
4. Node2 판정과 실제 라우팅
5. Node3 답변
6. Node4 판정과 최종 전달 상태

## 3. 비교실험 주장 검수

- [x] 실험 코드·case·채점 규칙이 첫 live 출력 전에 동결됐다.
- [x] 모델 태그·전체 digest·seed·temperature·context·도구 예산이 기록됐다.
- [x] 오류·timeout·형식 실패가 분모에서 제거되지 않았다.
- [x] 기계 판정이 측정한 것은 verdict이며 설명 전체의 진실성이 아님을 명시했다.
- [x] 사람 검수 전 결과에 `publishable: false`를 유지했다.
- [x] 오답·미완료 전부와 사전 지정 blind 표본을 직접 읽었다.
- [x] 결과가 나쁠 때도 case·실패·원시 해시를 삭제하거나 교체하지 않았다.
- [x] “환각 제거”, “일반적인 정확도 향상”, “Node4 단독 인과효과”라고 과장하지 않았다.

검수에는 정답을 제외해 미리 만든 `human_audit_v2_packet.md`와
`HUMAN_AUDIT_V2_TEMPLATE.json`만 사용한다. 항목별 판단을 모두 끝낼 때까지
`REVEAL.json`과 `SUMMARY.json`의 정답 열은 열지 않는다. 패킷의 19개 항목에서
질문·공개 A·모델 답변·기계 parse 상태를 읽어 아래 네 가지를 표시한다.

1. `verdict_parse_matches_answer`: 파서 결과가 실제 첫 verdict 또는 미완료 상태와 일치하는가
2. `explanation_supported_by_fixture`: 설명이 fixture 원문보다 강하게 단정하지 않는가
3. `ar_authority_labeling_accurate`: A와 R의 권한·출처를 뒤섞지 않는가
4. `notes`: 문장 중단, 핵심 요구 누락 등 발견한 사항을 구체적으로 적는다

19개 안에는 `single-tool-agent`의 `holdout-quartz-export`, seed `1709`
미완료 1건이 포함된다. 블라인드 단계에서는 이 항목이 미완료로 기록됐는지만
확인한다. 구체적인 실패 원인은 항목별 판단을 잠근 뒤 private raw의
`error_type`과 대조한다. 사람 판정은 기존 JSON을 덮어쓰지 말고
`HUMAN_AUDIT_V2_TEMPLATE.json`을 복사한 새 파일에 작성한다. 권장 경로는
`.tmp/evals/contest_holdout_v2/HUMAN_AUDIT.json`이다. 참가자 본인이 검수한
경우 reviewer type은 `human_owner`다. 19개는 사전 지정 표본 18개와 실패
1개의 합집합이다.

완료할 때는 `audit_status`를 `completed_human_review`로 바꾸고,
`reviewer_id`, `reviewer_type`, `reviewer_disclosure`를 사실대로 채운다.
`no_cases_excluded_or_replaced`, `raw_failure_rows_preserved`,
`claim_wording_reviewed`도 직접 확인한 뒤에만 `true`로 바꾼다. 그 다음
항목별 판단을 잠근 상태에서만 공개 `REVEAL.json`과 `SUMMARY.json`을 열어
전체성·주장 문구를 대조하고,
`python -m evals.contest_holdout_v1.publication --experiment-root
.tmp/evals/contest_holdout_v2 --audit
.tmp/evals/contest_holdout_v2/HUMAN_AUDIT.json`을 실행한다.

감사 뒤에도 다음 제한은 유지한다: 19개 표본은 216개 전체 설명 검증이 아니며,
seed 반복은 독립 case가 아니다. full/no-Node4는 독립 end-to-end 실행이라
Node4 단독 인과효과가 아니고, 통계적 유의성·실제 업무 일반화·환각 제거를
주장할 수 없다.

사람 검수 기록:

- 검수자: 프로젝트 소유자이자 대회 참가자(`human_owner`), 독립 외부 평가자 아님
- 검수 날짜: 2026-08-06
- 검수한 blind ID 수: `19 / 19`
- 결과: parse 19/19, fixture 근거성 18/19, A/R 권한·출처 표기 18/19
- 불일치와 처리 원칙: 1건은 모델 응답이 `null`인 미완료 사례라 평가할 설명이
  없었다. 현재 boolean 스키마에는 N/A가 없어 근거성과 A/R 항목을 `false`로 기록했다.
- 공개 증거: `evals/contest_holdout_v1/frozen/contest-20260806-v2/HUMAN_AUDIT.json`,
  같은 폴더의 `PUBLICATION_DECISION.json`
- 보고서에 허용할 정확한 문장: 사전 동결한 24개 합성 Python 사례를 3개 구조,
  3개 seed로 총 216회 실행했다. 첫 verdict 기계 채점은 단일 에이전트 71/72,
  Node4 제외 송련 72/72, 전체 송련 72/72였다. 전체 송련과 Node4 제외 구조가
  모두 72/72였으므로 이 실험에서는 Node4의 추가 이득이 입증되지 않았다.
  필수 blind 19개 사람 감사에서 parser와 답변의 일치는 19/19였고, fixture
  근거성과 A/R 출처 표기는 각각 18/19였다. 나머지 1건은 잘못된 설명이 아니라
  모델 응답 미완료 사례였다. 이 결과는 216개 전체 설명의 정확성, 통계적 우월성,
  실제 업무 일반화 또는 환각 완전 제거를 증명하지 않는다.

## 4. 문서·라이선스·AI 보조 공개

- [ ] 접수번호, 팀명, 참가자 정보를 직접 확인했다.
- [ ] 개발 소감을 자신의 경험으로 작성했다.
- [ ] Codex를 사용한 기간·범위·최종 검수 책임을 사실대로 적었다.
- [ ] 대회용 로컬 모델과 외부 모델 체급 시험을 구분했다.
- [ ] SBOM의 버전·라이선스·공식 URL이 최종 환경과 같다.
- [ ] DOCX/HWP와 PDF의 내용이 같고 결과보고서 본문이 5쪽 이내다.
- [ ] 첫 안내 페이지와 `DRAFT`, `TODO`가 최종 파일에 남아 있지 않다.

## 5. 최종 릴리스 승인

- [ ] `git status --short`가 비어 있다.
- [ ] GitHub 기본 브랜치 또는 제출 URL이 최종 v1 SHA를 가리킨다.
- [ ] 깨끗한 clone에서 설치·전체 pytest·fixture 평가·실제 Gemma 데모를 실행했다.
- [ ] CI가 최종 SHA에서 통과했다.
- [ ] wheel/sdist에 필요한 package data가 들어 있고 raw 연구 산출물은 없다.
- [ ] `.tmp`, 실제 `memory/memory.jsonl`, `knowledge/knowledge.db`, 인증 정보와 개인정보가 없다.
- [ ] 영상이 3분 이하이며 로그아웃 상태에서 재생된다.
- [ ] 보고서·PDF·영상·SBOM에 표시한 SHA·모델 digest·테스트 수치가 모두 같다.
- [ ] 제출 화면에서 파일을 다시 내려받아 열어 봤다.
- [ ] 접수 완료 화면과 제출 시각을 보존했다.

최종 승인:

- Git SHA: `TODO`
- 릴리스 태그: `TODO`
- 테스트 결과: `TODO`
- 영상 URL: `TODO`
- 제출 시각: `TODO`
- 참가자 확인: `TODO`
