# ORDER 015: L3 Preserved Frame Schema

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: ORDER 014 이후 다음 수 결정  
**목표**: L3가 DataStore에 저장하는 보존 프레임을 명시적 스키마로 만들고, 검색 결과 후보를 절대정보 중심으로 보존한다.

## 배경

ORDER 014에서 L3는 `search_docs` 도구 결과 payload를 읽고 `L3:preserved_info_frame`을 DataStore에 저장하게 됐다.  
하지만 이 payload는 아직 자유로운 dict에 가까워서, 2번 메타정보 경계관이나 나중의 LLM 노드가 안정적으로 읽기 어렵다.

## 범위

1. `schemas.py`에 L3 보존 프레임 dataclass를 추가한다.
2. 검색 결과 후보 하나를 나타내는 dataclass를 추가한다.
3. L3 보존 프레임 검증 함수를 추가한다.
4. L3는 dict를 직접 만들지 않고 스키마 객체를 만든 뒤 검증한다.
5. DataStore에는 검증을 통과한 스키마 payload만 저장한다.

## 메타정보 분리

### 절대 정보

- `frame_id`
- `turn_id`
- `schema_name`
- `schema_version`
- `source_trace_ids`
- `source_data_ids`
- `candidate_id`
- `result_id`
- `doc_id`
- `chunk_id`
- `score`
- `embedding_model_id`
- `text_preview`
- `source_data_id`
- `source_trace_id`

위 정보는 "문서 내용이 세계적으로 참이다"라는 뜻이 아니다.  
시스템이 해당 도구 결과 payload 안에서 확인한 값이라는 뜻이다.

### 상대 정보

이번 단계에서는 생성하지 않는다.

### 혼합 정보

이번 단계에서는 생성하지 않는다.  
`judgement_status`는 판단 결과가 아니라 "아직 판단하지 않았다"는 처리 상태로 둔다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. `L3:preserved_info_frame` payload에 `schema_name=L3PreservedInfoFrame`이 들어간다.
3. 보존 후보 목록 `candidates`가 생긴다.
4. L3는 검색 결과의 의미 판단을 하지 않는다.
5. Qwen, LangGraph, DB는 아직 사용하지 않는다.
