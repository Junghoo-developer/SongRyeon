"""기억 기능이 함께 사용하는 경로와 시야 정책 상수.

경로를 각 구현 파일에서 따로 계산하면 파일을 옮길 때 데이터 위치도
의도치 않게 바뀐다. 그래서 실제 데이터 위치는 이 파일 한 곳에서 정한다.
"""

from pathlib import Path


# 기본 데이터와 도구 경계는 설치된 패키지 폴더가 아니라 사용자가 명령을
# 실행한 프로젝트 폴더를 따른다. 소스 저장소 루트에서 실행할 때의 기존
# ``memory/memory.jsonl`` 위치는 그대로 유지된다.
PROJECT_ROOT = Path.cwd().resolve()
MEMORY_DIRECTORY = PROJECT_ROOT / "memory"
DEFAULT_MEMORY_PATH = MEMORY_DIRECTORY / "memory.jsonl"

# 사용 중인 모델의 전체 문맥 크기와 실제 기억 예산은 같은 값이 아니다.
QWEN3_14B_CONTEXT_TOKENS = 40_960

# 데모는 턴 시작 시 최신 약 8,000자에서 고정 시야 기준점을 만든다.
DEFAULT_AGENT_VIEW_CHARACTER_LIMIT = 8_000

# 검색용 지식, 도구 원문과 모델 입출력 원문은 원본에 보존하되 숨긴다.
KNOWLEDGE_INFORMATION_TYPE_PREFIX = "knowledge_"
TOOL_RAW_INFORMATION_TYPE_PREFIX = "tool_raw_"
MODEL_RAW_INFORMATION_TYPE_PREFIX = "model_raw_"
HIDDEN_INFORMATION_TYPE_PREFIXES = (
    KNOWLEDGE_INFORMATION_TYPE_PREFIX,
    TOOL_RAW_INFORMATION_TYPE_PREFIX,
    MODEL_RAW_INFORMATION_TYPE_PREFIX,
)

AGENT_VISIBLE_FIELDS = (
    "information",
    "information_type",
    "information_class",
    "code_verifiable",
)

# ``memory_index``는 원본에 저장하지 않고 JSONL을 읽을 때만 붙이는 순번이다.
AGENT_VIEW_FIELDS = (
    "memory_index",
    *AGENT_VISIBLE_FIELDS,
)
