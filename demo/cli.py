"""Ollama 연결, 사용자 입력과 화면 출력만 담당하는 얇은 CLI."""

import argparse
import sys
from pathlib import Path

from agent_tools import FileToolbox
from llm import ModelCallError, OllamaClient
from llm.structured import NodeOutputError
from memory import DEFAULT_MEMORY_PATH
from memory.settings import PROJECT_ROOT
from runtime import run_demo_turn


DEMO_MAX_PYTHON_FILE_BYTES = 16 * 1024


def _build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "로컬 Ollama의 Qwen3 14B로 송련 Node1~Node4를 한 턴 실행합니다."
        )
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="바로 실행할 사용자 요청. 생략하면 대화형 입력을 받습니다.",
    )
    parser.add_argument(
        "--model",
        default="qwen3:14b",
        help="Ollama 모델 이름 (기본값: qwen3:14b)",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="로컬 Ollama 주소",
    )
    parser.add_argument(
        "--memory",
        type=Path,
        default=DEFAULT_MEMORY_PATH,
        help="원본 JSONL 경로",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Node1이 읽을 수 있는 프로젝트 루트",
    )
    return parser


def _progress(node_name, message):
    print(f"[{node_name}] {message}", flush=True)


def _run_one(question, *, client, toolbox, memory_path):
    result = run_demo_turn(
        question,
        client=client,
        toolbox=toolbox,
        memory_path=memory_path,
        on_event=_progress,
    )
    print("\n송련>\n" + result.answer)
    print(
        "\n"
        f"(도구 {result.total_tool_calls}회, "
        f"Node2 반려 {result.node2_rejections}회, "
        f"Node4 반려 {result.node4_rejections}회)"
    )


def main(argv=None):
    """명령행 인자를 읽고 한 번 또는 대화형으로 데모를 실행한다."""

    args = _build_parser().parse_args(argv)
    client = OllamaClient(
        base_url=args.base_url,
        model_name=args.model,
    )

    try:
        ready = client.check_ready()
        print(
            "Ollama "
            f"{ready['server_version']} / {ready['model_name']} 준비 완료"
        )
        toolbox = FileToolbox(
            allowed_root=args.project_root,
            max_file_bytes=DEMO_MAX_PYTHON_FILE_BYTES,
        )

        if args.question:
            _run_one(
                " ".join(args.question),
                client=client,
                toolbox=toolbox,
                memory_path=args.memory,
            )
            return 0

        print("종료하려면 빈 줄 또는 exit를 입력하세요.")

        while True:
            question = input("\n사용자> ").strip()

            if not question or question.lower() in {"exit", "quit"}:
                return 0

            _run_one(
                question,
                client=client,
                toolbox=toolbox,
                memory_path=args.memory,
            )
    except (ModelCallError, NodeOutputError, OSError, ValueError) as error:
        print(f"\n데모 중단: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n사용자가 데모를 중단했습니다.", file=sys.stderr)
        return 130
