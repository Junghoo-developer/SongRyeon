# ORDER 252 R1 Evidence Contract 실행 기록

## 1. 작업 범위

- R1 LLM 출력에서 그래프 최소 깊이, 최소 노드 수, 최소 terminal material 수를 제거했다.
- 새 R1 출력은 검색 목표, 사용자 질문 anchor, 필요 재료 수준, 최소 재료 개수만 쓴다.
- 필요 재료 수준을 `overview`, `source_summary`, `raw_original` 세 값으로 고정했다.
- 기존 `min_*` 필드는 과거 테스트와 기록 호환용으로 유지했다.
- 새 실행에서는 code가 고유 그래프 노드 ID와 실제 text 존재 여부를 세어 R3 종료를 집행한다.

## 2. 책임 경계

- R1: 질문을 해석해 목표와 근거 계약을 생성한다. `info_class=mixed`, `generated_by=LLM:*` 경계를 유지한다.
- R2: code가 공급한 공식 후보 중 다음 노드를 선택한다.
- R3: 선택 재료의 의미상 충분성과 가지 문제를 판단한다.
- code: 재료 record의 구조 필드와 text 존재 여부, 고유 ID, 안전 상한을 확인한다.
- code는 관련 노드 선택이나 의미상 충분성 판단을 대신하지 않는다.

## 3. 재료 집계 규칙

- `overview`: text가 있는 summary 또는 실제 text가 있는 raw material
- `source_summary`: text가 있는 `source_leaf_summary` 또는 실제 text가 있는 raw material
- `raw_original`: 실제 원문 text가 포함된 RawSource 또는 RawCapsule
- 같은 그래프 노드를 반복 선택해도 한 번만 센다.
- RawSource 이름만 있고 실제 text가 없으면 `raw_original`로 세지 않는다.

## 4. 종료 집행

- 계약 충족 + R3 sufficient: `stop_sufficient`
- 계약 미충족 + 하위 후보와 예산 존재: `continue_deeper`
- 계약 미충족 + 하위 후보 없음: `partial / stop_no_actionable_path`
- 계약 미충족 + 안전 예산 종료: `partial / stop_budget_exhausted`
- one-step 정책도 계약 미충족을 거짓 `sufficient`로 닫지 않는다.

## 5. 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_252_R1_EVIDENCE_CONTRACT_AND_CODE_ENFORCED_STOP_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schema_parts/r_loop.py`
- `songryeon_core/prompts/r1_vessel_goal_setter_v0.md`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/terminal_view.py`
- `tests/test_order_184_r_vessel_multi_step_traversal.py`
- `tests/test_order_227_r1_minimum_traversal_budget.py`
- `tests/test_order_240_r_raw_intent_and_vessel_reporter_focus.py`
- `tests/test_order_252_r1_evidence_contract.py`

## 6. deterministic 검증 결과

```text
python -m compileall songryeon_core main.py
passed

python -m pytest
425 passed, 5 deselected in 76.32s

python main.py smoke-test
SMOKE_TEST_OK

python -m pytest tests/test_order_252_r1_evidence_contract.py tests/test_order_176_vessel_r_one_step_traversal.py -q
11 passed

