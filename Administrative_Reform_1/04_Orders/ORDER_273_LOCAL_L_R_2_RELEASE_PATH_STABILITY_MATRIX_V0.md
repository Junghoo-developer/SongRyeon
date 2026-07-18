# ORDER 273: Local L/R/2 Release Path Stability Matrix v0

## 1. 배경

2026-07-10의 자율 L/R/2 시험에서는 다음 문제가 남았다.

- R2가 ORDER 139 요청에서 ORDER 090 가지를 선택함
- node_4가 질문과 관련 없는 R 답변을 pass함
- route 2가 한 문장 요청 대신 내부 실행 절차를 길게 설명함
- 일부 Vessel 문자열 guard가 사용자 표현을 graph claim으로 오해함

그 뒤 R 계층 탐색·목표 계약·node_3/4 경계와 L 코드 읽기·L3 결속이 여러 차례
수정됐다. 현재 제품 상태를 말하려면 같은 종류의 경로를 다시 분리해 확인해야 한다.

## 2. 목표

새 기능을 추가하지 않고, 현재 로컬 runtime의 대표 경로를 같은 시점에 실행해
`통과 / 부분 통과 / 실패 / 환경 미확인`으로 분류한다.

## 3. 시험 원칙

1. 경로 배선 시험과 node_1 자율 선택 시험을 섞지 않는다.
2. L/R 경로는 force flag로 먼저 고정해 내부 경로 자체를 검사한다.
3. route 2는 도구가 필요 없는 간단한 사용자 명령으로 자연 선택을 검사한다.
4. R은 기존 Vessel 환경이 사용 가능할 때만 live로 실행한다.
5. Neo4j 인증정보 값은 문서·출력·export에 기록하지 않는다.
6. 결과 평가는 runtime의 trace/data/status/count를 절대정보로 삼고, 답변 품질 평가는
   별도 상대적 감사 의견으로 표시한다.

## 4. 시험 사례

### A. route 2 직접 응답

입력:

```text
오늘 테스트를 끝낸 나에게 한 문장으로 수고했다고 말해줘.
```

기대:

- final route 2
- L/R 실행 0회
- node_3 ran, node_4 pass
- 사용자 답변은 실제 한 문장

### B. L 내부 문서 원문

입력:

```text
내부 문서 ORDER_270을 직접 읽고 direct Ollama timeout 정책을 짧게 설명해줘.
```

조건: `--force-l`

기대:

- L 실행 1회
- 실제 문서 원문 1개 이상
- L3 semantic execution `ran`, failure `none`
- node_4 pass

### C. L 외부 업무 폴더 코드 원문

입력:

```text
workspace_policy.py를 직접 읽고 이 파일이 외부 업무 폴더 읽기 경계를 어떻게 제한하는지 설명해줘.
```

조건: `--workspace songryeon_core/tools --force-l`

기대:

- 실제 `read_code_file` 원문 1개 이상
- path/range/truncation 절대정보 보존
- L3 semantic execution `ran`, failure `none`
- node_4 pass

### D. Vessel R 그래프 원문

입력:

```text
Vessel R 그래프 기억에서 ORDER 090 L Loop Budget Plan을 찾아 요약 계층을 따라 RawSource 원문까지 확인하고 핵심을 설명해줘.
```

조건: Vessel local env + `--force-vessel-r-route --enable-vessel-r-route`

기대:

- R read packet passed
- R task sufficient 또는 partial 이유 명시
- RawSource 원문을 확보했다면 node_3 material에 전달
- 잘못된 ORDER 가지를 선택하면 실패로 분류
- node_4가 관련 없는 답을 pass하면 별도 실패로 분류

### E. 결정론적 공개 차단

명령:

```powershell
python main.py competition-demo
```

기대:

- LOCAL, HONEST FALLBACK, CODE GUARD 모두 PASS
- 최종 `SONGRYEON_COMPETITION_DEMO_OK`

## 5. 판정 경계

- **통과**: 절대 성공 조건을 모두 충족하고 최종 답변이 사용자 명령을 수행함
- **부분 통과**: 경로·실패 정직성은 맞지만 목표 달성이나 답변 수행이 부족함
- **실패**: 구조 실패, 근거 역할 위반, 관련 없는 답변 pass, 상태 은폐
- **환경 미확인**: 인증/서버/모델 상태 때문에 제품 로직까지 도달하지 못함

## 6. 금지

- 시험 중 schema validator, router, prompt를 즉시 고쳐 결과를 덮기
- force 결과를 자율 라우팅 성공으로 표현
- R partial을 sufficient로 표현
- Neo4j 비밀번호 기록
- 도구 예산·반복 횟수 확대
- 새 기능 구현

## 7. 완료 조건

1. 다섯 사례의 명령·절대 결과·상대 평가를 실행 기록에 남긴다.
2. 실패가 있으면 코드부터 고치지 않고 원인과 다음 발주 후보를 분리한다.
3. 현재 배포 가능 범위와 아직 실험 플래그에 남길 범위를 구분한다.
4. 작업 트리를 변경하지 않는 시험 산출물은 cache에만 둔다.

## 8. 후속 경계

ORDER 273은 감사·시험 발주다. 확인된 첫 번째 고위험 실패만 다음 발주로 좁히며,
여러 실패를 한 패치에 합치지 않는다.
