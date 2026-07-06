# Source Lineage And Summary-First Surface Philosophy - 2026-07-05

이 문서는 2026-07-05 대화에서 정리된 임시 철학 문서다.

핵심 질문은 두 가지였다.

1. 왜 자료를 굳이 동적/정적으로 크게 나누어야 하는가?
2. 왜 그래프에서 `TimeBundle` 또는 `SourceKindBundle` 다음에 바로 요약 layer가 아니라 원본 node가 먼저 보이는가?

현재 결론은 다음과 같다.

## 1. 동적/정적 분류는 주인이 아니다

자료의 유효성을 판단하는 주인은 `dynamic/static` 같은 큰 딱지가 아니다.

더 중요한 절대정보는 다음이다.

- `observed_at`: 이 원본을 언제 관측했는가.
- `content_hash` 또는 `content_sha1`: 관측 당시 원본 내용의 지문은 무엇인가.
- `source_version_id` 또는 source graph node id: 이 관측본의 버전 좌표는 무엇인가.
- `summary_source_version_ids`: 요약이 어떤 원본 버전을 보고 만들어졌는가.
- `summary_created_at`: 요약이 언제 만들어졌는가.
- `invalidated_at`: 요약이 언제 무효화되었는가.
- `invalidated_by`: 어떤 원본 변경 때문에 무효화되었는가.

따라서 요약이 유효한지 판단할 때 핵심 질문은 다음이다.

```text
이 요약이 본 원본 버전이, 지금도 해당 원본의 최신 활성 버전인가?
```

예를 들면 다음과 같다.

```text
source A v1: content_hash=aaa
summary S1: source A v1을 보고 생성됨

나중에 source A를 다시 관측함
source A v2: content_hash=bbb

그러면 S1은 A v1에 대한 요약으로는 보존되지만,
A v2에 대한 최신 요약으로 쓰면 안 된다.
```

여기서 중요한 것은 `source A`가 동적 자료인지 정적 자료인지가 아니다.
중요한 것은 실제 내용 hash가 바뀌었는지, 그리고 기존 요약이 어떤 버전을 바라보고 있었는지다.

## 2. 동적/정적 분류의 낮은 역할

동적/정적 분류를 완전히 없앨 필요는 없다.

다만 이 분류는 진리 판단의 주인이 아니라 운영 정책의 힌트로만 둔다.

예:

- 대화 턴 캡슐: append-only에 가깝다.
- 코드 파일: 자주 바뀔 수 있다.
- 내부 문서: 바뀔 수 있다.
- 외부 웹/API: 더 자주 바뀔 수 있다.

이 분류는 다음을 정할 때만 도움 된다.

- 얼마나 자주 다시 관측할지.
- 변경 감지를 얼마나 강하게 할지.
- 바뀌면 파생 요약을 얼마나 빨리 무효화할지.

하지만 최종 유효성 판정은 반드시 source version lineage와 hash 비교가 담당해야 한다.

요약하면 다음과 같다.

```text
동적/정적은 운영 힌트다.
버전 lineage가 진짜 판정자다.
```

## 3. 저장 족보와 탐색 지도는 다르다

그래프에는 서로 다른 두 관점이 필요하다.

### 저장/검증/무효화 관점

송련의 메타정보 원칙에서는 절대정보가 먼저 있고, 상대정보/혼합정보는 그 절대정보에서 파생된다.

따라서 저장 족보는 원본 중심이어야 한다.

```text
TimeBundle
-> SourceKindBundle
-> RawSource
-> Summary
```

이 구조는 다음을 지키기 좋다.

- 이 요약이 어떤 원본에서 나왔는지 추적한다.
- 원본이 바뀌었을 때 어떤 요약을 무효화해야 하는지 찾는다.
- LLM 요약이 원본 없이 떠다니지 않게 한다.

즉, 이 구조는 진실성, 출처성, 무효화에 강하다.

### R루프 탐색 관점

하지만 R루프가 그래프를 읽을 때는 처음부터 원본을 많이 보면 안 된다.

R루프는 다음처럼 움직이는 것이 좋다.

```text
1. 큰 묶음이 무엇인지 본다.
2. 그중 관련 있어 보이는 요약 묶음을 고른다.
3. 더 작은 요약으로 내려간다.
4. 정말 필요할 때만 원문을 본다.
```

따라서 R루프용 탐색 지도는 요약 우선이어야 한다.

```text
TimeBundle
-> SourceKindBundle
-> TokenBudgetSummaryLayer
-> TokenBudgetBundleSummary
-> LeafSummary
-> RawSource
```

이 구조는 다음을 지키기 좋다.

- R1/R2/R3의 컨텍스트 부담을 줄인다.
- 후보가 너무 많을 때 먼저 묶음 요약을 보고 방향을 정한다.
- 원문 열람 예산을 아낀다.

## 4. 결론: 두 구조를 분리한다

원본 중심 구조와 요약 우선 구조 중 하나만 고르면 안 된다.

둘은 목적이 다르다.

```text
원본 lineage는 진실을 지킨다.
summary-first surface는 탐색을 돕는다.
```

따라서 그래프에는 다음 관계가 함께 존재할 수 있다.

```text
SourceKindBundle
- CONTAINS_RAW_SOURCE -> RawSource
- HAS_SUMMARY_LAYER -> TokenBudgetSummaryLayer
```

`CONTAINS_RAW_SOURCE`는 저장 족보다.

`HAS_SUMMARY_LAYER`는 R루프가 먼저 걸어야 할 길이다.

이 둘을 섞어서 하나의 길로 만들면 사람이 보기에도 헷갈리고, R루프도 후보 폭탄을 맞기 쉽다.

## 5. 다음 설계 후보

이 문서는 발주서가 아니다.

다만 다음 발주 후보는 다음 두 방향으로 갈 수 있다.

1. `Vessel R material`을 node_3에게 줄 때 내부 graph id 대신 사람용 label, 역할명, 요약으로 감싸는 작업.
2. R루프가 `RawSource`보다 `TokenBudgetSummaryLayer`를 먼저 보도록 summary-first navigation surface를 더 명확히 정리하는 작업.

첫 번째는 live 최종 답변 통과에 가깝다.

두 번째는 장기 그래프 탐색 품질에 가깝다.

둘 다 송련의 기본 원칙과 충돌하지 않는다.

핵심은 다음이다.

```text
요약은 원본에서 파생되어야 한다.
하지만 탐색은 요약을 먼저 봐야 한다.
```

