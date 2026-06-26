# TMP ORDER 027: LLM JSON Schema Validation

## 목표

LLM 응답이 스키마를 통과했는지 확인하는 공통 검증 레이어를 만든다.

## 배경

LLM을 붙이면 출력이 흔들릴 수 있다.  
스키마 검증이 없으면 0/1/2/3의 메타정보 무결성이 깨진다.

## 범위

1. `LLMStructuredOutput` 기본 그릇을 만든다.
2. JSON 파싱 실패, 필드 누락, 타입 오류를 구분한다.
3. 실패 시 `FailureSignal`을 만들 수 있게 한다.
4. 기존 dataclass validator를 재사용한다.

## 완료 기준

- 잘못된 JSON 입력이 실패로 기록된다.
- 올바른 JSON 입력이 dataclass payload로 변환된다.

## 제외

- 모델 재시도 전략.
- 복잡한 Pydantic 의존성.
