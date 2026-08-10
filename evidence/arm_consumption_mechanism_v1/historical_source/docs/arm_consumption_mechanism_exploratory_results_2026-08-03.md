# ARM 증거 소비 메커니즘 탐색 실험 결과 보고서

**객관적 결론:** 사전 지정 판정은 **`NO-GO`**다. `ar-consumer-rule`의 negative strict success 개선은 placebo 대비 **+8.89%p**로 사전 문턱인 +10%p에 못 미쳤다. 이 결과 묶음의 메타데이터 값은 **`publishable=false`**이며, 이미 사용한 synthetic case를 재사용한 **탐색적(exploratory) 결과이지 확증적(confirmatory) 결과가 아니다.** 또한 아래의 사전 동결·감사 결격 때문에 내부 스냅샷 해시 일관성은 확인되더라도 완전한 사전등록 준수나 독립적 신뢰성은 성립하지 않는다.

> **PREDECLARED GO/NO-GO VERDICT: `NO-GO`**
>
> **Publication status: `publishable=false`**
> **Evidence status: exploratory, not confirmatory**

핵심 무결성 결격도 결론과 함께 읽어야 한다.

- Protocol이 요구한 사전 scorer/replay source freeze에 비해, 사후 분석에 사용된 `evals/mechanism_blind.py`, `evals/mechanism_score_verify.py`, `evals/mechanism_rating_reconcile.py`, `evals/mechanism_summary.py` source hash가 `FREEZE.json`에 없다.
- 제공된 provenance는 AI preliminary rating/adjudication을 기록할 뿐, protocol이 요구한 사람의 raw-packet 감사 증거는 제공하지 않는다.
- 내부 lock 상태와 hash는 있지만 blind key가 계속 미개봉이었다는 외부 timestamp·access log·제3자 custody 증거는 없다.

## 1. 연구 질문과 설계

연구 질문은 고정된 질문과 공개 evidence packet 아래에서 다음 세 효과를 분리하는 것이었다.

1. A/R 라벨 자체가 아니라, “A만 확인된 사실 근거로 쓰고 R을 A로 승격하지 않는다”는 정확한 소비 규칙이 근거 세탁을 줄이는가?
2. 같은 consumer draft를 검토하는 evidence reviewer가 길이·주의량을 맞춘 style-placebo reviewer보다 잘못된 사실 승격을 더 잘 교정하는가?
3. reviewer의 `permit/reject`를 결정론적으로 적용한 결과가 원 draft를 전달하는 shadow보다 unsafe delivery를 줄이면서 올바른 답변의 유용성을 보존하는가?

설계와 실행량은 다음과 같다.

| 항목 | 고정값 |
|---|---:|
| case | 30개 synthetic Python case |
| seed | 42, 43, 44 |
| 실험 block | **30 cases × 3 seeds = 90** |
| Panel P | 90 × 4 prompt arm = 360 answer call |
| Panel R | 90 × 2 reviewer = 180 reviewer call |
| 실제 신규 모델 호출 | **540회** |
| Panel R 파생 결과 | 90 × 3 (`shadow`, style enforced, evidence enforced) = 270; 추가 모델 호출 없음 |
| 추론 단위 | case 30개; seed는 동일 case의 반복 생성이며 독립 표본이 아님 |

네 prompt arm은 `opaque-label`, `ar-label-only`, `ar-label-placebo`, `ar-consumer-rule`이다. Reviewer arm은 `style-placebo-reviewer`와 `evidence-reviewer`이며, 두 reviewer가 보는 common draft는 각 block의 `ar-consumer-rule` 출력이다. `shadow`는 이 draft를 그대로 전달하고, enforced 조건은 reviewer가 `permit`이면 원 draft를, `reject`이면 `revised_answer`를 전달한다.

ITT 원칙에 따라 기술 실패·schema 실패·미완성 답변도 strict success 실패로 남긴다. Strict success는 의미 결론, 필수 공개 근거 사용, A/R·도구 사실 비위조, 사용자 전달 가능 완결성을 모두 충족해야 1이다. 아래 표에서 total 분모는 조건별 90, negative와 positive 분모는 각각 15 case × 3 seed = 45다. Laundering은 negative row만을 분모로 한다.

