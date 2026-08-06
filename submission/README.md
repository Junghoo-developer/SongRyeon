# 2026 오픈소스 개발자대회 제출 준비 패키지

> 상태: **작성 중인 내부 초안**
>
> 이 폴더의 Markdown 파일은 공식 제출 양식 자체가 아니다. 제출 전 반드시
> 대회가 배포한 결과보고서 DOCX/HWP 양식에 옮기고, 본문 분량과 PDF 변환
> 결과를 다시 확인해야 한다.
>
> **제출 마감: 2026-08-27 18:00.** 참가자 페이지의 최종 공지와 서버 시각을
> 제출 당일 다시 확인하고, 8월 26일까지 업로드를 마치는 것을 목표로 한다.

## 파일 구성

| 파일 | 용도 | 현재 상태 |
|---|---|---|
| `result_report_draft.md` | 결과보고서 본문에 옮길 사실 중심 원고 | 초안 |
| `sbom.md` | 소프트웨어·모델 구성요소 목록 | 버전·라이선스 최종 확인 필요 |
| `ai_model_spec.md` | AI 모델 사용 방식과 실행 경계 | 사용 기간·최종 시연 환경 보완 필요 |
| `demo_script_3min.md` | 3분 이하 YouTube 시연 대본 | 실제 촬영·링크 필요 |
| `live_pilot_notes.md` | Qwen3 동일 backbone 3구조 원시 비교 기록 | 내부 검토용·정량 인용 금지 |
| `../evals/contest_holdout_v1/frozen/contest-20260806-v2/` | 사전 동결·블라인드·점수 잠금·사람 감사·공개 검증 체인 | publication integrity gate 통과 |
| `human_audit_v2_packet.md` | 정답을 숨긴 필수 19개 사람 감사 읽기 묶음 | 참가자 직접 검수 완료 |
| `HUMAN_AUDIT_V2_TEMPLATE.json` | publication gate 입력 형식으로 미리 채운 19개 ID | 감사 원본 작성 완료 |
| `2026 오픈소스 개발자대회 결과보고서_접수번호(팀명)_DRAFT.docx` | 공식 양식 기반 편집본 | v2·사람 감사 반영, 신원·영상·개발 소감 필요 |
| 같은 이름의 `DRAFT.pdf` | 감사 반영 전 대조 PDF | 신원·영상 입력 뒤 최종 DOCX에서 다시 생성 필요 |

2026-08-06 대회 릴리스 작업 트리 검증은 `276 passed, 2 skipped`다. 두 skip은
현재 Windows의 심볼릭 링크 생성 권한이 없어 건너뛴 경계 테스트다. 공개 결과
커밋 `33c94534c168fb015b85984832503a6de5f170c6`을 GitHub에서 새로 clone한
가상환경에서도 `276 passed, 2 skipped`를 재현했고, demo 도움말·fixture
계약 평가·216개 공개 결과 검증·wheel 빌드와 새 환경 설치가 통과했다. 최종
제출 SHA를 확정한 뒤 같은 검증을 한 번 더 한다.

유효한 v2 holdout은 총 216회(24 case × 3 구조 × 3 seed)를 모두 기록했다.
기계 verdict는 Node2·Node4 없는 단일 에이전트 기준선 71/72, 송련 Node4 제외 72/72, 송련 전체
72/72였다. 기준선의 1건은 JSON 형식 실패로 미완료 처리됐다. 송련 전체와
Node4 제외 구조가 전부 동률이므로 현재 결과는 Node4의 효과를 입증하지 않는다.
필수 blind 19개에 대한 참가자 설명 감사도 완료했다. parser와 실제 답변·미완료
상태는 19/19가 일치했고, fixture 근거성과 A/R 권한·출처 표기는 각각
18/19였다. 나머지 1건은 잘못된 설명이 아니라 모델 응답이 `null`인 미완료
사례여서 설명과 출처 표기를 평가할 답변 자체가 없었다. 현재 boolean 감사
스키마는 N/A를 표현하지 못해 두 항목을 `false`로 기록했다.

사람 감사 뒤 publication integrity gate는 통과했고 공개 결과의 `publishable`은
`true`다. 이는 동결·감사·출처 연결을 공개할 수 있다는 뜻이지, 세 구조의 성능
우열, Node4의 추가 효과, 216개 설명 전체의 사실성, 통계적 유의성, 실제 업무
일반화 또는 환각 제거를 입증한다는 뜻이 아니다. 공개 감사와 결정 파일은 각각
`HUMAN_AUDIT.json`, `PUBLICATION_DECISION.json`으로 증거 폴더에 포함했다.

## 공식 제출 요건 대응표

| 요구 항목 | 준비 위치 | 완료 조건 |
|---|---|---|
| 결과보고서 DOCX 또는 HWP | `result_report_draft.md` | 공식 양식에 옮기고 본문 5쪽 이내 확인 |
| 결과보고서 PDF | 위 문서의 최종본 | DOCX/HWP와 내용·페이지가 같은 PDF 생성 |
| 소스 코드 | 공개 저장소와 제출 시점 커밋 | 깨끗한 환경에서 설치·테스트·데모 재현 |
| 3분 이하 YouTube 시연 | `demo_script_3min.md` | 실제 영상 3분 이하, 공개 범위와 URL 확인 |
| SBOM | `sbom.md` | 정확한 버전·출처·라이선스·해시 보완 |
| AI 모델 사양 | `ai_model_spec.md` | 모델과 AI 코딩 보조 사용 내역 최종 기재 |

