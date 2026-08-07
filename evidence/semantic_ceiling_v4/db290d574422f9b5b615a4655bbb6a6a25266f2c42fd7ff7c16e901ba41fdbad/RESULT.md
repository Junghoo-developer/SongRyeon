# Semantic Ceiling v4 — post-hoc result

이 문서는 동결된 최초 실행 결과를 사람이 읽기 쉽게 정리한 **사후 요약**이다.
사전등록 문서와 채점 규칙은 source commit `c755e72f79999805ba707614365df6edf0216471`,
동결 증명은 publication commit `cf6fd9d40f0e7053e0a7cbb940b30a2399da8508`에 먼저 공개됐다.

## 결과

| 항목 | 관측값 |
|---|---:|
| 고정 분류 | `near_ceiling` |
| exact joint correctness | 23 / 24 |
| SUPPORTED | 12 / 12 |
| UNSUPPORTED | 11 / 12 |
| 완전 정답 cluster | 7 / 8 |
| strict-parse 성공 | 8 / 8 |
| 실행한 model request | 8 / 8 |
| runner retry | 0 |
| 도구 사용 | 0 |
| readiness 일치 | true |
| 총 latency | 83,734.1179 ms |
| input tokens | 86,702 |
| output tokens | 3,218 |
| reasoning output tokens | 1,243 |
| total tokens | 89,920 |
| copy-`SUPPORTED` baseline | 12 / 24 |

고정 모델 계약은 Codex 계정 통합 경로의 `gpt-5.6-sol`, reasoning effort
`medium`, `openai-codex==0.144.4`였다. 각 cluster는 새 thread에서 실행됐고
에이전트 도구는 허용하지 않았다. API-key 관련 환경변수 세 개는 실행 전에
부재가 확인됐다.

## 유일한 오답

`v4-c06-exception-targets`의 세 번째 claim에서 모델은 다음 실제 관측값을
예측했다.

```json
["ZeroDivisionError", "NameError", false]
```

동결된 CPython 3.10.11 oracle의 실제 관측값은 다음과 같다.

```json
["ZeroDivisionError", "UnboundLocalError", false]
```

모델은 `except ZeroDivisionError as error` 종료 시 exception target이 지워진다는
핵심 현상은 파악했지만, 함수의 지역변수로 분류된 `error`를 이후 읽을 때 발생하는
정확한 예외 종류를 틀렸다. `UnboundLocalError`가 `NameError`의 하위 클래스여도 이
실험은 정확한 관측값과 verdict의 동시 일치를 요구하므로 오답이다.

## 해석

- v2의 12/12 ceiling과 달리 v4는 Sol medium의 완전 정답 ceiling을 실제로
  깨뜨렸다. 다만 서로 다른 문항 집합의 단일 실행이므로 v2 대비 난이도 차이를
  인과적으로 추정하지 않는다.
- 23/24는 이 고정 suite에서의 높은 Python 의미론 예측 성능을 보여주지만,
  SongRyeon 전체의 우월성이나 일반적인 환각 감소율을 측정한 결과는 아니다.
- 틀린 한 claim은 단순 문자열 실수가 아니라, 실행 없이 코드 의미론을 예측할 때
  남는 세밀한 언어 규칙 경계를 드러낸다. 이후 SongRyeon 대조 실험에서 검증
  루프가 이런 오류를 포착하는지 측정할 수 있는 표적 사례가 된다.

## 한계

- 24개 claim, 한 번의 stochastic realization뿐이므로 통계적 독립성이나
  신뢰구간을 주장하지 않는다.
- 문항 설계 과정에 같은 Sol 계열 모델의 도움을 받았으므로 model-family 독립
  문항이라고 주장하지 않는다.
- CPython 3.10.11의 동결된 관측만 평가하며 다른 Python 구현이나 버전으로
  일반화하지 않는다.
- 이번 실행은 target-only semantic diagnostic이다. bare model과 SongRyeon의
  직접 대조 결과가 아니며, 성능 향상 인과효과를 주장하지 않는다.
- 계정 통합 경로와 금지 환경변수 부재는 기록했지만, 이 산출물만으로 실제 결제나
  계정 한도 차감 여부까지 증명하지는 않는다.

## 무결성 식별자

- freeze SHA-256: `db290d574422f9b5b615a4655bbb6a6a25266f2c42fd7ff7c16e901ba41fdbad`
- frozen source tree SHA-256: `c3131e0b32e7781b82a7bda38da73006218c381c3a6e8fed8948544034b9a8a1`
- canonical/public `run.json` SHA-256: `8e4bbe0614b2b76133bc99224ddb75c6f1abed63a640fba78ae782fc39209599`
- run ID: `e51e24722054439a89129f2081fefe17`
- 실행 시각(UTC): `2026-08-07T11:01:47.528Z`–`2026-08-07T11:03:11.325Z`

기계 검증 가능한 원본은 같은 폴더의 `run.json`이다. 이 요약보다 원본과 동결
프로토콜을 우선한다.
