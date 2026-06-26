# TMP ORDER 025: Prompt Files Scaffold

## 목표

나중에 LLM 노드에 주입할 프롬프트 파일 구조를 만든다.

## 배경

현재 PromptRegistry는 prompt ref 문자열만 가진다.  
실제 프롬프트 파일은 아직 없다.

## 범위

1. `songryeon_core/prompts/` 폴더를 만든다.
2. `node_0`, `node_1`, `node_2`, `node_3`, `l1`, `l2`, `l3` 프롬프트 초안을 만든다.
3. 각 프롬프트는 역할, 입력, 출력 스키마, 금지사항을 포함한다.
4. PromptRegistry의 ref와 실제 파일명을 맞춘다.

## 완료 기준

- 모든 registry prompt ref가 실제 파일을 가리킨다.
- 프롬프트는 아직 실행하지 않는다.

## 제외

- 프롬프트 최적화.
- 모델별 튜닝.
