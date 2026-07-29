import json

from .indexer import sync_knowledge


def main():
    """소스와 문서를 동기화하고 사람이 읽기 좋은 JSON 보고서를 출력한다."""

    report = sync_knowledge()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
