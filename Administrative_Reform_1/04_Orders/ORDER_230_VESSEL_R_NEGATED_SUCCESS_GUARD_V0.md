# ORDER 230: Vessel R Negated Success Guard v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: node_3 grounding wording / node_4 Vessel R guard

## 배경

ORDER 229 이후 live Vessel R 강제 테스트에서 R2 schema 실패는 사라졌다.
R 탐색은 5개 재료를 node_3에 넘겼지만 `r_loop_task_status=partial`이었다.

node_3 보고문은 R 결과가 부분적이라고 말했지만, code가 만든 grounding block 안의 `graph memory 탐색 성공으로 단정하지 않는다`라는 부정문을 node_4 정규식 guard가 성공 주장으로 오탐했다.

## 목표

R/Vessel 결과가 partial일 때 성공을 단정하지 않는 안전 문장이 node_4에 의해 반려되지 않게 한다.
동시에 진짜 성공 과장은 계속 차단한다.

## 변경

- node_3 grounding limit 문구에서 `성공으로 단정하지 않는다` 표현을 `요구 수준에 도달했다고 보지 않는다`로 바꾼다.
- node_4의 Vessel R success claim guard가 부정문 context를 오탐하지 않게 한다.
- 부정문 예:
  - `graph memory 탐색 성공으로 단정하지 않는다`
  - `R 탐색이 충분하다고 단정할 수 없다`
- 단, `Vessel R 탐색은 성공했고 충분했다` 같은 실제 성공 과장은 기존처럼 차단한다.

## 하지 않는 것

- node_4 guard를 제거하지 않는다.
- Vessel R partial을 sufficient로 바꾸지 않는다.
- node_3가 partial 결과를 성공처럼 말하게 허용하지 않는다.
- R 루프 탐색 전략 자체는 바꾸지 않는다.

## 완료 조건

- partial Vessel R grounding block이 `성공` 단어 때문에 node_4에서 오탐 반려되지 않는다.
- partial 상태를 성공으로 말한 진짜 문장은 계속 반려된다.
- quick-smoke가 유지된다.