## 2. 조건별 블라인드 의미 채점 결과

### 2.1 Prompt arm

| Prompt 조건 | Total strict success | Negative strict success | Positive strict success | Laundering (negative) |
|---|---:|---:|---:|---:|
| `opaque-label` | 65/90 (72.22%) | 22/45 (48.89%) | 43/45 (95.56%) | 15/45 (33.33%) |
| `ar-label-only` | 69/90 (76.67%) | 25/45 (55.56%) | 44/45 (97.78%) | 18/45 (40.00%) |
| `ar-label-placebo` | 62/90 (68.89%) | 23/45 (51.11%) | 39/45 (86.67%) | 13/45 (28.89%) |
| `ar-consumer-rule` | 68/90 (75.56%) | 27/45 (60.00%) | 41/45 (91.11%) | 10/45 (22.22%) |

Consumer rule은 label placebo보다 total strict success +6.67%p, negative strict success +8.89%p, positive strict success +4.44%p였고 laundering은 -6.67%p였다. 방향은 대체로 유리했지만 negative strict success의 사전 문턱 +10%p는 넘지 못했다. `ar-label-only`는 `opaque-label`보다 total strict success가 +4.44%p였지만 laundering은 오히려 +6.67%p였다.

### 2.2 Reviewer enforced output

| Reviewer 적용 조건 | Total strict success | Negative strict success | Positive strict success | Laundering (negative) |
|---|---:|---:|---:|---:|
| `style-placebo-enforced` | 64/90 (71.11%) | 21/45 (46.67%) | 43/45 (95.56%) | 15/45 (33.33%) |
| `evidence-enforced` | 74/90 (82.22%) | 29/45 (64.44%) | 45/45 (100.00%) | 1/45 (2.22%) |

Evidence enforcement는 style-placebo enforcement보다 total strict success +11.11%p, negative strict success +17.78%p, positive strict success +4.44%p였고 negative laundering은 -31.11%p였다. 별도 사전 정의인 `unsafe delivery = 1 - no_unsupported_claims`를 전체 90개에 적용하면 evidence 6/90, style 21/90, shadow 17/90으로, evidence가 각각 -16.67%p와 -12.22%p 낮았다. Laundering 감소의 exact sign-flip 값은 명목상 `p=0.03125`였으나, 본 연구의 탐색적 지위와 무결성 제한을 넘어선 확증적 유의성으로 해석할 수 없다.

## 3. Case-cluster 짝지은 대조

각 case 안에서 세 seed의 평균 차이를 먼저 계산하고 case를 cluster로 취급했다. 차이는 앞 조건에서 뒤 조건을 뺀 percentage point이며, `p`는 two-sided exact case-cluster sign-flip 값이다. Seed 90개를 독립 표본으로 간주하지 않았다.

| 대조 | 지표 | 짝지은 차이 | Exact sign-flip `p` |
|---|---|---:|---:|
| `ar-consumer-rule − ar-label-placebo` | Total strict success | +6.67%p | 0.265625 |
|  | Negative strict success | +8.89%p | 0.500000 |
|  | Positive strict success | +4.44%p | 0.750000 |
|  | Negative laundering | -6.67%p | 0.625000 |
| `ar-label-only − opaque-label` | Total strict success | +4.44%p | 0.500000 |
|  | Negative strict success | +6.67%p | 1.000000 |
|  | Positive strict success | +2.22%p | 1.000000 |
|  | Negative laundering | +6.67%p | 1.000000 |
| `evidence-enforced − style-placebo-enforced` | Total strict success | +11.11%p | 0.093750 |
|  | Negative strict success | +17.78%p | 0.187500 |
|  | Positive strict success | +4.44%p | 1.000000 |
|  | Negative laundering | -31.11%p | 0.031250 |

이 `p` 값들은 작은 case 수와 많은 동률을 가진 탐색 지표다. 독립 held-out confirmatory 검정이나 SongRyeon 전체 우월성의 근거가 아니다.

## 4. Enforced 대 shadow: 교정과 회귀

`shadow`는 동일 block의 `ar-consumer-rule` draft다. 아래 교정은 shadow 실패가 enforced에서 성공으로 바뀐 경우, 회귀는 shadow 성공이 enforced에서 실패로 바뀐 경우이며, 순교정은 `교정−회귀`다.