공식 제출 제약은 **결과보고서 본문 5쪽 이내**, **시연 영상 3분 이내**이며,
AI 모델 활용·라이선스 명세와 SBOM을 함께 점검한다. 제출 직전에는
[공식 대회 안내](https://osscontest.kr/overview)와 참가자 페이지의 최신 공지를
다시 대조한다.

## 제출 전 필수 체크리스트

### 1. 신원과 링크

- [ ] 접수번호 입력: `TODO`
- [ ] 팀명 입력: `TODO`
- [ ] 팀장·팀원 정보 입력: `TODO`
- [ ] 공개 소스 저장소 URL 확정
- [ ] 제출 대상 Git 커밋 SHA와 태그 확정
- [ ] GitHub 기본 브랜치 또는 제출 링크가 최종 v1 커밋을 직접 가리키는지 확인
- [ ] 3분 이하 YouTube URL 입력: `TODO`

### 2. 결과보고서

- [ ] `result_report_draft.md`를 공식 DOCX/HWP 양식에 옮김
- [ ] 본문을 5쪽 이내로 편집
- [ ] Mermaid 그림을 정적 이미지로 변환하고 글자가 읽히는지 확인
- [ ] 정량 수치는 검토 완료된 라이브 평가 결과만 사용
- [ ] DOCX/HWP와 PDF의 표·그림·페이지 누락 여부를 대조
- [ ] 파일명과 압축 형식을 최종 공지에 맞춤

### 3. 소스와 재현성

- [ ] 제출 브랜치의 깨끗한 clone에서 아래 명령 실행
- [ ] `python -m pytest -q`의 정확한 결과를 보고서에 기록
- [ ] 실패가 하나라도 남아 있으면 성공 수치 대신 원인·처리 상태를 기록하고 제출 전 해소
- [ ] `python -m demo --help`와 시연 명령 실행 확인
- [ ] 로컬 Ollama에서 제출 모델의 전체 digest를 기록
- [ ] `memory/memory.jsonl`, API 키, 개인정보, 로컬 DB가 제출물에 없는지 확인
- [ ] `LICENSE`, `THIRD_PARTY_NOTICES.md`, 재현 문서 포함 확인

권장 깨끗한 clone 명령:

```powershell
git clone --branch codex/contest-release-2026 --single-branch `
  https://github.com/Junghoo-developer/SongRyeon.git SongRyeon_Core_v1
Set-Location SongRyeon_Core_v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -q
```

### 4. SBOM과 AI 공개

- [ ] Python·setuptools·pytest의 제출 환경 정확한 버전과 라이선스 확인
- [ ] Ollama와 모델의 공식 배포처·라이선스 원문 재확인
- [ ] 제출에 사용한 모델 태그, 전체 digest, 양자화, 컨텍스트 설정 기록
- [ ] 비교 기준선 결과를 제출 모델 결과와 섞지 않음
- [ ] 개발 중 사용한 생성형 AI 코딩 보조 서비스와 사용 범위 기재
- [ ] 외부 API 통합시험을 공식 로컬 성능 결과에서 제외
- [ ] Codex 계정·외부 API 모델 체급 실험을 공식 로컬 실행 결과와 분리

### 5. 평가 결과

- [x] v2 고정 case와 모든 비교 시스템의 원문 실행 결과 보존
- [x] 실패·시간 초과를 제외하지 않음
- [x] 필수 blind 항목의 사람 감사 방법과 결과를 공개
- [x] `HUMAN_AUDIT.json`과 publication integrity gate를 통과하고 제한된 문구를 승인
- [x] 기계 verdict 채점만 끝난 결과를 설명 전체의 사실성 증거로 사용하지 않음
- [x] 현재의 합성 fixture 점수를 실제 업무 전체 성능으로 인용하지 않음
- [x] 2026-07-30 P0 파일럿 30개 원시 capture와 실패 1건 보존
- [x] v1 채점기 결함을 숨기지 않고 무효화 기록 공개
- [x] v2 공개 체인의 216개 항목·해시 검증 통과
- [x] v2 필수 blind 19개(미완료 1개 포함)를 참가자가 직접 검수
- [x] 19개 감사가 216개 전체 설명 검증이 아님을 명시
- [x] seed 반복을 독립 case로 세거나 독립 end-to-end 비교를 Node4 순수 인과효과로 표현하지 않음

## 현재 남아 있는 `TODO`

- 참가자 신원, 접수번호, 팀명
- 제출 커밋 SHA와 릴리스 태그
- 최종 YouTube 영상 URL
- 최종 제출 SHA 확정 뒤 깨끗한 clone 검증 1회 반복
- 제출 모델 전체 digest와 실제 시연 환경
- AI 코딩 보조 서비스의 모델·기간·사용 범위
- 접수번호·팀명·영상 URL을 넣은 공식 양식 최종 DOCX/HWP와 PDF

## 제출본에 넣지 말아야 할 것

- publication gate의 `publishable: true`를 성능 우월성이나 설명 전체 검증으로 확대하는 문장
- `.tmp/`의 원시 프롬프트·thinking·절대 로컬 경로가 포함된 로그
- 실제 `memory/memory.jsonl`, `knowledge/knowledge.db`, API 키와 인증 정보
- 최종 커밋에서 재현하지 않은 테스트 통과 수치나 과거 영상
