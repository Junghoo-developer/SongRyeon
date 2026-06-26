# ORDER 072: Node2 LLM Metainfo Boundary v2

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: Node2가 혼합정보를 다루지만 아직 의미 분류를 코드 중심으로 처리하는 문제  
**목표**: Node2가 절대정보 목록을 코드에서 받고, 상대/혼합 정보의 분류와 출처 연결을 LLM으로 수행하게 한다.

## 배경

Node2의 핵심 임무는 메타정보 경계다.  
코드는 절대정보 목록을 안정적으로 만들 수 있지만, 어떤 자연어 claim이 상대정보인지 혼합정보인지, source bundle로 묶어야 하는지는 의미 판단을 필요로 한다.

## 범위

1. 코드가 `AbsoluteInfoFrame` 또는 동등한 절대정보 목록을 만든다.
2. Node2 LLM은 후보 자연어 claim들을 분류한다.
3. Node2 LLM 출력에는 다음을 둔다.
   - `relative_info`
   - `mixed_info`
   - `excluded_claims`
   - `source_mode`
   - `claim_alignment`
   - `source_data_ids`
   - `rejection_reason`
4. 코드가 만든 자연어 필드는 기본적으로 혼합정보 승격 대상에서 제외한다.
5. LLM, 사용자, 문서에서 온 자연어만 혼합정보 후보로 우선 허용한다.
6. exact field 대응이 부적절하면 `source_bundle`과 `not_line_mapped`를 사용한다.

## 원칙

1. Node2는 절대정보를 생성하는 노드가 아니라 경계를 관리하는 노드다.
2. source link는 진실 보장이 아니다.
3. 출처 없는 claim은 제외한다.
4. 코드 생성 자연어는 특별히 허용된 경우가 아니면 보고 후보가 아니다.
5. Node2 출력은 Node4가 검사할 수 있어야 한다.

## 완료 기준

1. Node2 LLM call이 기록된다.
2. MetainfoBoundary 안에 absolute, relative, mixed, excluded가 구분된다.
3. `source_bundle`과 `claim_alignment: not_line_mapped`가 동작한다.
4. 코드 생성 자연어가 무심코 혼합정보로 승격되지 않는다.
5. smoke test가 출처 없는 claim 배제와 source bundle 허용을 검증한다.

