# 2026 오픈소스 개발자대회 제출 준비 패키지

> 상태: **작성 중인 내부 초안**
>
> 이 폴더의 Markdown 파일은 공식 제출 양식 자체가 아니다. 제출 전 반드시
> 대회가 배포한 결과보고서 DOCX/HWP 양식에 옮기고, 본문 분량과 PDF 변환
> 결과를 다시 확인해야 한다.

## 파일 구성

| 파일 | 용도 | 현재 상태 |
|---|---|---|
| `result_report_draft.md` | 결과보고서 본문에 옮길 사실 중심 원고 | 초안 |
| `sbom.md` | 소프트웨어·모델 구성요소 목록 | 버전·라이선스 최종 확인 필요 |
| `ai_model_spec.md` | AI 모델 사용 방식과 실행 경계 | 코딩 보조 이력 보완 필요 |
| `demo_script_3min.md` | 3분 이하 YouTube 시연 대본 | 실제 촬영·링크 필요 |
| `live_pilot_notes.md` | Qwen3 동일 backbone 3구조 원시 비교 기록 | 내부 검토용·정량 인용 금지 |
| `2026 오픈소스 개발자대회 결과보고서_접수번호(팀명)_DRAFT.docx` | 공식 양식 기반 편집본 | 본문 3쪽·전체 6쪽, 신원·영상·개발 소감 입력 필요 |
| 같은 이름의 `DRAFT.pdf` | Word에서 내보낸 대조 PDF | 6쪽 전 페이지 렌더 검수 완료 |

## 공식 제출 요건 대응표

| 요구 항목 | 준비 위치 | 완료 조건 |
|---|---|---|
| 결과보고서 DOCX 또는 HWP | `result_report_draft.md` | 공식 양식에 옮기고 본문 5쪽 이내 확인 |
| 결과보고서 PDF | 위 문서의 최종본 | DOCX/HWP와 내용·페이지가 같은 PDF 생성 |
| 소스 코드 | 공개 저장소와 제출 시점 커밋 | 깨끗한 환경에서 설치·테스트·데모 재현 |
| 3분 이하 YouTube 시연 | `demo_script_3min.md` | 실제 영상 3분 이하, 공개 범위와 URL 확인 |
| SBOM | `sbom.md` | 정확한 버전·출처·라이선스·해시 보완 |
| AI 모델 사양 | `ai_model_spec.md` | 모델과 AI 코딩 보조 사용 내역 최종 기재 |

## 제출 전 필수 체크리스트

### 1. 신원과 링크

- [ ] 접수번호 입력: `TODO`
- [ ] 팀명 입력: `TODO`
- [ ] 팀장·팀원 정보 입력: `TODO`
- [ ] 공개 소스 저장소 URL 확정
- [ ] 제출 대상 Git 커밋 SHA와 태그 확정
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
- [ ] `python -m demo --help`와 시연 명령 실행 확인
- [ ] 로컬 Ollama에서 제출 모델의 전체 digest를 기록
- [ ] `memory/memory.jsonl`, API 키, 개인정보, 로컬 DB가 제출물에 없는지 확인
- [ ] `LICENSE`, `THIRD_PARTY_NOTICES.md`, 재현 문서 포함 확인

권장 깨끗한 clone 명령:

```powershell
git clone --branch refoundation/songryeon-v1 --single-branch `
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

### 5. 평가 결과

- [ ] 고정 case와 모든 비교 시스템의 원문 실행 결과 보존
- [ ] 실패·시간 초과를 제외하지 않음
- [ ] 사람이 정규화한 항목과 방법을 공개
- [ ] `review_status: "reviewed"`인 결과만 정량 근거로 사용
- [ ] 현재의 합성 fixture 점수를 실제 모델 성능으로 인용하지 않음
- [x] 2026-07-30 P0 파일럿 30개 원시 capture와 실패 1건 보존

## 현재 남아 있는 `TODO`

- 참가자 신원, 접수번호, 팀명
- 제출 커밋 SHA와 릴리스 태그
- 최종 YouTube 영상 URL
- 최종 제출 커밋을 깨끗하게 clone한 환경의 테스트 결과
- 제출 모델 전체 digest와 실제 시연 환경
- 검토 완료된 라이브 비교평가 수치
- AI 코딩 보조 서비스의 모델·기간·사용 범위
- 접수번호·팀명·영상 URL을 넣은 공식 양식 최종 DOCX/HWP와 PDF
