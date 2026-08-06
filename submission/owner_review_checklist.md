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

- [ ] 실험 코드·case·채점 규칙이 첫 live 출력 전에 동결됐다.
- [ ] 모델 태그·전체 digest·seed·temperature·context·도구 예산이 기록됐다.
- [ ] 오류·timeout·형식 실패가 분모에서 제거되지 않았다.
- [ ] 기계 판정이 측정한 것은 verdict이며 설명 전체의 진실성이 아님을 명시했다.
- [ ] 사람 검수 전 결과에 `publishable: false`를 유지했다.
- [ ] 오답 전부와 사전 지정 blind 표본을 직접 읽었다.
- [ ] 결과가 나쁠 때도 case·실패·원시 해시를 삭제하거나 교체하지 않았다.
- [ ] “환각 제거”, “일반적인 정확도 향상”, “Node4 단독 인과효과”라고 과장하지 않았다.

사람 검수 기록:

- 검수자: `TODO`
- 검수 날짜: `TODO`
- 검수한 blind ID 수: `TODO`
- 불일치와 처리 원칙: `TODO`
- 보고서에 허용할 정확한 문장: `TODO`

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
