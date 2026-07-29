"""프로젝트 안의 Python 소스만 다루는 읽기 전용 도구.

허용 루트는 모델이 정하지 않고 ``FileToolbox``를 만드는 코드가 고정한다.
모델은 목록에서 본 상대경로만 요청할 수 있으며, 절대경로·상위 폴더 탈출·
캐시·외부 문서 폴더·Python 이외 파일은 코드가 거부한다.
"""

import json
from pathlib import Path

from knowledge.settings import EXCLUDED_DIRECTORY_NAMES
from memory.settings import PROJECT_ROOT

from .result import (
    LIST_PYTHON_FILES,
    MAX_FILE_LIST_CHARACTERS,
    MAX_PYTHON_FILE_BYTES,
    MAX_TOOL_ARGUMENT_CHARACTERS,
    MAX_TOOL_NAME_CHARACTERS,
    READ_PYTHON_FILE,
    ToolInputError,
    ToolResult,
)


class FileToolbox:
    """한 프로젝트 루트에 고정된 두 가지 읽기 전용 도구."""

    def __init__(
        self,
        allowed_root=PROJECT_ROOT,
        max_file_bytes=MAX_PYTHON_FILE_BYTES,
        documents_directory=None,
    ):
        root = Path(allowed_root).resolve(strict=True)

        if not root.is_dir():
            raise NotADirectoryError(root)

        if max_file_bytes <= 0:
            raise ValueError("max_file_bytes는 1 이상이어야 합니다.")

        self.allowed_root = root
        self.max_file_bytes = max_file_bytes
        self.documents_directory = (
            (root / "knowledge" / "documents").resolve()
            if documents_directory is None
            else Path(documents_directory).resolve()
        )

    def _relative_path(self, resolved_path):
        """실제 경로가 허용 루트 안에 있는지 확인하고 상대경로로 바꾼다."""

        try:
            return resolved_path.relative_to(self.allowed_root)
        except ValueError as error:
            raise ToolInputError(
                "프로젝트 폴더 밖의 파일은 열람할 수 없습니다."
            ) from error

    def _is_excluded(self, resolved_path):
        """캐시·가상환경·외부 문서 폴더에 속하는지 확인한다."""

        relative_path = self._relative_path(resolved_path)
        directory_names = {
            part.lower()
            for part in relative_path.parts[:-1]
        }

        if directory_names & EXCLUDED_DIRECTORY_NAMES:
            return True

        return (
            resolved_path == self.documents_directory
            or self.documents_directory in resolved_path.parents
        )

    def _resolve_python_file(self, relative_path):
        """사용자 입력 경로를 검증해 안전한 실제 Python 파일로 바꾼다."""

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ToolInputError("path에는 Python 파일 상대경로가 필요합니다.")

        if "\x00" in relative_path:
            raise ToolInputError("허용되지 않는 문자가 path에 포함됐습니다.")

        requested_path = Path(relative_path)

        if (
            requested_path.is_absolute()
            or requested_path.drive
            or requested_path.root
        ):
            raise ToolInputError("절대경로는 열람할 수 없습니다.")

        if ":" in relative_path:
            raise ToolInputError("허용되지 않는 문자가 path에 포함됐습니다.")

        try:
            resolved_path = (
                self.allowed_root / requested_path
            ).resolve(strict=True)
        except (OSError, ValueError) as error:
            raise ToolInputError(
                "요청한 Python 파일 경로를 처리할 수 없습니다."
            ) from error

        self._relative_path(resolved_path)

        if self._is_excluded(resolved_path):
            raise ToolInputError("제외된 폴더의 파일은 열람할 수 없습니다.")

        if not resolved_path.is_file():
            raise ToolInputError("파일만 열람할 수 있습니다.")

        if resolved_path.suffix.lower() != ".py":
            raise ToolInputError("현재는 .py 파일만 열람할 수 있습니다.")

        return resolved_path

    def list_python_files(self):
        """허용된 Python 파일 이름을 정렬된 상대경로 목록으로 반환한다."""

        python_files = []

        for candidate in self.allowed_root.rglob("*.py"):
            try:
                resolved_path = candidate.resolve(strict=True)
                relative_path = self._relative_path(resolved_path)

                if self._is_excluded(resolved_path):
                    continue

                if (
                    not resolved_path.is_file()
                    or resolved_path.suffix.lower() != ".py"
                ):
                    continue
            except (OSError, ToolInputError):
                # 깨진 링크나 루트 밖 링크는 목록에서 조용히 제외한다.
                continue

            python_files.append(relative_path.as_posix())

        return sorted(set(python_files))

    def read_python_file(self, relative_path):
        """Python 파일을 byte 상한 안에서 읽어 원문 문자열 그대로 반환한다."""

        path = self._resolve_python_file(relative_path)

        with path.open("rb") as file:
            raw_content = file.read(self.max_file_bytes + 1)

        if len(raw_content) > self.max_file_bytes:
            raise ToolInputError(
                "파일이 현재 도구의 최대 열람 크기를 초과했습니다."
            )

        try:
            return raw_content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ToolInputError(
                "현재는 UTF-8 Python 파일만 열람할 수 있습니다."
            ) from error

    def execute(self, tool_name, arguments):
        """고정 허용 목록에서 도구 하나를 실행하고 실패도 결과로 반환한다."""

        valid_tool_name = (
            isinstance(tool_name, str)
            and 0 < len(tool_name) <= MAX_TOOL_NAME_CHARACTERS
        )
        recorded_tool_name = (
            tool_name
            if valid_tool_name
            else "<invalid_tool_name>"
        )
        arguments_error = None

        if isinstance(arguments, dict):
            recorded_arguments = dict(arguments)

            try:
                serialized_arguments = json.dumps(
                    recorded_arguments,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                recorded_arguments = json.loads(serialized_arguments)
            except (RecursionError, TypeError, ValueError):
                recorded_arguments = {
                    "invalid_arguments": "not_json_serializable",
                }
                arguments_error = (
                    "도구 arguments는 JSON으로 기록할 수 있어야 합니다."
                )
            else:
                if (
                    len(serialized_arguments)
                    > MAX_TOOL_ARGUMENT_CHARACTERS
                ):
                    recorded_arguments = {
                        "rejected_argument_characters": len(
                            serialized_arguments
                        ),
                    }
                    arguments_error = (
                        "도구 arguments가 최대 길이를 초과했습니다."
                    )
        else:
            recorded_arguments = {
                "invalid_arguments_type": type(arguments).__name__,
            }
            arguments_error = "도구 arguments는 JSON 객체여야 합니다."

        def failure_result(error_message):
            return ToolResult(
                tool_name=recorded_tool_name,
                arguments=recorded_arguments,
                success=False,
                content="",
                error=error_message,
            )

        try:
            if not valid_tool_name:
                raise ToolInputError(
                    "도구 이름은 허용 길이의 문자열이어야 합니다."
                )

            if arguments_error is not None:
                raise ToolInputError(arguments_error)

            if tool_name == LIST_PYTHON_FILES:
                if arguments:
                    raise ToolInputError(
                        "list_python_files는 arguments를 받지 않습니다."
                    )
                content = "\n".join(self.list_python_files())

                if len(content) > MAX_FILE_LIST_CHARACTERS:
                    raise ToolInputError(
                        "Python 파일 목록이 현재 도구 한도를 초과했습니다."
                    )
            elif tool_name == READ_PYTHON_FILE:
                if set(arguments) != {"path"}:
                    raise ToolInputError(
                        "read_python_file에는 path 하나만 필요합니다."
                    )
                content = self.read_python_file(arguments["path"])
            else:
                raise ToolInputError("허용되지 않은 도구입니다.")
        except ToolInputError as error:
            return failure_result(str(error))
        except OSError:
            # 운영체제 오류에는 실제 호스트 절대경로가 포함될 수 있다.
            return failure_result(
                "파일 도구가 요청을 처리하지 못했습니다."
            )

        return ToolResult(
            tool_name=recorded_tool_name,
            arguments=recorded_arguments,
            success=True,
            content=content,
        )
