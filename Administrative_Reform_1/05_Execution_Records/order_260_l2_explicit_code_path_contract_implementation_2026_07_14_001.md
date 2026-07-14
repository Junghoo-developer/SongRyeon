# ORDER 260 L2 Explicit Code Path Contract 구현 기록

## 1. 구현 일자

- 2026-07-14

## 2. 구현 요약

- 사용자 입력에 문자 그대로 등장하며 workspace에 실제 존재하는 코드/설정 경로 목록을 code가 생성한다.
- L2는 `read_code_file.query_text`에 이 목록의 정확한 원소만 사용할 수 있다.
- 설명문이 붙은 경로는 schema validation에서 거절한다.
- 허용 경로가 정확히 하나이고 L tool scope가 `read_code_file`을 열었으면 code가 그 경로만 복사한다.
- 복사 fallback은 `query_source=code_explicit_path_copy_fallback`으로 기록한다.
- 의미 기반 경로 추측, 유사 경로 교정, 여러 경로 중 code 선택은 구현하지 않았다.

## 3. 변경 파일

- `songryeon_core/tools/code_tools.py`
- `songryeon_core/nodes/l2_query_setter.py`
- `songryeon_core/loops/l_loop.py`
- `songryeon_core/core/schemas.py`
- `songryeon_core/prompts/l2_query_setter_v0.md`
- `tests/test_order_260_l2_explicit_code_path_contract.py`
- 관련 기존 테스트의 명시 경로 입력 정렬

## 4. 자동 검증

```text
python -m compileall songryeon_core main.py
passed

focused pytest
25 passed in 7.31s

python -m pytest -q
459 passed, 5 deselected in 126.70s

python main.py smoke-test
SMOKE_TEST_OK
```

## 5. 로컬 Qwen 라이브 재시험

모델은 외부 API 없이 `qwen3:14b via Ollama`만 사용했다.

입력:

```text
songryeon_core/nodes/node_0_memory_supplier.py 파일을 처음부터 read_code_file로 읽고,
첫 구간 뒤에 있는 build_pre_route_memory_items 함수의 매개변수, 반환 구조,
호출하는 helper를 원문 근거로 설명해줘. 첫 12,000자만 읽고 추측하지 말고
같은 파일의 다음 구간을 이어 읽어 확인해.
```

확인된 절대정보:

- 최초 L2 LLM 경로 계획은 계약을 통과하지 못했다.
- code가 단일 명시 경로 `songryeon_core/nodes/node_0_memory_supplier.py`를 복사했다.
- `query_source=code_explicit_path_copy_fallback`이 표시됐다.
- `read_code_file=5/10`이 실행됐다.
- revision start는 `12000`, `24000`, `36000`, `48000` 순서로 기록됐다.
- 실제 읽은 범위는 최소 `[0, 12000)`부터 `[48000, 60000)`까지 이어졌다.
- `l_internal_revision=present`가 기록됐다.
- node_3에는 source-code context 5개가 공급됐다.
- node_4 gate는 pass였다.

판정:

- ORDER 260 정확 경로 계약: 통과.
- ORDER 259 실제 연속 구간 읽기: 통과.
- 사용자 과업의 최종 답변 품질: 불합격.

## 6. 새로 확인된 남은 위험

node_3는 다섯 코드 구간을 공급받았지만 목표 함수의 매개변수, 반환 구조, helper를 설명하지 않았다.
대신 근거에 없는 `파싱 오류`, `들여쓰기 문제` 가능성을 말했다. node_4는 이 답변을 pass했다.

따라서 다음 감사 대상은 경로/이어 읽기가 아니라 다음 두 경계다.

1. 여러 `read_code_file` 구간이 node_3에서 같은 파일의 순서 있는 원문으로 조립되는가.
2. node_4가 코드 원문에 없는 오류 진단을 unsupported claim으로 잡는가.

이번 ORDER에서는 이 downstream 문제를 덧칠하지 않았다.