| Enforced 조건 | 구간 | Pair | 교정 | 회귀 | 순교정 |
|---|---|---:|---:|---:|---:|
| `style-placebo-enforced` | 전체 | 90 | 3 (3.33%) | 7 (7.78%) | -4 |
|  | negative | 45 | 1 (2.22%) | 7 (15.56%) | -6 |
|  | positive | 45 | 2 (4.44%) | 0 (0.00%) | +2 |
| `evidence-enforced` | 전체 | 90 | 7 (7.78%) | 1 (1.11%) | +6 |
|  | negative | 45 | 3 (6.67%) | 1 (2.22%) | +2 |
|  | positive | 45 | 4 (8.89%) | 0 (0.00%) | +4 |

Rate 관점에서도 style enforcement는 shadow보다 total strict success -4.44%p, negative strict success -13.33%p였고 negative laundering은 +11.11%p로 악화됐다. Evidence enforcement는 shadow보다 total strict success +6.67%p, negative strict success +4.44%p, positive strict success +8.89%p였고 negative laundering은 -20.00%p였다. 전체 row의 unsafe delivery는 evidence가 shadow보다 -12.22%p였다.

Reviewer 호출 자체는 evidence reviewer 90/90 valid(`permit` 76, `reject` 14), style reviewer 89/90 valid(`permit` 79, `reject` 10)였다. Style reviewer의 한 호출은 `invalid_exhausted`였으며 ITT에서 성공 row로 대체하지 않았다.

## 5. `pass^3` 안정성

`pass^3`는 한 case가 캡처된 세 seed 모두에서 strict success인 경우다. 분모는 조건별 30 case다.

| 조건 | `pass^3` case | 비율 |
|---|---:|---:|
| `opaque-label` | 21/30 | 70.00% |
| `ar-label-only` | 22/30 | 73.33% |
| `ar-label-placebo` | 17/30 | 56.67% |
| `ar-consumer-rule` | 20/30 | 66.67% |
| `style-placebo-enforced` | 20/30 | 66.67% |
| `evidence-enforced` | 23/30 | 76.67% |

## 6. 사전 지정 go/no-go 판정

사전 규칙은 여러 조건을 함께 충족해야 하는 보수적 진행 기준이었다. 관측값을 그대로 대입한 판정은 다음과 같다.

| 사전 기준 | 관측값 | 판정 |
|---|---|---|
| Consumer rule의 negative strict success가 placebo보다 +10%p 이상, positive 손실은 10%p 이내 | negative **+8.89%p**; positive +4.44%p(손실 없음) | **실패** |
| Evidence reviewer의 negative strict success가 style placebo보다 +10%p 이상, positive 손실은 10%p 이내 | negative +17.78%p; positive +4.44%p(손실 없음) | 통과 |
| 향상 방향이 5개 family 중 4개 이상에서 일치 | negative strict 기준 두 비교 모두 3개 향상, 1개 동률, 1개 하락 | 엄격한 양의 개선 해석에서는 **실패** |
| 어떤 family도 positive strict success가 25%p 이상 하락하지 않음 | 해당 하락 없음 | 통과 |
| Evidence-enforced가 style-enforced와 shadow보다 unsafe delivery를 10%p 이상 줄이고 positive 손실은 10%p 이내 | unsafe delivery -16.67%p vs style, -12.22%p vs shadow; positive는 각각 +4.44%p, +8.89%p | 통과 |

따라서 결합 규칙의 문자 그대로의 최종 판정은 다음과 같다.

> **PREDECLARED GO/NO-GO VERDICT: `NO-GO`**

Family 동률을 “방향 일치”에 포함할지는 protocol에 별도로 정의돼 있지 않다. 그러나 그 해석과 무관하게 consumer rule의 +8.89%p가 +10%p 문턱을 독립적으로 실패하므로 최종 `NO-GO`는 바뀌지 않는다. 이는 evidence reviewer의 관측 방향을 부정한다는 뜻이 아니라, 이 결과만으로 새 held-out 확인 실험으로 진행할 사전 문턱을 모두 충족하지 못했다는 뜻이다.

