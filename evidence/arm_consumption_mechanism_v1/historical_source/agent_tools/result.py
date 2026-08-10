"""파일 도구들이 공통으로 반환하는 결과 형식과 이름."""

from dataclasses import dataclass


LIST_PYTHON_FILES = "list_python_files"
READ_PYTHON_FILE = "read_python_file"
MAX_PYTHON_FILE_BYTES = 64 * 1024
MAX_FILE_LIST_CHARACTERS = 16_000
MAX_TOOL_ARGUMENT_CHARACTERS = 1_024
MAX_TOOL_NAME_CHARACTERS = 64


class ToolInputError(ValueError):
    """모델이 요청한 도구 이름이나 인자가 허용 범위를 벗어났다."""


@dataclass(frozen=True)
class ToolResult:
    """도구 실행 후 Node1과 원본 로그에 전달할 결과."""

    tool_name: str
    arguments: dict
    success: bool
    content: str
    error: str | None = None

    def __post_init__(self):
        if not isinstance(self.tool_name, str) or not self.tool_name:
            raise ValueError("tool_name은 비어 있지 않은 문자열이어야 합니다.")

        if not isinstance(self.arguments, dict):
            raise ValueError("arguments는 dict여야 합니다.")

        if not isinstance(self.success, bool):
            raise ValueError("success는 bool이어야 합니다.")

        if not isinstance(self.content, str):
            raise ValueError("content는 문자열이어야 합니다.")

        if self.success and self.error is not None:
            raise ValueError("성공한 도구 결과에는 error가 없어야 합니다.")

        if not self.success and (
            not isinstance(self.error, str)
            or not self.error
        ):
            raise ValueError("실패한 도구 결과에는 error가 필요합니다.")

    @property
    def observation_text(self):
        """Node1이 이번 호출에서 직접 검토할 원문을 반환한다."""

        if self.success:
            return self.content
        return self.error or "도구 실행에 실패했습니다."
