# ORDER 067: Code Semantic Text Lockdown

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 메타정보 관리법의 `Code No-Paraphrase Rule`  
**목표**: 코드가 자연어 의미문을 새로 쓰는 지점을 제거하거나 운영 라벨로 격하한다.

## 배경

현재 코드에는 `route_reason`, `macro_goal_reason`, `micro_goal_reason`, `reason`, `expected_use`, `compression_summary` 같은 자연어 필드가 있다.

일부는 `CODE:RULE_STUB`로 표시되어 정직하지만, 사용자는 여전히 이것을 의미 판단처럼 읽을 수 있다.  
따라서 코드가 쓰는 문장은 의미문이 아니라 상태 라벨, 계산 결과, 복사문, 출처 정보로 제한해야 한다.

## 범위

1. 코드가 직접 생성하는 자연어 이유문을 찾는다.
2. 코드가 유지해도 되는 값을 다음처럼 바꾼다.
   - `route_reason` -> `route_rule_id`, `matched_keywords`, `policy_flag`
   - `compression_summary` -> `evidence_trace_count`, `memory_packet_mode`
   - `reason` -> `operation_status_code`, `stop_reason`, `condition_flags`
   - `expected_use` -> `tool_use_policy_id`
3. 꼭 사람에게 보여야 하는 설명은 런타임 렌더러에서 "코드가 붙인 상태 설명"으로만 출력한다.
4. 코드가 문서나 LLM 문장을 복사할 때는 `copied_from`, `selection_method`, `truncated`를 기록한다.
5. `dry_run.py`에서 L루프 뒤 `user_input="보고"`로 라우팅하는 부분은 사용자 입력이 아니라 정책 라우팅으로 분리한다.

## 원칙

1. 코드가 쓴 자연어가 상대정보처럼 보이면 실패다.
2. 코드가 쓸 수 있는 것은 라벨, 수치, ID, enum, bool, copied text뿐이다.
3. 스텁은 스텁이라고 표시하되, 스텁 이유문을 의미 판단처럼 보여주지 않는다.
4. 기존 기능은 유지하되 런타임 정직성을 우선한다.

## 완료 기준

1. 코드 생성 자연어 이유문이 감사 표 기준으로 모두 제거, 격하, 또는 명시 라벨링된다.
2. `python main.py smoke-test`가 통과한다.
3. `qwen-chat --pretty` 출력에서 코드 생성 의미문과 LLM 생성 의미문이 눈으로 구분된다.
4. L루프 뒤 최종 보고 라우팅이 사용자 입력 위장 없이 정책 플래그로 기록된다.

