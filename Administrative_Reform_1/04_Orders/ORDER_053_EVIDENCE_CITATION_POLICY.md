# ORDER 053: Evidence Citation Policy

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 혼합 정보 보고의 근거 추적 필요  
**목표**: 3 보고관의 주요 문장마다 근거 data/trace ID를 연결하는 인용 정책을 만든다.

## 배경

에이전트 보고가 자연어가 될수록 환각 위험이 커진다.  
보고 문장에 근거 ID를 붙이면 사용자는 문장의 출처를 따라갈 수 있고, 2는 출처 없는 단정을 막을 수 있다.

## 범위

1. `ReportEvidenceLink` 또는 동등한 구조를 만든다.
2. 각 보고 문장은 `statement_id`, `text`, `evidence_data_ids`, `evidence_trace_ids`를 가진다.
3. 근거 없는 문장은 `limits`나 `uncertainty`로 분류한다.
4. replay에서 보고 문장과 근거를 역추적할 수 있게 한다.
5. CLI 출력은 너무 장황하지 않게 근거를 접거나 요약할 수 있게 한다.

## 원칙

1. 근거 ID는 장식이 아니라 검증 가능한 링크다.
2. 모든 문장에 긴 근거를 붙이지 않아도 되지만, 핵심 주장에는 반드시 붙인다.
3. 사용자가 원하면 근거 ID를 펼쳐볼 수 있어야 한다.

## 완료 기준

1. ReportFrame에 evidence link 목록이 저장된다.
2. L3 achievement 요약 문장에는 `L3:achievement_frame` 근거가 붙는다.
3. tool choice 요약 문장에는 `tool_choice:*` 근거가 붙는다.
4. smoke test가 최소 1개 evidence link를 확인한다.