## 7. 채점자 일치와 조정

채점은 조건 메타데이터를 가린 `condition-metadata-masked review`였으며 완전 맹검으로 부르지 않는다.

| 항목 | 결과 |
|---|---:|
| 검증된 blind ID | 540개, 모두 고유 |
| 채점자별 검증 item | 540개 |
| 두 채점자 일치 | 470/540 (87.04%) |
| 불일치 | 70/540 (12.96%) |
| `semantic_grounded_success`만의 일치 | 503/540 (93.15%); Cohen's κ = 0.806 |
| 조정(adjudication) | 70/540 (12.96%); 불일치 전부 |
| 최종 strict success | 402/540 (74.44%) |
| scorer 표기 | `blind_ai_preliminary` |

Score lock은 `locked_before_unblinding`, rating provenance는 `finalized_before_unblinding` 상태를 기록하며, 두 파일의 score chunk 해시와 blind packet 해시는 서로 일치한다. 그러나 채점자는 AI preliminary rater이고, 제공된 산출물에는 독립 인간 채점이나 protocol이 요구한 사람의 raw-packet 대조 감사 기록이 없다.

## 8. 기술 실행 통계와 핵심 해시

모델은 `gemma4:26b`, digest `5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251`, server `0.32.5`, `num_ctx=16384`, `temperature=0`, timeout 180초였다. Answer/reviewer 최대 출력은 각각 768/1024 token이고 호출당 최대 시도는 3회였다.

| 실행 통계 | 값 |
|---|---:|
| 고유 모델 호출 | 540 |
| valid / `invalid_exhausted` | 539 / 1 |
| 총 시도 | 543; 평균 1.0056회/호출 |
| 총 token | 306,950 |
| 합산 latency | 1,162,482.759 ms |
| 평균 / p95 latency | 2,152.746 / 3,247.988 ms |
| Freeze 전 test | 302 passed, 1 skipped |
| 최종 전체 test | 329 passed, 1 skipped |
| Capture 상태 | `complete` |

| 객체 | SHA-256 |
|---|---|
| Source manifest canonical | `20d1406856d5c754353d03c6cd064a70da973e42535169a41ea65e958e71747e` |
| Evidence packet set | `03c9ddcd21e096b8df3bd178e807a208c4f953e14475b7f48f051c345b751967` |
| Evidence packet file | `dfcdcf9efaff1ff44a7ed54e8d49b44df6db5a7d795296ea384a585e9f10227d` |
| Protocol file | `e9c499e669a192458f73dde580f516bc85af8b131dcd21b90fedecb0c0879dc1` |
| Run plan file | `15888fec2c96a216955e9417c9c2d87690969a08d76246ce280ae928e5759f36` |
| Freeze file snapshot | `6992f83675e9b5efc8c39fb8f39d0dcd036048902f0cd33a7c4b0af37aab4027` |
| Capture | `dad82bebab0c601b6290d8d2468aae3ce7e52f6c753fe736d636d90cfa7b3fad` |
| Operational summary file | `0ad51fdb63e9c9d64102f36c00f476a85a469f09bb36739c876aea0847269947` |
| Blind key | `a8d37297cca48bca4dacd18aee36d9323d0cf53847fb0723516f294168a8e86d` |
| Score lock file | `8b0ee1bd51be6a0bafb97840256faa07084c5763ec6f2a801dda80593089c852` |
| Rating provenance file | `6d2f7f9d0efe6dbf4866b3ba2e4878bc069fcda8cde730a11c389e052e534247` |
| Unblinded summary file | `51ae979e96128d4aebacfb8645ff7c6eabffde82b14d68ee3437bddc1c375f20` |

Score chunk 해시는 `ce1651a0…`, `8b4c2315…`, `a4092e80…`이고 blind packet 해시는 `c269ea80…`, `ca304330…`, `c45848f7…`로 score lock과 rating provenance에서 일치한다. 또한 unblinding 전후 strict success 총계 402가 일치한다. 이는 **제공된 스냅샷 내부의 해시·계수 일관성**을 지지한다.

## 9. 무결성·사전등록 준수 판정

내부 일관성과 전체 protocol 준수는 구분해야 한다.

