# ORDER 261 Code Range Material Assembly And L3 Recheck 구현 기록

## 1. 구현 일자

- 2026-07-17

## 2. 구현 목적

ORDER 258~260으로 이어 읽은 `read_code_file` 구간이 node_3에 도달한 뒤에도
정상적인 부분 코드가 전체 파일 문법 오류처럼 보이고, revision 뒤 L3 의미 판정이
다시 실행되지 않던 문제를 고쳤다.

## 3. 구현 내용

1. `Node3SourceCodeOutline`에 분석 범위와 정확한 문자 구간을 추가했다.
   - `analysis_scope=complete_file|partial_range`
   - `range_start_char`
   - `range_end_char_exclusive`
   - `total_char_count`
   - `utf8_bom_present`
2. 부분 구간은 AST를 실행하지 않고 `parse_status=not_run_partial_range`로 기록한다.
3. 완전한 Python 파일만 AST를 실행한다. 맨 앞 UTF-8 BOM은 분석용 문자열에서만 제거하며 원본 파일은 바꾸지 않는다.
4. node_3 LLM payload에 `source_code_range_materials`를 추가했다.
   - 코드 원문
   - 안전한 payload 전용 참조명
   - 파일 경로
   - 정확한 `[start, end)` 범위
   - 전체 길이와 잘림 상태
   - 분석 범위와 parse 상태
5. 같은 코드 원문은 호환용 `read_documents`와 `supplied_document_contexts`에서 제외해 한 채널에만 싣는다.
6. task-focused payload는 node_2가 `read_code_file` 또는 `l3_result`를 근거로 골랐을 때 대응 코드 구간만 공급한다.
7. L3 revision은 현재 L run에서 이미 읽은 코드 구간과 새 구간을 함께 입력받아 의미 적합성을 다시 판정한다.
8. revision 달성 승격은 다음 조건이 모두 맞을 때만 code 정책으로 실행한다.
   - L3 LLM 의미 판정이 실제 실행됨
   - `semantic_goal_match_status=matched`
   - 요청 파일/goal-match 구조가 partial 또는 missing이 아님
   - 현재 L lineage에 비어 있지 않은 원문이 있음
   - L1 최소 원문 수량 조건을 충족함
9. grounding block의 원문 수는 보존 frame의 예정 수량이 아니라 실제 node_3 LLM payload 수로 계산한다.
10. node_3/node_4 prompt에 부분 구간 분석 미실행을 문법 오류로 바꾸지 않는 경계를 추가했다.
11. node_2에는 코드 원문 전체를 중복 공급하지 않고 다음 절대 좌표만 공급한다.
    - 파일 경로
    - `[start, end)` 문자 범위
    - 전체/반환 문자 수
    - `truncated_before`, `truncated_after`
    - 원문은 해당 evidence ref 선택 뒤 node_3에만 전달
12. 필수 근거 계약과 실제 answer-ready 선택의 구조적 모순을 검사한다.
    - 모순 시 기존 schema repair를 1회 사용
    - repair 중 `evidence_roles` 외 이미 유효한 과업/모드 필드는 잠금
    - code는 어떤 answer-ready ref가 의미상 맞는지 대신 고르지 않음
13. direct Ollama 호출에 `num_ctx=16384` 기본값을 명시했다.
    - 모델 최대 context와 실제 실행 context가 다르다는 점을 코드 주석으로 남김
    - `SONGRYEON_QWEN_NUM_CTX`로 조정 가능

## 4. 정보 분류 경계

- 파일 경로, 문자 범위, 문자 수, BOM 존재, parse 실행 여부: 절대정보
- 코드 구간이 사용자 목표에 의미상 맞는지에 대한 L3 판정: 혼합정보
- 의미 일치와 CODE 원문 조건을 결합한 revision 종료: 명시적 CODE 정책 결정
- node_3의 코드 설명과 node_4의 주장 검토: LLM 의미 판단

## 5. 변경 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/loops/l_loop.py`
- `songryeon_core/nodes/l3_result_keeper.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_3_reporter.py`
- `songryeon_core/llm/fake.py`
- `songryeon_core/llm/qwen_adapter.py`
- `songryeon_core/nodes/node_2_metainfo_boundary.py`
- `songryeon_core/prompts/l3_result_keeper_v0.md`
- `songryeon_core/prompts/node_2_answer_basis_selector_v0.md`
- `songryeon_core/prompts/node_3_reporter_v0.md`
- `songryeon_core/prompts/node_4_gatekeeper_v0.md`
- `tests/test_order_261_code_range_material_and_l3_recheck.py`
- `Administrative_Reform_1/04_Orders/ORDER_261_CODE_RANGE_MATERIAL_ASSEMBLY_AND_L3_RECHECK_V0.md`

## 6. 새 회귀 테스트

