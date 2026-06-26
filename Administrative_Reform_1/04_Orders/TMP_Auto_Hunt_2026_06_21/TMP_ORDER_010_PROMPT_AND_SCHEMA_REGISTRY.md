# TMP ORDER 010: Prompt And Schema Registry

**상태**: 임시 발주서  
**목표**: 노드에 주입되는 프롬프트와 강제되는 스키마를 관리하는 레지스트리 구조를 정의한다.  
**실행 권한**: 없음.

## 배경

노드는 LLM 호출 단위로 볼 수 있다. 각 노드는 역할에 맞는 프롬프트와 출력 스키마를 가져야 한다.

## 만들 것

```text
PromptRegistry
- node_id
- prompt_name
- version
- purpose
- system_prompt_ref
- conditional_prompt_rules
```

```text
SchemaRegistry
- schema_name
- version
- target_node
- required
- fields
- validation_policy
```

## 0 조건부 프롬프트

0은 1의 라우팅 결과에 따라 맞춤형 조건부 프롬프트를 받아야 한다.

필요 입력:

- 1의 라우팅 대상.
- 1의 라우팅 이유.
- 대상 노드/루프 profile.
- 현재 trace.
- 0.state.

## 완료 기준

- 노드 프롬프트와 노드 스키마가 분리되어 있다.
- 0의 조건부 프롬프트 규칙이 들어 있다.
- 스키마 강제 여부를 기록하는 칸이 있다.

## 제외

- 실제 프롬프트 전문 작성.
- JSON Schema 구현.
