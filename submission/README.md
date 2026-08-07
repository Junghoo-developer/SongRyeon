# 2026 오픈소스 개발자대회 공개 증거 패키지

이 폴더에서 Git으로 추적하는 파일은 대회 소스 릴리스의 실행 경계, 모델·
라이선스 정보, 시연 절차와 사람 감사 기록을 설명하는 공개 자료다.

공식 결과보고서 DOCX/PDF, 최종 영상과 참가자 개인 검수표는 대회 포털에
별도로 제출한다. 이 파일들은 최종 Git SHA를 인용하므로 소스 태그에 넣지
않는다. 이렇게 해야 보고서가 자신을 포함한 커밋의 SHA를 적는 자기참조를
피할 수 있다.

## 공개 파일

| 파일 | 용도 |
|---|---|
| `sbom.md` | 소프트웨어·모델 구성요소와 배포 경계 |
| `ai_model_spec.md` | 공식 로컬 모델, 선택적 외부 시험과 AI 코딩 보조 공개 |
| `demo_script_3min.md` | 3분 시연의 주장 범위와 화면 구성 |
| `video_capture.ps1` | 깨끗한 작업 트리·fixture·모델·테스트를 확인하는 촬영 진입점 |
| `live_pilot_notes.md` | Qwen3 P0 원시 파일럿과 비공개 상태의 한계 기록 |
| `human_audit_v2_packet.md` | 정답을 숨긴 필수 19개 사람 감사 읽기 묶음 |
| `HUMAN_AUDIT_V2_TEMPLATE.json` | 사람 감사 입력 형식과 고정 blind ID |
| `../evals/contest_holdout_v1/frozen/contest-20260806-v2/` | 동결·블라인드·점수 잠금·감사·공개 결정의 검증 가능한 체인 |

## 고정 소스 릴리스

- 태그: `contest-2026-final`
- 저장소: <https://github.com/Junghoo-developer/SongRyeon>
- 고정 소스: <https://github.com/Junghoo-developer/SongRyeon/tree/contest-2026-final>
- 실행 모델: 로컬 또는 자체 호스팅 Ollama `gemma4:26b`
- 모델 전체 digest: `5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251`
- 로컬 최종 사전 점검: `276 passed, 2 skipped`

두 skip은 Windows에서 심볼릭 링크 생성 권한이 없을 때만 건너뛰는 경계
시험이다. 최종 태그의 GitHub Actions는 Ubuntu Python 3.10·3.12와 Windows
Python 3.10에서 확인한다.

## 공식 v2 결과와 주장 경계

사전 동결 합성 평가의 크기는 24 case × 3 구조 × 3 seed = 216회다.

| 구조 | 첫 verdict 결과 |
|---|---:|
| Node2·Node4 없는 단일 에이전트 | 71 / 72 |
| Node4 모델 검열 제외(결정론적 bypass) 송련 | 72 / 72 |
| 전체 송련 | 72 / 72 |

단일 에이전트의 1건은 `ModelResponseError` 미완료다. 사전 지정 18개와
프로토콜이 자동 포함한 미완료 1개를 합친 19개를 프로젝트 소유자가 감사한
결과 parse 19/19, fixture 근거성 18/19, A/R
권한·출처 표기 18/19였다. 나머지 1건은 모델 응답이 `null`이어서 설명을
평가할 수 없는 미완료 사례였다.

publication integrity gate 통과는 동결·감사·출처 연결을 공개할 수 있다는
뜻이다. 세 구조의 성능 우월성, Node4의 독립 인과효과, 216개 설명 전체의
사실성, 통계적 유의성, 실제 업무 일반화나 환각 제거를 입증하지 않는다.

## 재현

```powershell
git clone --branch contest-2026-final --single-branch `
  https://github.com/Junghoo-developer/SongRyeon.git SongRyeon_Core_v1
Set-Location SongRyeon_Core_v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -q
```

시연 전 검증과 격리 데모는 다음 진입점을 사용한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\submission\video_capture.ps1 -Mode verify
powershell -ExecutionPolicy Bypass -File .\submission\video_capture.ps1 -Mode demo
```

촬영할 때 `-AllowDirty`와 `-SkipTests`는 사용하지 않는다. 스크립트는 실제
`memory/memory.jsonl` 대신 매번 새로운 `.tmp/video-capture/` 기억을 쓴다.

## 소스 릴리스 제외 항목

- 공식 결과보고서 DOCX/PDF와 최종 영상
- 참가자 이름·연락처·접수 완료 화면과 제출 시각
- 실제 `memory/memory.jsonl`, `knowledge/knowledge.db`
- API 키, 브라우저 세션과 인증 정보
- `.tmp/`의 원시 프롬프트·thinking·비공개 평가 산출물

소스 ZIP은 작업 폴더를 직접 압축하지 않고 반드시 고정 Git 태그에서
`git archive`로 만든다.