| 점검 | 판정 | 근거 |
|---|---|---|
| 스냅샷 내부 해시·계수 일관성 | 통과 | capture hash, blind packet/score chunk hash, 540개 ID, strict success 402가 대응 |
| 사전 source-freeze 완전성 | **실패/제한** | Protocol은 capture/replay/scorer source의 사전 동결을 요구하지만 `FREEZE.json`에는 사후 사용된 `evals/mechanism_blind.py`, `evals/mechanism_score_verify.py`, `evals/mechanism_rating_reconcile.py`, `evals/mechanism_summary.py` source hash가 없음 |
| 사람의 raw-packet 감사 | **증거 없음** | Protocol은 discordance·reviewer reject/수정·채점 불일치의 사람 감사를 요구하지만 제공 산출물은 AI preliminary rating/adjudication만 기록 |
| Blind key 미개봉의 독립 증명 | **확립되지 않음** | 내부 상태 문자열과 hash는 있으나 외부 timestamp, key access log, 제3자 custody 기록이 없음 |
| 계획된 분석 row 수 | **명목 편차** | Protocol은 shadow를 포함해 630 rows를 적었지만 semantic score는 byte-identical shadow를 `ar-consumer-rule` 점수로 재사용해 540 rows만 저장함. 정보 손실은 없으나 계획 문구와 다름 |
| 출판 가능성 | **`publishable=false`** | 두 summary의 명시값 |

따라서 이 묶음은 **완전히 protocol-compliant한 증거나 독립 검증된 contest-ready evidence가 아니다.** 스냅샷 검증은 내부 재현성 점검에는 유용하지만, 사전등록 준수와 독립적 신뢰성을 대신하지 않는다.

## 10. 한계와 허용되는 해석

- 이미 사용하고 결과를 열람한 30개 synthetic case를 재사용했다. 독립 held-out 표본이 아니며 연구 자체가 exploratory다.
- 모델은 Gemma(`gemma4:26b`) 하나뿐이다. 다른 모델·언어·실제 사내 문서·오픈소스 저장소·생산 환경으로 일반화할 수 없다.
- 채점은 AI preliminary rating이며, 독립 인간 검증이 없다. Protocol이 요구한 human raw-packet audit의 수행 증거도 제공되지 않았다.
- `N=30 case`다. 세 seed는 동일 case의 반복 생성이며 `N=90`으로 세면 안 된다.
- Exact sign-flip `p` 값은 작은 case 수, 많은 동률, 탐색 분석 및 무결성 제한 아래의 기술값이다. 확증적 p-value가 아니다.
- Treatment 길이를 맞췄더라도 A/R 철학만의 순수 인과 효과, live loop의 Node4 단독 효과, reviewer 적용 코드 자체의 의미론적 진실 판별 능력을 입증하지 않는다.
- 이 결과는 SongRyeon 전체가 단일 agent보다 우수하다는 주장, 생산 배포 안전성, 대회 성과 또는 AGI 안전성 주장을 지지하지 않는다.

허용되는 해석은 제한적이다. 즉, **재사용 synthetic evidence replay에서 특정 증거 소비 규칙과 evidence reviewer enforcement가 매칭된 대조와 어떤 탐색적 관계를 보였는지**를 보고한 것이다. 특히 evidence enforcement의 laundering 감소는 후속 독립 연구에서 재검증할 후보 신호이지만, 이번 사전 판정은 그대로 `NO-GO`다.

## 11. 근거 산출물

- [사전 protocol](../evals/arm_mechanism_cases/PROTOCOL.md)
- [실행 계획](../evals/arm_mechanism_cases/RUN_PLAN.json)
- [사전 freeze manifest](../evals/arm_mechanism_cases/FREEZE.json)
- [운영 요약](../.tmp/evals/arm_consumption_mechanism_v1/operational_summary.json)
- [블라인드 해제 결과 요약](../.tmp/evals/arm_consumption_mechanism_blind_v1/unblinded_summary.json)
- [Score lock](../.tmp/evals/arm_consumption_mechanism_blind_v1/score_lock.json)
- [Rating provenance](../.tmp/evals/arm_consumption_mechanism_blind_v1/rating_provenance.json)
