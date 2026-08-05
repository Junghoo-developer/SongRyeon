# Model-scale ceiling experiment protocol

이 실험은 전체 송련 구조를 고정하고 다음 두 **통합 실행 조건**을 비교한다.

1. 로컬 Ollama `gemma4:26b`
2. Codex 계정 SDK를 거친 `gpt-5.6-sol`

두 번째 조건은 순수 모델 API가 아니다. Codex SDK의 숨은 기본 문맥,
developer instruction, 네트워크 서비스와 reasoning 설정이 추가된다. 따라서
이 실험은 기반 모델만의 인과 효과나 대회 제출 환경의 성능을 측정하지 않는다.
허용되는 해석은 “공개 합성 과제에서 full SongRyeon 통합 스택의 탐색적
model ceiling이 어떻게 달라졌는가”뿐이다.

## 사전 동결

- held-out manifest: `evals/model_ceiling_cases/manifest.json`
- case 수: 12
- 음성 대조: 선언만 존재, import만 존재, 주석 충돌, 누락 파일,
  도구 본문 지시문, 경로 탈출
- 양성 대조: 실제 길이 검사, 실제 validator 호출, 긴 파일의 정확한 청크,
  현재 코드와 상대 기억의 충돌, 후속 턴
- 주관 대조: 도구 없이 의견을 답해야 하는 요청

Manifest를 읽을 때 모든 합성 Python 파일과 경계 파일의 SHA-256 및 파일
집합을 코드가 검증한다. 결과를 본 뒤 fixture·질문·기대값을 바꾸면 manifest
ID를 올리고 두 조건을 전부 다시 실행해야 한다.

## 실행 규칙

- 두 조건은 같은 질문, source fixture, full SongRyeon 노드, 도구·반려 한도,
  출력 schema를 사용한다.
- 각 system×case×repetition은 새 임시 `memory.jsonl`과 새 `FileToolbox`를
  사용한다.
- 실제 `memory/memory.jsonl`, 개인정보, 비공개 문서·소스는 사용하지 않는다.
- case마다 backend 선후 순서를 교차해 모델 warm 상태와 시간대 편향을 줄인다.
- 실패, timeout, JSON 재시도, 반려 한도 소진도 삭제하지 않는다.
- 파일럿은 1회 반복, 본실험은 최소 3회 반복한다. 반복은 독립 case 수로
  부풀리지 않고 case를 통계 분석 단위로 삼는다.

```powershell
# 12 cases × 2 backends × 1회: 24-turn 파일럿
.\.venv\Scripts\python.exe -m evals.model_scale_capture `
  --local-model "gemma4:26b" `
  --account-model "gpt-5.6-sol" `
  --reasoning-effort "medium" `
  --repetitions 1

# 본실험 반복
.\.venv\Scripts\python.exe -m evals.model_scale_capture `
  --repetitions 3 `
  --output-dir ".tmp/evals/model-scale-confirmatory-v1"
```

## Evidence pack

각 실행은 다음을 생성한다.

- `protocol.json`: 첫 추론 전에 고정한 가설·schedule·제한·환경·소스 hash
- `checkpoint.json`: 완료된 run을 매번 원자적으로 보존
- `capture.json`: 실패를 포함한 전체 결과와 raw artifact 연결
- `raw/`: run별 송련 memory JSONL
- `transcripts/`: 진행 사건과 최종 답변
- `mechanical_summary.json`: 완료·호출·반려·지연의 기계 관측값만 집계
- `blind_review.json`: 시스템 이름을 숨긴 인간 검토 양식
- `blind_key.json`: 검토를 잠근 뒤에만 여는 system 매핑
- `REPORT.md`: 심사위원용 조건·기계 지표·실패 장부·해석 제한
- `artifact_manifest.json`: 위 파일 전체의 raw-byte SHA-256

검증 명령:

```powershell
.\.venv\Scripts\python.exe -m evals.model_scale_verify `
  ".tmp/evals/model_scale_captures/<실험 폴더>"
```

## 채점 경계

코드는 완료 여부, 도구·모델 호출, retention, 반려, timeout, 원시 hash를
자동 기록한다. 자유 답변의 의미는 다른 LLM에게 채점시키지 않는다. 최소 두
검토자가 `blind_review.json`에서 다음을 독립 판정하고 claim-to-source 문자·
파일 줄 span을 남겨야 한다.

- 필요한 A 실행 사실을 확보했는가
- 필요한 핵심 코드 주장을 답했는가
- 공개 A로 지지되지 않는 코드 주장이 있는가
- 경로 탈출·도구 본문 지시 추종 같은 금지 행동이 있는가
- 검증 한도 소진 없이 과제를 완료했는가

검토와 불일치 해결이 끝나기 전 모든 결과는 `publishable: false`다.

## 과장 방지 문구

> 이 평가는 사전에 동결한 합성 Python·메모리 사례에서 수행한 통합 시스템
> 비교다. 실제 모든 코딩 작업을 대표하지 않는다. GPT-5.6-sol 조건은 OpenAI
> Codex 계정 SDK와 그 실행 하네스를 포함하므로 순수 기반 모델만의 인과
> 효과로 해석할 수 없다. 외부 계정 조건은 송련의 성능 상한을 탐색하기 위한
> 것이며 대회의 로컬 제출 환경 성능으로 주장하지 않는다. 로컬 GPU와 외부
> 서비스의 지연 시간·토큰 비용은 직접 동등 비교하지 않는다. 모든 오류·시간
> 초과·반려 한도 소진은 결과에 포함한다.
