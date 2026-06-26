# ORDER 055: Report Style Modes

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 보고를 학습용/디버그용/간단 보고로 나눌 필요  
**목표**: 3 보고관이 상황에 따라 다른 보고 스타일을 선택할 수 있게 한다.

## 배경

사용자가 매번 같은 밀도의 보고를 원하는 것은 아니다.  
코딩 학습 중에는 자세한 설명이 필요하고, 반복 실행 중에는 짧은 결과만 필요하며, 디버그 중에는 trace/data ID가 많이 필요하다.

## 범위

1. `ReportStyleMode` 후보를 정의한다.
2. MVP 후보는 `brief`, `learning`, `debug`, `audit`로 둔다.
3. CLI나 runtime 옵션으로 style mode를 지정할 수 있게 한다.
4. style mode는 보고 표현만 바꾸고, boundary 안전 규칙은 바꾸지 않는다.
5. LLM reporter가 들어와도 style mode는 스키마로 전달한다.

## 원칙

1. 스타일은 안전 경계를 우회하지 못한다.
2. debug mode는 내부 ID를 많이 보여도 되지만, 허가되지 않은 payload 본문은 말하지 않는다.
3. learning mode는 사용자가 이해할 수 있게 단계별 설명을 포함한다.

## 완료 기준

1. 보고 생성 시 style mode를 받을 수 있다.
2. 최소 2개 이상의 style mode가 smoke/probe로 검증된다.
3. style mode가 ReportFrame payload에 기록된다.
4. 기존 기본 보고는 깨지지 않는다.
