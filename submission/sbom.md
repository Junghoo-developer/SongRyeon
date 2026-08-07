# SongRyeon Core v1 SBOM

> 상태: **2026-08-06 관찰 환경과 공개 소스 릴리스 기준 명세**
>
> 이 표는 현재 저장소의 직접 구성요소를 정리한 것이며 SPDX 또는 CycloneDX
> 정식 산출물을 대신하지 않는다. 아래 버전은 프로젝트 `.venv`와 로컬 모델
> 런타임에서 관찰했으며, 소스 릴리스는 `contest-2026-final` 태그로 고정한다.

## 범위

- 포함: 제출 소스, 직접 실행·빌드·테스트 의존성, 로컬 모델 런타임, 시연과
  비교에 명시된 모델
- 미포함: 운영체제 기본 구성요소, 편집기, 개인 개발 환경, 선택적 외부 API
  통합시험의 공급자 모델
- 배포 경계: 저장소는 Ollama 실행 파일이나 모델 가중치를 재배포하지 않는다.

## 구성요소 목록

| 구성요소 | 종류·관계 | 버전·식별자 | 공급자·출처 | 라이선스 | 제출물 포함 여부 | 최종 확인 |
|---|---|---|---|---|---|---|
| SongRyeon Core | 애플리케이션, 최상위 패키지 | `0.1.0`; tag `contest-2026-final` | 이 저장소 | MIT | 소스 포함 | 고정 태그에서 해시 확인 |
| Python | 실행 런타임 | 요구 `>=3.10`; 관찰 `3.10.11` | Python Software Foundation | PSF-2.0 | 별도 설치 | 제출 환경에서 재확인 |
| setuptools | 빌드 backend | 요구 `>=65`; 관찰 `65.5.0` | Python Packaging Authority; <https://github.com/pypa/setuptools> | MIT | 패키지 미포함, 빌드 시 설치 | 제출 환경에서 재확인 |
| wheel | 빌드·패키징 테스트 의존성 | 요구 `>=0.40`; 관찰 `0.47.0` | Python Packaging Authority; <https://github.com/pypa/wheel> | MIT | 패키지 미포함, 빌드·테스트 시 설치 | 제출 환경에서 버전 재확인 |
| pytest | 선택적 테스트 의존성 | 요구 `>=8`; 관찰 `9.1.1` | pytest 프로젝트; <https://github.com/pytest-dev/pytest> | MIT | 런타임 미포함 | 제출 환경에서 재확인 |
| Ollama | 로컬 모델 런타임 | 관찰 `0.32.5` | <https://github.com/ollama/ollama> | MIT | 별도 설치 | 제출 환경에서 재확인 |
| Gemma 4 26B | 대회용 로컬 모델 | `gemma4:26b`; digest `5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251`; 25.8B; `Q4_K_M` | Google; <https://ollama.com/library/gemma4>, <https://huggingface.co/google/gemma-4-26B-A4B/blob/main/README.md> | Apache-2.0 | 가중치 별도 설치 | 2026-08-06 로컬 license 출력·공식 배포 페이지 교차 확인; 최종 digest 재확인 |
| Qwen3-14B | 과거 모델 체급 탐색 대상 | `qwen3:14b`; digest `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`; `Q4_K_M` | Qwen / Alibaba Cloud; <https://huggingface.co/Qwen/Qwen3-14B> | Apache-2.0 | 탐색 재현 시 별도 설치 | 공식 v2 비교군·fallback 아님 |
| openai-codex | 선택적 외부 모델 체급 시험 SDK | 요구·관찰 `0.144.4` | OpenAI; <https://github.com/openai/codex> | Apache-2.0 | 기본 런타임 미포함, `[codex]` 선택 설치 | 2026-08-06 확인 |
| pydantic | `openai-codex` 직접 의존성 | 요구 `>=2.12`; 관찰 `2.13.4` | <https://github.com/pydantic/pydantic> | MIT | `[codex]` 선택 설치에만 포함 | 제출 환경에서 재확인 |
| openai-codex-cli-bin | `openai-codex` 직접 의존성 | 요구·관찰 `0.144.4` | OpenAI; <https://github.com/openai/codex> | Apache-2.0 | `[codex]` 선택 설치에만 포함 | 2026-08-06 package metadata 확인 |

## 의존 관계

```text
SongRyeon Core 0.1.0
├─ requires: Python >=3.10
├─ build backend: setuptools >=65 + wheel
├─ optional test: pytest >=8 + wheel >=0.40
├─ optional external experiment: openai-codex ==0.144.4
│  ├─ pydantic >=2.12 (observed 2.13.4)
│  └─ openai-codex-cli-bin ==0.144.4
└─ inference endpoint: Ollama
   ├─ contest profile: gemma4:26b
   └─ historical model-scale exploration: qwen3:14b
```

실행 코드는 Python 표준 라이브러리의 `json`, `pathlib`, `sqlite3`,
`urllib`, `uuid`, `datetime` 등을 사용한다. `pyproject.toml`의 필수
`dependencies` 배열은 비어 있다.

## 검증 명령

```powershell
git rev-parse HEAD
python --version
python -m pip show setuptools wheel pytest
python -m pip show openai-codex pydantic openai-codex-cli-bin
ollama --version
ollama list
ollama show gemma4:26b
ollama show gemma4:26b --license
ollama show qwen3:14b
```

`gemma4:26b`의 로컬 라이선스 출력과 공식 배포 페이지는 2026-08-06에
Apache-2.0으로 교차 확인했다. 공식 결과보고서에는 전체 모델 digest를 적고,
최종 소스 ZIP은 작업 폴더가 아니라 고정 Git 태그에서 `git archive`로 만든다.
배포 검사에서는 자격증명, 실제 `memory.jsonl`, 로컬 DB와 원시 평가 자료가
포함되지 않았는지 별도로 확인한다.

## 명시적 제외

`--external-api-integration`으로 연결할 수 있는 OpenAI-compatible API는
대회용 로컬 실행 경로의 자동 fallback도, 제출 런타임의 필수 구성요소도
아니다. 공급자 API를 별도 통합시험에 사용한다면 공급자명, 정확한 모델,
시험 날짜와 적용 약관을 해당 시험 기록에만 추가하고 공식 로컬 성능 집계와
분리한다.

`openai-codex` 선택 의존성과 `--codex-account-integration`도 같은 원칙으로
대회 기본 런타임과 분리한다. 소스에 선택 경로가 남아 있는 경우 SBOM에는
기재하되, 공식 로컬 시연의 필수 구성요소나 성능 결과로 표시하지 않는다.
