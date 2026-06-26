from __future__ import annotations

"""Runtime 기본값 모음.

여러 진입점이 같은 숫자를 공유하므로 이 파일에 모아둔다.
새 MVP에서 기본 budget을 바꿀 때는 CLI, fake-turn, qwen-turn, dry-run을
따로 뒤지지 말고 여기부터 확인한다.
"""


DEFAULT_TURN_ID = "turn_dry_001"
DEFAULT_MAX_TOOL_CALLS = 5
DEFAULT_SEARCH_TOP_K = 3
DEFAULT_MAX_QUERY_ATTEMPTS = 3
# Backward-compatible alias. Older code/CLI used "query candidates" to mean
# query attempts, not search result candidates.
DEFAULT_MAX_QUERY_CANDIDATES = DEFAULT_MAX_QUERY_ATTEMPTS
DEFAULT_MAX_READ_DOC_CALLS = 1
DEFAULT_MAX_INPUT_CHARS = 6000
DEFAULT_DOCUMENT_ROOT = "Administrative_Reform_1"
