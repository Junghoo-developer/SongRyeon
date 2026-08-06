# 대회용 근거 권한 holdout 비교실험 v1

## 질문

같은 로컬 `gemma4:26b`를 사용할 때 송련의 A/R 권한 분리와 Node4가 코드보다 강한
결론을 사실처럼 말하는 **근거 세탁**을 줄이는가?

이 case는 기존 `model_ceiling`, `evidence_laundering`, `arm_mechanism` 결과를 다시
채점하거나 재포장한 것이 아니다. 새 파일명, 새 코드, 새 질문으로 만든 동결 후보이며 첫
live 출력 전에 최종 SUT와 함께 별도 동결해야 한다.

## 조건

모델, digest, context, temperature, seed, timeout, 도구, fixture와 턴당 도구 호출 상한은
같게 유지한다.

1. `single-tool-agent`: Node2와 Node4가 없는 단일 도구 에이전트
2. `songryeon-no-node4`: A/R 기억과 Node1·Node2를 사용하고 Node4만 결정론적으로 통과
3. `songryeon-full`: Node1~Node4 전체 사용

`no-node4`와 `full`의 차이는 end-to-end Node4 활성 조건의 차이다. 독립 실행의 Node3
초안이 byte 단위로 같다고 보장하지 않으므로 이를 “Node4 하나의 순수한 인과효과”라고
부르지 않는다.

## case 구성

24개 case는 네 축마다 negative 3개와 positive 3개를 가진다.

- 상수 선언과 실제 집행
- import와 실제 호출
- 주석/docstring과 런타임 반환
- 과거 R 기억의 주장과 이번 턴 현재 코드 A

마지막 축의 case는 과거 Node1 review 형식의 R을 격리 기억에 심고, 현재 파일 원문 A와
충돌시킨다. positive control은 무조건 부정하는 시스템을, negative control은 사용자의
거짓 전제·표면적 텍스트·과거 R에 순응하는 시스템을 함께 잡는다. 압박형 문구는 positive
6개와 negative 6개에 같은 문장으로 넣고, 중립형도 양쪽 6개씩 둔다. category 안에서도
압박 유무와 label 수가 같아 질문 문구만으로 정답을 예측할 수 없게 한다. 각 질문은 첫 줄에
두 개 중 하나의 고정 verdict를 쓰게 하여 핵심 판단을 결정론적으로 채점한다.

## 실행 단위

세 seed와 순환된 variant 순서를 사용한다. 총 실행은
`24 cases × 3 variants × 3 seeds = 216`이다. seed 반복은 독립 case가 아니라 같은
case의 안정성 관측이다. 오류·timeout·형식 실패를 제거하거나 다시 뽑지 않는다.

## 동결과 블라인드

최종 코드 수정이 끝난 뒤 `python -m evals.contest_holdout_v1.protocol freeze`를 단 한 번
실행한다. 이 명령은 비어 있는 `.tmp` 실험 루트에 다음을 배타적으로 만든다.

- case/protocol/scorer와 SUT source tree 해시를 담은 `FREEZE.json`
- 결과 전에 모든 case×variant×seed를 blind ID로 대응시킨 `BLIND_KEY.json`
- key·mapping commitment와 사전 표본을 담은 `BLINDING_COMMITMENT.json`

trusted packetizer만 결과를 blind ID에 붙이기 위해 `BLIND_KEY.json`을 사용한다. 채점자와
리뷰어에게는 key를 주지 않으며, 조건을 가린 verdict 점수 lock이 생긴 뒤에만 unblind한다.
각 block은 freeze가 출력한
manifest hash, SUT hash, 모델 digest를 `evals.live_capture` 인자로 강제한다. raw artifact와
실패를 모두 보존한다.

## 공개 가능성

결과가 좋다는 이유만으로 publishable이 되지 않는다. 다음이 전부 참이어야 한다.

- 최종 동결 뒤 SUT와 protocol이 바뀌지 않음
- 216개 raw capture와 hash가 모두 존재
- trusted packetizer가 만든 조건 은닉 packet에서, 채점자는 key 없이 기계 verdict를 lock
- 점수 lock 뒤 조건과 정답을 unblind
- score lock hash와 secret·mapping을 묶은 `REVEAL.json`을 공개해 제3자가 commitment와
  unblind 결과를 다시 계산 (`scorer verify-public`)
- 최종 publication gate가 private raw JSONL에서 blind packet과 summary를 읽기 전용으로
  다시 계산해, 결과 파일의 self-hash만 바꾼 사후 조작을 거부
- 실패·오답 전부와 사전 추출된 blind 표본을 사람이 확인
- 제외된 case나 재실행 대체가 없음
- 공개 문구가 이 합성 Python holdout의 범위를 넘지 않음

방향성 gate를 통과하지 못해도 무결한 결과 자체는 공개할 수 있지만, “송련이 두 비교군보다
개선했다”는 문장은 사용할 수 없다.
