# TMP ORDER 020: Node 2 Metainfo Boundary v0.2

## 목표

2 메타정보 경계관이 trace output_ref뿐 아니라 DataStore payload 구조를 읽어 절대정보 경계를 더 정밀하게 만든다.

## 배경

현재 2는 trace와 output_ref를 DataRef로 나열한다.  
DataStore payload 안의 schema_name, schema_version, source_data_ids 같은 절대정보는 아직 세분화하지 않는다.

## 범위

1. `MetainfoBoundary`를 v0.2로 확장한다.
2. DataStore record의 schema metadata를 DataRef로 분리한다.
3. `absolute_info`, `relative_info`, `mixed_info` 필드의 빈 그릇을 만든다.
4. 이번 단계에서는 relative/mixed 내용은 생성하지 않는다.

## 완료 기준

- DataStore record metadata가 boundary에 포함된다.
- relative/mixed 필드는 비어 있어도 구조상 존재한다.
- 3번 보고관은 여전히 절대정보만 보고한다.

## 제외

- 상대정보 판단.
- 혼합정보 생성.
