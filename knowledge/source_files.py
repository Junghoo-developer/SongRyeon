"""색인할 파일을 찾고, UTF-8 본문과 SHA-256을 준비한다.

이 파일은 DB에 접근하지 않는다. 파일 시스템에서 읽은 사실만 딕셔너리로
만들어 다음 단계인 ``indexer.py``에 넘긴다.
"""

import hashlib
from pathlib import Path

# 이 파일의 전체 흐름:
# 1. 색인할 파일을 찾는다.
# 2. 파일을 바이트 그대로 읽는다.
# 3. DB에 저장하기 좋은 ``경로 + 본문 + 디지털 지문`` 묶음으로 만든다.
#
# 여기서는 파일을 찾고 읽기만 한다.
# DB 저장과 memory.jsonl 기록은 뒤 단계인 indexer.py가 지휘한다.

from .settings import (
    # 외부 문서로 인정할 확장자 모음. 예: .md, .txt
    DOCUMENT_EXTENSIONS,
    # 검색에서 제외할 폴더 이름 모음. 예: .git, __pycache__, 가상환경
    EXCLUDED_DIRECTORY_NAMES,
)


def prepare_file(file_path, root_directory):
    """허용된 루트 안의 파일을 읽어 상대경로·본문·hash를 반환한다."""

    # Path는 문자열 경로를 다루기 편한 '경로 객체'로 바꾼다.
    # resolve()는 ``..`` 등을 정리해 실제 절대경로로 만든다.
    # 두 경로를 먼저 정규화해야 "허용된 폴더 안인가?"를 정확히 검사할 수 있다.
    root = Path(root_directory).resolve()
    path = Path(file_path).resolve()

    try:
        # 예:
        # root = C:/SongRyeon_Core_v1
        # path = C:/SongRyeon_Core_v1/memory/store.py
        # 결과 = memory/store.py
        #
        # path가 root 밖에 있으면 relative_to()가 ValueError를 낸다.
        # 따라서 상대경로 변환과 보안 검사를 한 번에 수행하는 셈이다.
        relative_path = path.relative_to(root)
    except ValueError as error:
        raise ValueError("허용된 폴더 밖의 파일은 색인할 수 없습니다.") from error

    # 경로는 존재하지만 폴더인 경우도 있으므로 "실제 파일"인지 따로 확인한다.
    if not path.is_file():
        raise FileNotFoundError(path)

    # 문자열로 바로 읽지 않고 원본 바이트를 한 번만 읽는다.
    # 같은 바이트로 본문을 만들고 SHA-256도 계산해야 둘의 기준이 어긋나지 않는다.
    raw_content = path.read_bytes()

    return {
        # 컴퓨터마다 달라지는 C:/Users/... 절대경로 대신
        # 프로젝트 안에서 동일하게 통하는 상대경로를 저장한다.
        # as_posix()는 Windows에서도 구분자를 "/"로 통일한다.
        "path": relative_path.as_posix(),
        # 송련은 색인할 텍스트 파일이 UTF-8이라고 가정한다.
        # UTF-8이 아니면 여기서 오류가 나므로 깨진 글자를 조용히 저장하지 않는다.
        "content": raw_content.decode("utf-8"),
        # SHA-256은 파일 원본 바이트의 64자리 디지털 지문이다.
        # 이전 지문과 같으면 내용이 그대로이고, 다르면 파일이 변경된 것이다.
        "content_hash": hashlib.sha256(raw_content).hexdigest(),
    }


def _contains_excluded_directory(relative_path):
    """캐시·가상환경·Git 내부 파일인지 확인한다."""

    # 파일명은 제외하고, 파일을 감싸는 폴더 이름만 모은다.
    # 예: ".git/objects/example.py" -> {".git", "objects"}
    # lower()를 사용해 대소문자가 달라도 같은 제외 폴더로 취급한다.
    directory_names = {
        part.lower()
        for part in relative_path.parts[:-1]
    }

    # ``&``는 두 집합의 교집합이다.
    # 제외 목록과 겹치는 폴더가 하나라도 있으면 True를 반환한다.
    return bool(directory_names & EXCLUDED_DIRECTORY_NAMES)


def find_python_source_files(
    project_root,
    documents_directory=None,
):
    """프로젝트에서 외부 문서 폴더를 제외한 Python 파일을 찾는다."""

    root = Path(project_root).resolve()

    # 문서 폴더를 따로 받지 않으면 프로젝트의 기본 위치를 사용한다.
    # 위치를 미리 확정해 두어 그 안의 .py 파일을 프로젝트 소스로 오인하지 않게 한다.
    if documents_directory is None:
        documents_root = (root / "knowledge" / "documents").resolve()
    else:
        documents_root = Path(documents_directory).resolve()

    # 조건을 모두 통과한 Python 파일의 절대경로를 여기에 모은다.
    python_files = []

    # rglob("*.py")는 root 아래의 모든 하위 폴더를 재귀적으로 돌며
    # 확장자가 .py인 파일 후보를 찾는다.
    for path in root.rglob("*.py"):
        resolved_path = path.resolve()
        relative_path = resolved_path.relative_to(root)

        # .git, __pycache__, 가상환경 등에 들어 있는 코드는 송련 소스가 아니다.
        if _contains_excluded_directory(relative_path):
            continue

        # 외부 문서 보관 폴더의 .py는 프로젝트 소스와 섞지 않는다.
        # 첫 조건은 documents_root 자체, 두 번째는 그 아래 모든 자손을 뜻한다.
        if (
            resolved_path == documents_root
            or documents_root in resolved_path.parents
        ):
            continue

        python_files.append(resolved_path)

    # 파일 시스템이 돌려주는 순서는 환경마다 달라질 수 있다.
    # 정렬해 두면 색인·테스트 결과가 언제나 같은 순서가 된다.
    return sorted(python_files)


def find_document_files(documents_directory):
    """외부 문서 폴더를 준비하고 허용된 UTF-8 텍스트 파일을 찾는다."""

    root = Path(documents_directory).resolve()

    # 문서 폴더가 아직 없다면 만든다.
    # parents=True는 중간 폴더도 만들고, exist_ok=True는 이미 있어도 오류를 내지 않는다.
    root.mkdir(parents=True, exist_ok=True)

    # 아래 코드는 목록을 만드는 축약 문법이다.
    # root 아래의 모든 항목 중에서:
    # - 실제 파일이고
    # - 확장자가 settings.py의 허용 목록에 있는 것만 남긴다.
    # 마지막으로 절대경로로 바꾸고 정렬한다.
    return sorted(
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in DOCUMENT_EXTENSIONS
    )
