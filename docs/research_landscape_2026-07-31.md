# 송련 연구 지형과 AX 포지셔닝

> 조사 기준일: 2026-07-31
> 목적: 송련의 A/R 분류가 어떤 연구 문제에 속하며, 이미 존재하는 기술과
> 무엇이 겹치고, 어디에 집중해야 하는지 결정한다.

## 결론

송련이 낄 자리는 있다. 다만 그 자리는 “기억이 있는 멀티에이전트”나
“실행 로그를 남기는 코딩 에이전트”가 아니다. 그 기능들은 이미 제품,
오픈소스 관측 도구, 표준과 최신 연구에 널리 존재한다.

현재 가장 방어 가능한 위치는 다음과 같다.

> **에이전트가 주장한 것과 시스템에서 실제로 일어난 일을 서로 다른
> 권위로 기록하고, 최종 주장을 근거 사건에 연결하는 모델 독립형
> claim–action provenance 계층**

송련은 무엇이 현실에서 참인지 전부 판정하려는 시스템이 아니다. 대신
다음을 보장하려는 작은 런타임이다.

1. 모델이 만든 해석은 모델의 주장으로 남는다.
2. 런타임이 관측·적용한 사건은 모델이 다시 써서 만들 수 없다.
3. 모델은 자신의 주장을 런타임 관측 사실로 승격할 수 없다.
4. 중요한 주장은 어떤 사건 기록을 근거로 삼았는지 표시한다.
5. 근거가 없거나 연결을 확인하지 못하면 확실한 사실처럼 통과시키지 않는다.

## A/R을 어떻게 설명해야 하는가

현재 코드의 `absolute`와 `relative` 이름은 내부 호환을 위해 당장 바꾸지
않아도 된다. 그러나 외부 발표에서는 다음 뜻으로 한정해야 한다.

- **A — Attested event**: 정해진 신뢰 경계 안에서 코드가 직접 관측하거나
  적용했고, 모델에게 수정 권한을 주지 않은 사건 기록
- **R — Reported/Reasoned claim**: 사용자·문서·모델이 말하거나 해석한
  내용으로, 그 의미의 참을 코드만으로 보장하지 않는 주장

`absolute`를 “우주의 절대진리”로 설명하면 코드 버그, 잘못된 시계, 손상된
파일, 악성 런타임 같은 반례 하나로 무너진다. A는 **무오류**가 아니라
**권한과 출처가 고정된 관측 기록**이다.

### A 봉투와 R 의미

사용자 발화와 문서에는 두 층이 함께 있다.

```text
A: 14시 31분에 사용자 U가 문자열 X를 입력했다고 런타임이 기록했다.
R: 문자열 X가 주장하는 명제는 참이다.
```

파일도 같다.

```text
A: 도구 T가 경로 F에서 바이트열 X를 반환했다.
R: X 안의 설명은 현실에 대해 참이다.
R: X 안의 코드는 안전하다.
```