- 부분 Python 구간이 `parse_failed`가 아니라 `not_run_partial_range`인지 확인
- 완전한 BOM 포함 Python 파일이 분석용 복사본에서 정상 parse되는지 확인
- 다중 코드 구간의 원문/경로/범위가 같은 payload 항목으로 결합되는지 확인
- 같은 코드 원문이 legacy 문서 채널에 중복되지 않는지 확인
- 실제 node_3 payload 원문 수와 grounding block 수가 일치하는지 확인
- revision L3가 누적 코드 구간을 다시 보고 `matched`일 때만 달성으로 닫는지 확인
- revision L3가 `partial`이면 달성으로 승격하지 않는지 확인
- node_2 필수 근거 계약이 answer-ready 재료 0개 선택을 거절하고 repair하는지 확인
- repair가 사용자 과업을 바꾸면 schema 실패로 닫는지 확인
- node_2에는 코드 범위 좌표만 한 번 보이고 원문은 노출되지 않는지 확인
- direct Ollama Qwen 호출에 `num_ctx=16384`가 실제 전달되는지 확인

## 7. 자동 검증

```text
python -m compileall songryeon_core main.py
passed

focused pytest
18 passed in 0.26s

python -m pytest
468 passed, 5 deselected in 192.62s

python main.py smoke-test
SMOKE_TEST_OK
```

## 8. 로컬 Qwen 재시험

ORDER 260과 같은 함수 설명 문구를 여러 번 실행해 원인을 단계적으로 분리했다.

1. Windows 제외 포트 범위에 기본 11434가 포함되어 별도 Ollama server를 12200에서 실행했다.
2. node_2에 두 코드 구간 원문 약 24,000자를 직접 공급했을 때 node_2 입력은 33,668자가 됐고,
   사용자 과업이 JSON 오류 설명으로 변질됐다.
3. node_2를 좌표 선택자로 되돌리자 입력은 8,875자로 줄고 두 코드 구간을 정상 선택했다.
4. 그래도 node_3 입력 33,194자의 뒤쪽 목표 함수를 읽지 못했다. `ollama ps`에서 실제
   CONTEXT가 4,096임을 확인했다.
5. direct adapter에 `num_ctx=16384`를 명시한 뒤 같은 입력으로 최종 성공했다.

최종 live 절대정보:

- 실행 상태: `model_fallback`
- fallback 범위: L2의 명시 경로 exact-copy (`code_explicit_path_copy_fallback`)
- node_1 router fallback: 0회
- node_2 answer-basis failure: `none`
- node_2 입력: 두 `read_code_file` 구간을 primary/supporting으로 선택
- node_3 코드 재료: 2개, 범위 `[0,12000)`, `[12000,24000)`
- node_4: `pass`, unsupported 0, contradiction 0
- 실제 Ollama CONTEXT: 16,384
- RTX 5080 VRAM: 약 13,438 / 16,303 MiB 사용, 약 2,540 MiB 여유
- export: `.songryeon_core_cache/order_261_live_final_20260717_003`

최종 node_3 답변은 원문과 대조했을 때 다음을 정확히 포함했다.

- 다섯 매개변수: `zero_state`, `packet_id`, `packet`, `read_window`, `alignment_read_window`
- 반환형: `list[MemoryItem]`
- helper 3개: `build_trace_evidence_memory_item`,
  `build_previous_turn_capsule_index_items`,
  `build_recent_raw_conversation_capsule_alignment_items`

## 9. 의도적으로 하지 않은 것

- 키워드/함수명 휴리스틱으로 code가 관련 구간 선택
- read_code_file 예산 증가
- 부분 구간 AST 강제 실행
- BOM 파일 일괄 재작성
- node_4 guard 약화
- L/R 라우팅, W/R loop, scheduler, 외부 DB 변경

## 10. 남은 위험

1. L3 code preview는 현재 최신 3개 구간으로 제한된다. 더 긴 다구간 의미 비교는 별도 예산/컨텍스트 정책 논의 대상이다.
2. 라이브 시행 중 L3 revision LLM이 사용자 질문과 무관한 코드 내용을 `matched`로 판단한 사례가 있었다.
   최종 node_3는 초기 L3의 `partial` 한계를 보존해 정답을 만들었지만, revision 의미 판정의
   source-claim 정렬은 별도 감사 대상이다.
3. 기본 16,384 context는 현재 5080 16GB에서 작동했으나 VRAM 여유가 약 2.5GB다.
   더 큰 모델, 병렬 호출, context 상향 전에는 메모리 검증이 필요하다.
4. 최종 live 상태의 `model_fallback`은 명시 코드 경로를 그대로 복사한 L2 구조 fallback이다.
   의미 판단 fallback은 아니지만 runtime 명칭이 넓어 사용자에게 혼동을 줄 수 있다.
