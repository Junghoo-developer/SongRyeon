# ORDER 177: R1 Candidate Text Blindness v0

## 1. Goal

R1이 후보 summary 본문이나 개별 후보 내용에 끌려 사용자 질문 밖으로 목표가 새는 문제를 막는다.

R1은 L1처럼 목표 설정자여야 한다.
따라서 R1은 사용자 질문과 Vessel packet의 절대 통계/count/kind/depth만 보고 graph search goal을 세우고, 개별 후보 본문은 R2/R3 단계에서만 보게 한다.

## 2. Required Behavior

- R1 input에서 다음을 제거한다.
  - `summary_text`
  - `summary_text_preview`
  - `summary_candidate_samples`
  - `entry_candidate_samples`
  - 개별 후보 node id 목록
- R1 input에는 다음만 남긴다.
  - user question
  - read packet id
  - entry candidate count
  - summary candidate count
  - summary count by data kind
  - summary count by depth
  - one-step policy/budget
  - R1은 후보 본문을 보지 않는다는 policy note
- R2 input은 기존처럼 후보 목록과 summary text를 볼 수 있다.
- R3 input은 R2가 선택한 후보 하나의 record만 볼 수 있다.
- R1 output validator는 user question의 핵심 anchor가 사라지는 것을 막기 위한 최소 구조 검사를 추가한다.
  - 휴리스틱 의미 판단이 아니라, R1 goal이 user question의 의미 있는 토큰 중 하나도 포함하지 않으면 schema failure로 닫는다.

## 3. Non-goals

- R route를 기본 live route로 열지 않는다.
- R2/R3 선택 품질을 이번에 크게 바꾸지 않는다.
- multi-step Vessel traversal을 열지 않는다.
- Neo4j write를 수행하지 않는다.
- summary 생성/수정/무효화를 하지 않는다.

## 4. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py -q
python main.py fast-test --profile graph
git diff --check
```

수동 확인:

```powershell
python main.py vessel-r-one-step "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 한 단계만 골라봐" --database neo4j --llm-mode qwen --timeout 120 --format text
```