이 구분은 철학의 [증언 인식론](https://plato.stanford.edu/entries/testimony-episprob/)과
잘 맞는다. 누군가 어떤 말을 했다는 사건과 그 말을 믿어도 된다는 정당화는
서로 다른 문제다. [인식적 근거 관계](https://plato.stanford.edu/entries/basing-epistemic/)도
좋은 근거가 존재하는 것과 실제 믿음이 그 근거에 기초해 형성되는 것을
구분한다. 송련은 이 “어떤 주장이 실제로 어느 근거에 기초했는가”를
실행 기록으로 만들 수 있다.

## 이미 존재하여 차별점이 될 수 없는 것

다음만으로는 송련의 독창성을 주장할 수 없다.

- JSONL이나 데이터베이스에 도구 호출을 기록한다.
- 원본 로그와 요약된 모델 문맥을 분리한다.
- 로컬 모델을 사용한다.
- 여러 모델 노드가 서로 검토한다.
- LLM-as-a-judge로 답변을 평가한다.
- append-only 형식으로 이벤트를 추가한다.
- 최종 답변에 인용이나 근거 ID를 붙인다.

[W3C PROV](https://www.w3.org/TR/prov-overview/)는 이미 provenance를
Entity–Activity–Agent와 생성·사용·파생·귀속 관계로 표현한다.
[OpenTelemetry의 GenAI 관측 규약](https://opentelemetry.io/blog/2026/genai-observability/)은
모델 호출, 토큰, 프롬프트·응답, 도구 호출·결과를 구조화해 추적한다.
[C2PA Content Credentials](https://spec.c2pa.org/specifications/)는
콘텐츠의 출처와 변경 이력을 암호학적으로 결박한다. 출처 이력이 콘텐츠
내용의 진실을 자동 보장하지 않는다는 점도 송련의 A/R 경계와 같다.

[LLM information-flow 연구](https://www.microsoft.com/en-us/research/publication/permissive-information-flow-analysis-for-large-language-models/)와
[Microsoft FIDES](https://learn.microsoft.com/en-us/agent-framework/agents/security)도
모델 바깥의 코드가 데이터 label을 전파하고 민감한 도구 실행을 결정론적으로
허용·차단하는 방향을 보여준다. 따라서 “label을 붙이고 코드가 막는다”도
그 자체로 새롭지는 않다. 다만 이들은 주로 보안 무결성·기밀성과 행동 권한을
다루고, 송련은 **모델 발언의 인식론적 권한**을 다룬다는 차이를 실험할 수
있다. A/R을 개발자에게 설명할 때 `epistemic taint tracking`이라는 비유가
유용하지만, 보안 taint와 동일한 문제라고 주장해서는 안 된다.

### 2026년의 직접 경쟁 연구

아래 연구는 송련과 매우 가깝다. 모두 최신 arXiv 공개본이므로 유용한
선행연구이지만, 동료평가가 끝난 확정적 결과처럼 인용해서는 안 된다.

| 연구 | 이미 구현한 핵심 | 송련에 남기는 과제 |
|---|---|---|
| [Eywa](https://arxiv.org/abs/2605.30771) | 불변 source evidence, 파생된 typed fact, 결정론적 bounded memory view, 기억과 답변 정책 분리 | “원본/시야 분리”만으로는 새롭지 않다. 모델의 A 발행 권한을 막는 규칙과 효과를 보여야 한다. |
| [ProvenanceGuard](https://arxiv.org/abs/2606.18037) | MCP trace의 안정된 tool/source ID, 원자 claim 분해, source별 support 및 attribution 검사, allow/block | 단순 Node4보다 강하다. 송련도 답변 전체가 아니라 claim별 evidence ID를 가져야 한다. |
| [TRACER](https://arxiv.org/abs/2605.09934) | 답변 문장마다 tool turn, evidence unit, support relation을 함께 생성·검증 | “근거 ID를 붙인다”도 부족하다. 원문 인용·압축·추론처럼 관계 종류를 검증할 필요가 있다. |
| [AgentTrace](https://arxiv.org/abs/2602.10133) | 운영·인지·문맥 표면의 구조화된 런타임 trace | 로그 수집은 독창성이 아니라 입력 기반이다. |
| [Agent Traces to Trust 조사](https://arxiv.org/abs/2606.04990) | evidence tracing, execution provenance, memory lineage, runtime guardrail을 하나의 연구 지형으로 정리 | 송련을 이 분야의 작고 재현 가능한 reference runtime으로 위치시킬 수 있다. |

이 선행연구는 송련을 죽이는 자료가 아니라 **주제를 정확히 이름 붙여 주는
자료**다. 다만 “내가 처음 생각했다”는 주장을 포기하고, 더 좁고 측정 가능한
가설을 세워야 한다.

## 철학과 컴퓨터과학에서 얻는 설계 근거

### 1. 증언은 사건과 진실을 분리한다

[Hardwig의 Epistemic Dependence](https://doi.org/10.2307/2026523)는
현대 지식이 자신이 전부 재검증할 수 없는 타인의 전문적 증언에 의존한다는
문제를 다룬다. 송련은 “누가 무엇을 말했다”를 A로 보존하되, 그 말의 내용을
곧바로 A로 만들지 않는 방식으로 이 의존 관계를 드러낼 수 있다.

### 2. R은 고정된 참/거짓보다 가결적 상태에 가깝다

[Pollock의 defeasible reasoning](https://doi.org/10.1207/s15516709cog1104_4)은
많은 합리적 결론이 반박 정보가 생기기 전까지만 유지된다는 점을 다룬다.
향후 R에는 A/R과 별개의 축으로 아래 상태를 붙일 수 있다.

```text
supported / contradicted / unresolved
```

여기서 `supported`도 “현실의 절대진리”가 아니라 지정된 근거가 해당 주장을
지지한다는 검증 결과다.

### 3. 결론보다 근거 의존 관계가 중요하다

[Doyle의 Truth Maintenance System](https://doi.org/10.1016/0004-3702(79)90008-0)은
믿음의 이유와 의존 관계를 기록해야 모순이 생겼을 때 관련 결론을 철회하고
설명할 수 있음을 보여준다. 송련의 다음 핵심 자료형은 단순 답변 문자열보다
`claim → evidence` 연결이어야 한다.

[FActScore](https://aclanthology.org/2023.emnlp-main.741/)도 긴 답변을 원자
사실로 분해하고 각 사실이 자료에 의해 지지되는지를 따로 평가한다.
[ALCE](https://aclanthology.org/2023.emnlp-main.398/)는 인용의 존재,
인용 정확성, 인용 완전성, 답변 품질을 서로 다른 평가축으로 다룬다.

### 4. 출처에는 “왜”와 “어디서”가 모두 필요하다

[Why- and Where-Provenance](https://www.research.ed.ac.uk/en/publications/why-and-where-a-characterization-of-data-provenance)는
결과가 왜 생겼는지와 값이 정확히 어디에서 복사됐는지를 구분한다.
송련에 대응시키면 다음과 같다.

- why: 이 답변 주장이 어떤 도구 활동과 판단 때문에 생겼는가?
- where: 주장의 근거 본문은 어느 파일·도구 결과·문자 범위에서 왔는가?

현재 `source`, `action`, `tool_result_content`는 출발점이지만, 최종
`node3_answer`와 근거 사이의 명시적 edge가 아직 없다.

## 한 분류에 모든 의미를 넣지 않는다

A/R 하나로 출처, 무결성, 의미의 참, 근거 충분성을 모두 표현하면 다시
혼란이 생긴다. 아래는 서로 다른 축이다.

| 축 | 질문 | 예시 |
|---|---|---|
| authority class | 누가 이 값을 발행·수정할 권한이 있는가? | A / R |
| provenance | 누가·언제·무엇을 사용해 만들었는가? | actor, event, parent ID |
| integrity | 저장 뒤 바뀌지 않았음을 확인했는가? | hash, signature, unverified |
| support | 특정 근거가 이 주장을 지지하는가? | supported / contradicted / unresolved |
| freshness | 지금도 유효한 관측인가? | observed_at, superseded_by |

이 표는 지금 당장 원본 7필드를 전부 바꾸라는 뜻이 아니다. 현재 구조를
유지하면서 다음 실험에 필요한 `claim`과 `evidence_ids`부터 별도 자료형으로
추가하는 것이 작고 안전하다.

## AX에서 생기는 자리

AX는 단순히 모델을 업무에 붙이는 단계에서, 에이전트가 실제 도구와 조직
데이터를 사용하도록 만드는 단계로 이동하고 있다. 이때 문제는 “AI를
썼는가”뿐 아니라 “무엇을 읽고, 무엇을 했으며, 어떤 근거로 말했는가”다.

- [NIST AI Agent Standards Initiative](https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative)는
  2026년부터 agent 인증·신원, 안전 평가, 상호운용 표준을 주요 축으로
  다루고 있다.
- [NIST GenAI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)은
  생성형 AI 위험을 조직이 측정·관리하기 위한 자발적 프레임워크다.
- [ISO/IEC 42001](https://www.iso.org/standard/42001)은 AI 경영시스템에서
  위험관리, 추적성, 투명성, 신뢰성을 조직 절차로 다룬다.
- [한국 인공지능기본법](https://www.law.go.kr/LSW/lsInfoP.do?efYd=20260122&lsiSeq=282791)은
  2026년 1월 시행됐고 안전성과 신뢰를 기본 원칙으로 둔다.
- [행정안전부 공공부문 AI 도입·활용 가이드](https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=126757)는
  공공 AI 도입을 기획부터 운영까지 관리하는 표준 절차를 제시한다.
- [EU AI Act의 적용 일정](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)은
  단계적으로 진행 중이며 투명성·로그·감독·문서화 요구가 중요해지고 있다.

이 자료들은 송련이 법률 준수를 자동으로 보장한다는 뜻이 아니다. 현재
송련은 인증 제품도, 변조 방지 원장도, 고영향 AI 규제 솔루션도 아니다.
정확한 주장은 **감사와 설명에 사용할 실행 증거 묶음을 만드는 실험적
기반**이라는 것이다.

### 현실적인 사용처 순서

1. **코드·문서 조사 에이전트**
   - 읽은 파일, 결과, 선택 근거, 최종 코드 주장을 연결한다.
   - 현재 도구와 평가 fixture로 바로 시연할 수 있다.
2. **사내 규정·업무문서 답변 에이전트**
   - 문서 버전과 문단을 claim별로 연결하고 미지원 주장을 표시한다.
   - 이후 knowledge DB 검색 도구가 연결되면 자연스럽게 확장할 수 있다.
3. **도구 사용 에이전트의 행동 감사**
   - 모델이 하겠다고 한 행동 R과 실제 호출·인자·결과 A를 비교한다.
   - 모델 종류나 에이전트 프레임워크에 독립적인 middleware가 목표다.
4. **모델·프롬프트 교체 비교**
   - 같은 요청에서 근거 없는 주장률, 행동–보고 불일치, 비용을 비교한다.

의료·금융·채용 판단은 장기 사용처가 될 수 있지만 현재 대회 MVP로 삼으면
도메인 진실과 법적 책임까지 떠안게 되므로 피한다.

## 대회에서 검증할 세 가설

### H1. 권한 경계

> 모델이 실행 사실 A를 직접 생성하거나 승격하지 못하게 하면, 모델의
> 실제 행동 오보고가 기준선보다 줄어든다.

### H2. claim–evidence 결박

> 최종 코드 주장을 원자 단위로 나누고 유효한 근거 ID를 요구하면, 근거 없는
> 코드 주장률이 답변 전체를 한 번 검토하는 방식보다 줄어든다.

### H3. 혼합 검증

> ID 존재·출처·범위·시각은 코드가 검사하고 의미적 지지 여부만 모델이
> 검사하면, LLM 검토자 하나에게 전부 맡길 때보다 오류가 줄면서 유용한
> 답변의 완료율을 유지한다.

## 다음 MVP의 최소 자료 흐름

```text
도구·런타임 사건
  ↓ 코드가 event_id와 원문 위치를 부여
A evidence records
  ↓
Node3가 답변과 원자 claim + evidence_ids를 생성(R)
  ↓
코드 검증
  - ID가 실제 존재하는가?
  - 현재 턴 또는 허용 범위의 A인가?
  - 공개된 원문 범위를 가리키는가?
  ↓
Node4 의미 검증
  - 이 근거가 실제로 claim을 지지하는가?
  - 단순 인용, 충실한 압축, 추론 중 어느 관계인가?
  ↓
verified / contradicted / unresolved와 최종 답변
```

Node4가 모든 것을 판단하면 현재처럼 판정 이유를 복사하거나 반려 횟수를
혼동할 수 있다. 반대로 코드는 자연어 함의를 전부 판정할 수 없다. 따라서
**구조 무결성은 코드, 의미 관계는 제한된 모델 판단**으로 분리하는 것이
송련 철학과 가장 잘 맞는다.

## 비교 실험

현재 `evals/`의 세 구조는 올바른 출발점이다.

1. 같은 모델의 단일 도구 에이전트
2. 원본 기록과 증거 수집은 있지만 최종 claim audit가 없는 송련
3. 전체 송련

같은 모델·도구·입력·시간 예산으로 아래 실패를 넣는다.

- 읽지 않은 파일을 읽었다고 주장
- 실패한 도구를 성공했다고 주장
- 선언한 도구와 실제 실행 도구가 다름
- 일부 청크만 읽고 파일 전체의 부재를 단정
- 파일이 관측 뒤 변경됨
- 과거 턴의 낡은 R을 현재 A보다 우선
- 존재하는 근거를 엉뚱한 주장에 연결
- 근거 ID는 맞지만 원문이 주장을 지지하지 않음

주요 측정값:

- 실행 사실 exact match
- 행동–보고 불일치 탐지율
- unsupported claim rate
- 잘못된 source attribution rate
- 검증기의 오탐·미탐
- 작업 완료율과 사람 유용성 평가
- 모델 호출 수, 토큰·문자 수, 지연시간

성능 주장은 각 그룹을 충분히 확장하고 사람이 원시 trace와 정규화 결과를
검토한 뒤에만 한다.

## 구현 우선순위

1. Node3 출력에 `claims`와 `evidence_ids`를 추가한다.
2. 코드가 ID 존재·출처·공개 범위·현재성 계약을 검사한다.
3. Node4의 책임을 claim–evidence 의미 관계 검사로 좁힌다.
4. 평가 fixture에 잘못된 근거 연결과 행동–보고 불일치를 추가한다.
5. 그 뒤 OpenTelemetry 또는 W3C PROV와의 export/import 매핑을 만든다.
6. 변조 방지를 주장하려면 마지막에 hash chain 또는 서명을 추가한다.

현재 JSONL은 추가 기록 형식이지 암호학적으로 불변인 원장이 아니다.
hash chain 전에는 발표에서 `tamper-proof`나 “변조 불가능”이라고 부르지
않는다.

## 최종 포지셔닝 문장

대회와 README에서 가장 안전하고 강한 문장은 다음이다.

> **송련은 AI를 더 똑똑하게 만드는 에이전트가 아니다. 모델이 무엇을
> 주장했고 시스템이 실제로 무엇을 관측·실행했는지 분리하고, 중요한
> 주장을 근거 사건에 연결해 근거 없는 확실성이 조용히 통과하지 못하게
> 하는 오픈소스 증거 런타임이다.**

조금 더 연구적으로 표현하면 다음과 같다.

> **SongRyeon is a model-independent reference runtime for enforcing an
> authority boundary between system-attested events and revisable model
> claims, then evaluating claim-to-evidence grounding over agent traces.**

이 위치에서는 Codex, OpenTelemetry, W3C PROV와 경쟁할 필요가 없다. 그들이
만드는 실행 이벤트를 송련이 입력으로 받아 claim–evidence 계약을 검사하는
보완 계층으로 확장할 수 있다.