git diff --check
passed before final execution-record write
```

ORDER 252 회귀 시험에서 확인한 절대정보:

- raw contract path: TimeAxis -> SourceIngest -> SourceKind -> TokenBudgetSummary -> SourceLeafSummary -> RawSource
- 실제 raw original text read count: 1
- evidence contract: `raw_original / required=1 / observed=1 / satisfied`
- text 없는 RawSource: `observed=0 / unmet / partial / stop_no_actionable_path`
- 같은 source leaf summary ID를 두 번 넣어도 observed ID는 한 개

## 7. live Qwen 재시험 중 하드웨어 사고

다음 기존 회귀 문구로 live Qwen 시험을 시작했다.

```text
Vessel R 그래프 기억에서 ORDER 090 L Loop Budget Plan을 찾아 시간축과 요약 계층을 따라 RawSource 원문까지 확인해줘. 원문에 적힌 제안과 안전장치를 현재 실행 사실과 구분해서 설명해줘.
```

최종 런타임 결과가 생성되기 전 화면 신호가 사라졌다. 확인된 시스템 사실:

- `nvidia-smi`: `GPU0 0000:01:00.0 GPU is lost`
- Windows VideoController: RTX 2080 Ti `Status=Error`
- RTX 5080과 Intel UHD: `Status=OK`
- RTX 2080 Ti PnP problem code: `43`
- 2026-07-11 13:09:46 Windows WHEA-Logger event 17
- 내용: PCI Express Root Port의 corrected hardware error
- GPU 탈락 후 Ollama는 qwen3:14b를 `100% CPU`로 계속 처리하고 있었다.

조치:

- 실행 중이던 live Python 시험을 중단했다.
- qwen3:14b를 내리고 Ollama loaded model이 없는 상태를 확인했다.
- 재부팅은 사용자 승인 없이 실행하지 않았다.

따라서 이 live 실행은 `R1/R2/R3 기능 실패`로 판정하지 않는다. 최종 trace가 생성되기 전에
하드웨어가 탈락했으므로 결과는 `검증 중단`이다.

## 8. 남은 위험

- 재부팅 후 동일 live 문구를 한 번 다시 실행해야 한다.
- R1이 요구 개수를 안전 상한 안에서 골라도 실제 그래프 경로 길이 때문에 계약이 달성 불가능할 수 있다. 이 경우 현재 정책은 정직하게 `partial`로 닫는다.
- legacy `min_*` 필드는 아직 스키마에 남아 있다. 제거는 과거 기록 migration 범위를 별도 결재한 뒤 진행한다.
- 이번 작업은 R2의 가지 선택 품질이나 최단 경로 계산을 바꾸지 않았다.
- 최대 raw original 열람 5회는 유지했다.

## 9. 작업트리 경계

작업 시작 전부터 ORDER 251 one-command launcher 관련 미커밋 변경이 있었다. 해당 변경은
되돌리거나 재작성하지 않았다. ORDER 252는 별도 발주서, 코드, 테스트, 실행 기록으로 추가했다.

## 10. 재부팅 후 통제 live 재시험

첫 하드웨어 사고 후 재부팅했을 때 RTX 5080과 RTX 2080 Ti는 모두 정상 인식됐고
problem code는 0이었다. 이후 아버지가 RTX 2080 Ti를 소프트웨어로 의도적으로
비활성화했다. 따라서 그 뒤의 RTX 2080 Ti problem code 22는 사고가 아니라 설정 결과다.

RTX 5080만 활성화한 상태에서 같은 ORDER 090 live 문구를 다시 실행했다.

관측값:

- Ollama qwen3:14b: 100% GPU, 약 10.6GB VRAM
- RTX 5080 초기 관측: 55°C, 약 207W, utilization 52%
- 고부하 관측: 82~84°C, 약 251~303W, utilization 97~98%
- `nvidia-smi` fan 보고값: 0%. 실제 물리 팬 정지 여부는 확인하지 못했으므로
  이 값만으로 냉각 장치 고장을 확정하지 않는다.
- 안전을 위해 Python live 시험과 Ollama 모델을 중단했다.
- 중단 직후 `nvidia-smi`는 RTX 5080을 `GPU is lost`로 보고했다.
- Windows System log: 2026-07-11 13:48:51, Kernel-Power event 41
- 의미: 시스템이 정상 종료 절차 없이 재부팅됐다.
- 재부팅 후 RTX 5080은 다시 인식됐으며 47°C, 약 15W 대기 상태였다.
- RTX 2080 Ti는 의도적 software disable 상태를 유지했다.

판정:

- 두 번째 live 실행도 최종 trace 생성 전에 시스템이 재부팅됐으므로 `검증 중단`이다.
- RTX 2080 Ti를 배제한 상태에서도 RTX 5080 고부하 중 재현됐으므로 단순한 두 GPU
  동시 연산 충돌만으로 설명할 수 없다.
- 코드 원인, 냉각, 전원 공급 장치/케이블, PCIe 연결, 드라이버/BIOS 중 어느 하나로
  원인을 확정할 근거는 아직 없다.
- 하드웨어 점검 전 추가 GPU live 부하 시험을 금지한다.

## 11. RTX 2080 Ti 물리 제거 후 재시험

사용자가 RTX 2080 Ti를 본체에서 물리적으로 제거한 뒤 RTX 5080 단독 상태를 확인했다.

재시험 전 기준선:

- GPU: NVIDIA GeForce RTX 5080 한 개만 인식
- 대기 온도: 34°C
- 대기 전력: 약 10W
- 최근 WHEA event: 0개
- Ollama loaded model: 없음

동일 ORDER 090 문구를 강제 라우팅 없이 실행한 결과:

- 실행 시간: 약 315초
- Python 종료 코드: 0
- 고부하 온도: 약 55~70°C
- fan 보고값: 약 30~46%
- 소비 전력: 약 270~290W
- 실행 후 WHEA event: 0개
- 시스템 재부팅 및 GPU lost 없음
- node_1 route: `L -> L -> 2`
- L은 문서 6개를 읽었지만 ORDER 090을 선택하지 못했다.

따라서 이 실행은 하드웨어 안정성 확인에는 성공했으나, 자율 node_1 라우팅 시험에는
실패했다. ORDER 252의 R 증거 계약은 이 실행에서 호출되지 않았다.

같은 문구에 `--force-vessel-r-route --enable-vessel-r-route`를 적용해 다시 실행한 결과:

- 실행 시간: 약 204초
- Python 종료 코드: 0
- 실행 후 RTX 5080: 48°C, 약 13W
- 실행 후 WHEA event: 0개
- route: `R -> 2`
- R1 evidence contract: `raw_original / required=1`
- R traversal step count: 6
- 경로: TimeAxis -> SourceIngestTimeBundle -> SourceKindBundle -> TokenBudgetSummary
  -> SourceLeafSummary -> RawSource
- terminal material: 2개
- raw original material: 1개
- R task status: `sufficient`
- node_4 gatekeeper: `pass`

선택된 RawSource 절대 ID는 다음과 같다.

```text
graph:raw_source:internal_document:a825aad2a17dc819
```

DataStore의 source lineage를 대조한 결과 이 ID는 다음 원본에 연결된다.

```text
Administrative_Reform_1/04_Orders/ORDER_090_L_LOOP_BUDGET_PLAN_V0.md
source_file:internal_document:7d6d7bace1cf9012
content_sha1: b7fb2eaa551fae821fa66385a12d738c2da2f4e2
```

최종 판정:

- RTX 2080 Ti 물리 제거 후 두 번의 Qwen 고부하 실행은 모두 정상 종료했다.
- 이번 두 실행만으로 하드웨어 고장의 최종 원인을 확정하지는 않는다.
- 강제 R 실행에서는 ORDER 252의 `raw_original` 계약이 실제 ORDER 090 원문까지 도달했다.
- 남은 기능 문제는 node_1이 같은 질문을 자율적으로 R이 아니라 L로 보낸 점이다.
- 시험 종료 후 qwen3:14b를 내렸고 RTX 5080은 38°C, 약 35W, WHEA 0개였다.
