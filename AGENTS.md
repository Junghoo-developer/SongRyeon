# AGENTS.md - SongRyeon Core 협업자 작업 규칙

이 문서는 `SongRyeon_Project/AGENTS.md`의 본점 지침을 SongRyeon Core 연습판에 맞게 옮긴 운영 규칙이다.
Codex 또는 다른 AI 협업자는 이 저장소를 다룰 때 아래 규칙을 따른다.

## 1. 인코딩 규칙

이 저장소의 `.md`, `.py`, `.json`, `.yml`, `.txt` 파일은 기본적으로 **UTF-8, BOM 없음**으로 다룬다.

Windows PowerShell의 기본 `Get-Content`, `Set-Content`, `cat`, 리다이렉션은 한글 문서를 모지바케로 보이게 하거나 잘못 저장할 수 있다.
한글이 깨져 보인다고 해서 파일이 곧바로 깨진 것은 아니다. 먼저 읽는 쪽 설정을 의심한다.

PowerShell에서 읽을 때:

```powershell
Get-Content path\to\file.md -Encoding UTF8
Get-Content path\to\file.md -Raw -Encoding UTF8
```

PowerShell에서 단순히 아래처럼 읽는 것은 피한다.

```powershell
Get-Content path\to\file.md
cat path\to\file.md
```

문서가 깨져 보이면 재작성하기 전에 먼저 다음을 확인한다.

1. 실제 파일 인코딩이 UTF-8인지 확인한다.
2. PowerShell에서는 `-Encoding UTF8`로 다시 읽는다.
3. 그래도 깨져 있을 때만 문서 복구를 검토한다.

문서 재작성은 최후의 수단이다.

## 2. 역할 분담

| 역할 | 담당 |
| --- | --- |
| 비전 결정, 구조 철학, 최종 결재 | 정후 |
| 비전 토론, 문제 제기, 코드 검수 보조 | 외부 조언자 또는 검토자 |
| 코드 작성, 수정, 테스트, 실행 기록 | Codex |
| 런타임 답변 생성 | 송련 노드/LLM |

Codex는 사용자의 비전 결정을 대신하지 않는다.
불명확한 정책 판단이 나오면 임의로 밀지 말고 문서화하거나 질문한다.

## 3. Core 연습판의 문서 우선순위

작업 기준은 보통 다음 순서로 본다.

1. `AGENTS.md`
2. `Administrative_Reform_1/01_Maintenance_System/`
3. `Administrative_Reform_1/03_Maps/`
4. `Administrative_Reform_1/04_Orders/`
5. `Administrative_Reform_1/05_Execution_Records/`
6. 코드와 테스트 결과

실행 로그, 데모 출력, 사용자의 테스트 캡처는 중요한 증거지만 그 자체가 항상 설계 권한은 아니다.
코드 변경이 필요하면 명시 요청, 발주서, 유지 체계 문서, 또는 실행 기록으로 경계를 남긴다.

## 4. 메타정보 관리 원칙

SongRyeon Core에서는 절대 정보, 상대 정보, 혼합 정보를 구분한다.

- 절대 정보: 코드/도구가 확정할 수 있는 ID, 경로, 존재 여부, 횟수, schema 통과 여부, tool result.
- 상대 정보: 특정 하나의 절대 정보 record/field에 대응하거나 그것을 근거로 생성된, 시스템 안에서 의미 참거짓을 확정할 수 없는 해석, 의미 판단, 목표 달성 평가, 요약.
- 혼합 정보: 해석이나 판단이 여러 절대 정보 묶음에 근거하거나, 특정 하나의 절대 정보로 지정하는 것이 불가능하거나 부적절한 경우의 source-bundle 정보.

코드는 의미 판단을 한 것처럼 위장하지 않는다.
LLM이 판단한 것은 `generated_by`, `info_class`, `semantic_judgement_status`, `source_data_ids`로 드러낸다.

## 5. 안전한 작업 규칙

- 기존 사용자 변경을 되돌리지 않는다.
- 무관한 파일을 정리한다는 이유로 삭제하지 않는다.
- 대량 이동, 삭제, DB 변형, 라우팅/프롬프트/answer_mode 대변경은 먼저 문서화하거나 결재를 받는다.
- 테스트 결과와 실패 원인을 실행 기록에 남긴다.
- `git add .` 같은 무차별 staging은 쓰지 않는다.

## 6. 반복 실수 갱신 규칙

같은 실수를 두 번 반복하면 이 문서나 유지 체계 문서에 규칙을 추가한다.
