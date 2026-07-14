# ORDER 260: L2 Explicit Code Path Contract v0

## 1. 배경

ORDER 258과 ORDER 259는 `read_code_file`의 문자 구간 장부와 다음 구간 이어 읽기 경로를 만들었다.
그러나 2026-07-14 로컬 Qwen 라이브 시험에서 L2가 정확한 파일 경로 대신 다음 설명문을
`query_text`로 생성했다.

```text
songryeon_core/nodes/node_0_memory_supplier.py 파일의 처음부터 12,000자까지 읽기
```

기존 코드는 이 문자열이 실제 workspace 파일 경로인지 확인하지 않고 `file_path`로 넘겼다.
도구는 `not_found`와 빈 구간 `[0, 0)`을 반환했고, 따라서 ORDER 259의 연속 읽기 후보도
생성되지 않았다.

## 2. 목표

사람이 쓰는 읽기 목적 문장과 코드 도구가 받는 정확한 파일 경로를 분리한다.
사용자 입력에 문자 그대로 등장하며 workspace에 실제 존재하는 코드/설정 파일 경로만
`read_code_file` 후보로 허용한다.

## 3. 구현 범위

1. code가 사용자 입력과 workspace 파일 목록을 대조해 `available_explicit_code_file_paths`를 만든다.
2. 이 목록은 의미 추론이 아니라 실제 파일 존재와 문자열 일치만 사용한다.
3. L2 prompt와 validator는 `read_code_file.query_text`가 허용 목록의 정확한 원소인지 검사한다.
4. LLM 계획이 이 계약을 어겼고 허용 경로가 정확히 하나라면 code는 그 경로를 그대로 복사한다.
5. 이 fallback은 `query_source=code_explicit_path_copy_fallback`으로 표시한다.
6. 허용 경로가 없거나 여러 개인 경우 code는 어느 파일이 중요한지 의미 판단하지 않는다.
7. ORDER 259의 revision continuation은 성공한 이전 구간에서 code가 만든 정확한 경로/시작점만 사용한다.

## 4. 정보 분류

- workspace 파일 존재, 사용자 입력 안의 정확한 경로 문자열, 허용 경로 목록: 절대정보
- L2의 읽기 목적과 기대 신호: 혼합정보
- 단일 허용 경로 복사 fallback: 코드가 새 의미를 만든 것이 아닌 절대정보 복사 정책

## 5. 금지

- 파일명을 추측하는 키워드 휴리스틱
- 유사 경로 자동 교정
- 여러 경로 중 code가 중요 파일을 선택하는 동작
- 읽기 예산 증가
- L3 달성 판단 강제
- L/R 라우팅 변경

## 6. 완료 조건

1. 설명문 전체를 `read_code_file` 경로로 낸 L2 계획이 스키마 검증에서 거절된다.
2. 사용자 입력에 정확한 실제 경로가 하나 있으면 code 복사 fallback이 그 경로만 사용한다.
3. 정확한 경로를 낸 L2 계획은 기존처럼 통과한다.
4. 첫 성공 구간이 `truncated_after=true`이면 ORDER 259 continuation option이 유지된다.
5. `python -m compileall songryeon_core main.py` 통과.
6. 집중 pytest와 전체 pytest 통과.
7. `python main.py smoke-test` 통과.
8. 로컬 Qwen 라이브 시험에서 실제 두 번째 구간 읽기 여부를 다시 확인한다.

