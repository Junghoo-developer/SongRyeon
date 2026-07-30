"""모델 연결, 사용자 입력과 화면 출력만 담당하는 얇은 CLI."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from agent_tools import FileToolbox
from llm import (
    ModelCallError,
    OllamaClient,
    OpenAICompatibleIntegrationClient,
)
from llm.client import (
    DEFAULT_BASE_URL,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_MODEL_NAME,
    DEFAULT_NUM_CTX,
    DEFAULT_TIMEOUT_SECONDS,
)
from llm.openai_compatible import DEFAULT_EXTERNAL_API_KEY_ENV
from llm.structured import NodeOutputError
from memory import DEFAULT_MEMORY_PATH
from memory.settings import PROJECT_ROOT
from runtime import run_demo_turn


DEMO_MAX_PYTHON_FILE_BYTES = 16 * 1024


def _build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "로컬 또는 자체 호스팅 Ollama 모델로 송련 Node1~Node4를 "
            "한 턴 실행합니다."
        )
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="바로 실행할 사용자 요청. 생략하면 대화형 입력을 받습니다.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help=f"Ollama 모델 이름 (기본값: {DEFAULT_MODEL_NAME})",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"로컬 또는 자체 호스팅 Ollama 주소 (기본값: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=DEFAULT_NUM_CTX,
        help=f"모델 컨텍스트 크기 (기본값: {DEFAULT_NUM_CTX})",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"각 Ollama HTTP 요청 제한 시간 (기본값: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--keep-alive",
        default=DEFAULT_KEEP_ALIVE,
        help=f"Ollama 모델 유지 시간 (기본값: {DEFAULT_KEEP_ALIVE})",
    )
    parser.add_argument(
        "--memory",
        type=Path,
        default=None,
        help=(
            "원본 JSONL 경로. Ollama 실행은 기본 memory.jsonl을 사용하고, "
            "외부 API 통합시험은 생략 시 폐기되는 임시 로그를 사용합니다."
        ),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Node1이 읽을 수 있는 프로젝트 루트",
    )
    parser.add_argument(
        "--external-api-integration",
        action="store_true",
        help=(
            "대회 기본 경로가 아닌 OpenAI-compatible 외부 API 통합시험을 "
            "단발로 실행합니다."
        ),
    )
    parser.add_argument(
        "--external-api-base-url",
        help="통합시험용 HTTPS API base URL (예: https://host.example/v1)",
    )
    parser.add_argument(
        "--external-api-model",
        help="통합시험 공급자에 요청할 모델 이름",
    )
    parser.add_argument(
        "--external-api-key-env",
        default=DEFAULT_EXTERNAL_API_KEY_ENV,
        help=(
            "API key를 읽을 환경 변수 이름 "
            f"(기본값: {DEFAULT_EXTERNAL_API_KEY_ENV})"
        ),
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
    warning_messages = []
    if result.node2_limit_exhausted:
        warning_messages.append(
            "주의: Node2 반려 한도를 넘어 증거 검증이 완료되지 않은 채 "
            "답변 단계로 진행했습니다."
        )
    if result.node4_limit_exhausted:
        warning_messages.append(
            "주의: Node4 반려 한도를 넘어 최종 답변은 검열 permit을 "
            "받지 못한 상태로 전달됐습니다."
        )

    if warning_messages:
        print("\n[검증 미완료]")
        for message in warning_messages:
            print(message)
        answer_label = "송련 (검증 미완료)>"
    else:
        answer_label = "송련>"

    print(f"\n{answer_label}\n" + result.answer)
    print(
        "\n"
        f"(도구 {result.total_tool_calls}회, "
        f"Node2 반려 {result.node2_rejections}회, "
        f"Node4 반려 {result.node4_rejections}회)"
    )


def _external_memory_path(memory_path):
    """대회용 실제 원본 memory.jsonl을 외부 API 실행에서 차단한다."""

    resolved = Path(memory_path).resolve()
    default_resolved = DEFAULT_MEMORY_PATH.resolve()
    same_file = False
    if resolved.exists() and default_resolved.exists():
        try:
            same_file = os.path.samefile(resolved, default_resolved)
        except OSError:
            same_file = False
    if resolved == default_resolved or same_file:
        raise ValueError(
            "외부 API 통합시험은 실제 memory/memory.jsonl을 사용할 수 없습니다."
        )
    return resolved


def _run_external_integration(args):
    if not args.question:
        raise ValueError("외부 API 통합시험에는 단발 질문이 반드시 필요합니다.")
    if not args.external_api_base_url:
        raise ValueError(
            "외부 API 통합시험에는 --external-api-base-url이 필요합니다."
        )
    if not args.external_api_model:
        raise ValueError(
            "외부 API 통합시험에는 --external-api-model이 필요합니다."
        )
    external_memory = (
        None
        if args.memory is None
        else _external_memory_path(args.memory)
    )

    client = OpenAICompatibleIntegrationClient(
        base_url=args.external_api_base_url,
        model_name=args.external_api_model,
        api_key_env=args.external_api_key_env,
        timeout_seconds=args.timeout_seconds,
    )
    client.check_configuration()
    toolbox = FileToolbox(
        allowed_root=args.project_root,
        max_file_bytes=DEMO_MAX_PYTHON_FILE_BYTES,
    )
    question = " ".join(args.question)
    print(
        "backend=OpenAI-compatible external API / "
        f"model={client.model_name} / mode={client.execution_mode}"
    )

    if external_memory is not None:
        _run_one(
            question,
            client=client,
            toolbox=toolbox,
            memory_path=external_memory,
        )
        return 0

    print("감사 로그는 격리된 임시 경로를 사용하며 실행 후 삭제됩니다.")
    with tempfile.TemporaryDirectory(
        prefix="songryeon-external-api-",
    ) as temporary_directory:
        _run_one(
            question,
            client=client,
            toolbox=toolbox,
            memory_path=Path(temporary_directory) / "memory.jsonl",
        )
    return 0


def main(argv=None):
    """명령행 인자를 읽고 한 번 또는 대화형으로 데모를 실행한다."""

    args = _build_parser().parse_args(argv)
    try:
        if args.external_api_integration:
            return _run_external_integration(args)
        if (
            args.external_api_base_url is not None
            or args.external_api_model is not None
        ):
            raise ValueError(
                "외부 API 옵션은 --external-api-integration과 함께 사용해야 합니다."
            )

        client = OllamaClient(
            base_url=args.base_url,
            model_name=args.model,
            num_ctx=args.num_ctx,
            timeout_seconds=args.timeout_seconds,
            keep_alive=args.keep_alive,
        )
        ready = client.check_ready()
        print(
            f"backend=Ollama {ready['server_version']} / "
            f"model={ready['model_name']} / "
            f"digest={ready['model_digest'][:12]} / "
            f"num_ctx={client.num_ctx} 준비 완료"
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
                memory_path=args.memory or DEFAULT_MEMORY_PATH,
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
                memory_path=args.memory or DEFAULT_MEMORY_PATH,
            )
    except (ModelCallError, NodeOutputError, OSError, ValueError) as error:
        print(f"\n데모 중단: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n사용자가 데모를 중단했습니다.", file=sys.stderr)
        return 130
