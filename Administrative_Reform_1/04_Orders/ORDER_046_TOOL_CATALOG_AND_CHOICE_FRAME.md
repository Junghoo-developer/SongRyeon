# ORDER 046: Tool Catalog And Choice Frame

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "일일이 다 데이터 설명 안 해도"  
**목표**: LLM이 도구 이름과 사용법을 매번 사람에게 듣지 않아도 되도록, 사용 가능한 도구 목록과 선택 이유를 스키마로 제공한다.

## 배경

현재 도구는 `ToolRegistry`에 `list_docs`, `read_doc`, `search_docs`로 등록되어 있다.  
하지만 LLM 노드는 이 registry를 자기 입력으로 구조화해서 받지 않는다. 그래서 LLM에게 매번 도구 설명을 사람이 풀어줘야 하는 문제가 생긴다.

## 범위

1. `ToolCatalogFrame`을 만든다.
2. 각 도구의 이름, 설명, read_only 여부, 입력 필드, 출력 data_type을 payload로 만든다.
3. `ToolChoiceFrame`을 만든다.
4. L2 또는 L루프 controller가 어떤 도구를 왜 선택했는지 기록한다.
5. 허용되지 않은 도구 선택은 schema validation 또는 tool registry 단계에서 막는다.

## 원칙

1. LLM은 도구 실행 권한을 직접 갖지 않는다. 도구 선택 프레임을 만들고 코드가 검증 후 실행한다.
2. MVP에서는 읽기 전용 도구만 허용한다.
3. 도구 설명은 prompt에 하드코딩하지 않고 registry에서 생성한다.

## 완료 기준

1. DataStore에 `tool_catalog:<turn_id>`가 저장된다.
2. L2 또는 L루프 controller가 `ToolChoiceFrame`을 만든다.
3. `ToolChoiceFrame.tool_name`은 registry에 존재해야 한다.
4. `search_docs`, `read_doc`, `list_docs` 중 하나를 선택하는 FakeLLM 테스트가 통과한다.
