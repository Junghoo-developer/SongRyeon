from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.fast_test import run_fast_tests
from songryeon_core.runtime.graph_vessel_first_write import run_local_vessel_first_write
from songryeon_core.runtime.graph_vessel_inspect import (
    render_vessel_inspect_text,
    run_local_vessel_inspect,
)
from songryeon_core.runtime.graph_vessel_readback import run_local_vessel_readback
from songryeon_core.runtime.graph_vessel_summary_provenance_audit import (
    render_vessel_summary_provenance_audit_text,
    run_local_vessel_summary_provenance_audit,
)
from songryeon_core.runtime.graph_vessel_summary_invalidation_candidate_audit import (
    render_vessel_summary_invalidation_candidate_audit_text,
    run_local_vessel_summary_invalidation_candidate_audit,
)
from songryeon_core.runtime.l_loop_smoke import run_qwen_l_loop_smoke
from songryeon_core.runtime.night_changed_source_summary import (
    DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR,
    run_night_changed_source_summary,
)
from songryeon_core.runtime.night_token_budget_layer_summary import (
    DEFAULT_NIGHT_TOKEN_BUDGET_MAX_LAYER_DEPTH,
    DEFAULT_NIGHT_TOKEN_BUDGET_MAX_STEPS,
    DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_MAX_BUNDLE_CHARS,
    DEFAULT_NIGHT_TOKEN_BUDGET_TARGET_CONTEXT_CHARS,
    run_night_token_budget_layer_summary,
)
from songryeon_core.runtime.r_loop_vessel_read_packet import (
    render_r_loop_vessel_read_packet_text,
    run_local_r_loop_vessel_read_packet,
)
from songryeon_core.runtime.r_loop_vessel_one_step import (
    render_r_loop_vessel_one_step_text,
    render_r_loop_vessel_traverse_text,
    run_local_r_loop_vessel_one_step,
    run_local_r_loop_vessel_traverse,
)
from songryeon_core.runtime.r_loop_vessel_answer_demo import (
    render_r_loop_vessel_answer_demo_text,
    run_local_r_loop_vessel_answer_demo,
)
from songryeon_core.runtime.replay import replay_run
from songryeon_core.runtime.quick_smoke import run_quick_smoke_tests
from songryeon_core.runtime.smoke_test import run_smoke_tests
from songryeon_core.runtime.terminal_view import render_compact_turn, render_pretty_turn
from songryeon_core.runtime.user_turn import (
    run_codex_sdk_user_turn,
    run_fake_user_turn,
    run_openai_user_turn,
    run_qwen_codex_hybrid_user_turn,
    run_qwen_user_turn,
)
from songryeon_core.runtime.live_trace import make_live_trace_sink
from songryeon_core.runtime.local_launcher import (
    load_local_env,
    resolve_main_cli_args,
)
from songryeon_core.runtime.chat_session import (
    ChatSessionMemory,
    attach_chat_session_snapshot,
    current_chat_turn_id,
    store_chat_turn_result,
)
from songryeon_core.runtime.competition_demo import (
    render_competition_demo,
    run_competition_demo,
)
from songryeon_core.core.workspace_manifest import (
    build_workspace_manifest,
    workspace_manifest_cli_payload,
)
from songryeon_core.runtime.defaults import (
    DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_QUERY_ATTEMPTS,
    DEFAULT_MAX_READ_DOC_CALLS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_SEARCH_TOP_K,
)
from songryeon_core.llm.runtime import ping_openai, ping_qwen
from songryeon_core.llm.codex_sdk_adapter import ping_codex_sdk
from songryeon_core.tools.document_tools import search_docs


def main() -> None:
    # 이 파일은 SongRyeon Core의 CLI 입구다.
    # 사용자가 `python main.py qwen-chat`처럼 명령을 치면 여기서 명령을 해석하고
    # 실제 작업은 runtime/nodes/tools 모듈에 넘긴다.
    _configure_stdio()
    # 간편 실행에서는 PowerShell 스크립트를 점으로 불러오지 않아도 되도록
    # 프로젝트 루트의 Git 비추적 .env를 Python이 직접 읽는다.
    load_local_env(Path(__file__).resolve().parent / ".env")
    cli_args, default_launch = resolve_main_cli_args(sys.argv[1:])

    # argparse는 "터미널 명령어를 파이썬 함수 호출로 바꾸는 장치"라고 보면 된다.
    # subparser 하나가 CLI 명령 하나에 대응한다.
    parser = argparse.ArgumentParser(prog="songryeon-core")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # dry-run은 Qwen 없이도 한 턴 실행 구조와 trace/data가 살아있는지 보는 기본 점검이다.
    dry_run_parser = subparsers.add_parser("dry-run")
    dry_run_parser.add_argument("--export", default=None)
    dry_run_parser.add_argument("--same-turn-l-reroute", action="store_true")
    dry_run_parser.add_argument("--max-l-runs-per-turn", type=int, default=1)
    dry_run_parser.add_argument("--same-turn-r-reroute", action="store_true")
    dry_run_parser.add_argument("--max-r-runs-per-turn", type=int, default=2)
    dry_run_parser.add_argument("--live-trace", action="store_true")

    # search-docs는 L루프 전체를 돌리지 않고 문서 검색 도구만 직접 확인할 때 쓴다.
    # qwen-chat은 송련 전체를 돌려보는 모드이고, search-docs는 문서 검색 엔진만 따로 뜯어보는 모드다.
    # 따라서 "송련이 못 찾은 것인지, 검색 도구가 못 찾은 것인지"를 분리해서 진단할 때 중요하다.
    search_parser = subparsers.add_parser("search-docs")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=3)

    # show-orders는 현재 발주서 목록을 빠르게 훑기 위한 작은 보조 명령이다.
    subparsers.add_parser("show-orders")

    # workspace-check는 LLM 호출이나 파일 복사 없이 업무 폴더 읽기 경계를 먼저 보여준다.
    workspace_check_parser = subparsers.add_parser("workspace-check")
    workspace_check_parser.add_argument("root")

    # replay는 export로 저장한 실행 기록을 다시 읽을 때 쓴다.
    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("run_dir")

    # qwen-ping은 로컬 Qwen/Ollama 연결이 살아있는지 확인하는 가장 작은 LLM 호출이다.
    qwen_ping_parser = subparsers.add_parser("qwen-ping")
    qwen_ping_parser.add_argument("--endpoint", default=None)
    qwen_ping_parser.add_argument("--model-id", default=None)
    qwen_ping_parser.add_argument("--timeout", type=int, default=None)

    # openai-ping은 전체 송련을 돌리기 전에 API 키/모델/과금 연결을 한 번만 확인한다.
    openai_ping_parser = subparsers.add_parser("openai-ping")
    openai_ping_parser.add_argument("--model-id", default=None)
    openai_ping_parser.add_argument("--timeout", type=int, default=None)
    openai_ping_parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high", "xhigh"],
        default=None,
    )
    openai_ping_parser.add_argument("--max-output-tokens", type=int, default=1024)

    codex_sdk_ping_parser = subparsers.add_parser("codex-sdk-ping")
    codex_sdk_ping_parser.add_argument("--model-id", default="gpt-5.4")
    codex_sdk_ping_parser.add_argument("--codex-bin", default=None)
    codex_sdk_ping_parser.add_argument(
        "--reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        default="low",
    )

    codex_sdk_turn_parser = subparsers.add_parser("codex-sdk-turn")
    codex_sdk_turn_parser.add_argument("user_input")
    _add_codex_sdk_turn_runtime_args(codex_sdk_turn_parser)

    codex_sdk_chat_parser = subparsers.add_parser("codex-sdk-chat")
    _add_codex_sdk_turn_runtime_args(codex_sdk_chat_parser)

    # 혼합 모드는 Qwen이 탐색하고 Codex가 판단·보고하는 비용 절약형 경로다.
    hybrid_turn_parser = subparsers.add_parser("hybrid-turn")
    hybrid_turn_parser.add_argument("user_input")
    _add_hybrid_turn_runtime_args(hybrid_turn_parser)

    hybrid_chat_parser = subparsers.add_parser("hybrid-chat")
    _add_hybrid_turn_runtime_args(hybrid_chat_parser)

    # qwen-l-loop-smoke는 Qwen이 붙은 L루프만 좁게 점검한다.
    qwen_l_loop_parser = subparsers.add_parser("qwen-l-loop-smoke")
    qwen_l_loop_parser.add_argument("--endpoint", default=None)
    qwen_l_loop_parser.add_argument("--model-id", default=None)
    qwen_l_loop_parser.add_argument("--timeout", type=int, default=None)
    qwen_l_loop_parser.add_argument("--export", default=None)

    # fake-turn은 가짜 LLM adapter로 한 턴을 돌린다. 구조 회귀 테스트에 가깝다.
    fake_turn_parser = subparsers.add_parser("fake-turn")
    fake_turn_parser.add_argument("user_input")
    _add_turn_runtime_args(
        fake_turn_parser,
        include_qwen_args=False,
        include_workspace=True,
    )

    # qwen-turn은 사용자 입력 하나를 Qwen 기반 한 턴으로 실행한다.
    qwen_turn_parser = subparsers.add_parser("qwen-turn")
    qwen_turn_parser.add_argument("user_input")
    _add_turn_runtime_args(
        qwen_turn_parser,
        include_qwen_args=True,
        include_workspace=True,
    )

    # qwen-chat은 qwen-turn을 반복 호출하는 대화형 껍데기다.
    # 세션 안 raw conversation과 capsule을 다음 턴의 ZeroState로 이어준다.
    qwen_chat_parser = subparsers.add_parser("qwen-chat")
    _add_turn_runtime_args(
        qwen_chat_parser,
        include_qwen_args=True,
        include_workspace=True,
    )

    # 외부 Codex 비교 실험은 기존 qwen 명령과 분리해 실수로 과금하지 않게 한다.
    openai_turn_parser = subparsers.add_parser("openai-turn")
    openai_turn_parser.add_argument("user_input")
    _add_openai_turn_runtime_args(openai_turn_parser)

    openai_chat_parser = subparsers.add_parser("openai-chat")
    _add_openai_turn_runtime_args(openai_chat_parser)

    # competition-demo는 외부 API/Neo4j 없이 심사용 신뢰 경계 세 가지를 한 화면에 재현한다.
    competition_demo_parser = subparsers.add_parser("competition-demo")
    competition_demo_parser.add_argument("--json", action="store_true")

    # quick-smoke는 문서 검색/Neo4j/Qwen 없이 최소 건강 상태만 본다.
    subparsers.add_parser("quick-smoke")

    # smoke-test는 오래 걸리는 전체 통합 기준선이다. 빠른 점검은 quick-smoke/fast-test를 쓴다.
    subparsers.add_parser("smoke-test")
    subparsers.add_parser("full-smoke")
    fast_test_parser = subparsers.add_parser("fast-test")
    fast_test_parser.add_argument("--profile", choices=["core", "graph"], default="graph")
    fast_test_parser.add_argument("--skip-compileall", action="store_true")
    fast_test_parser.add_argument("--dry-run", action="store_true")

    vessel_first_write_parser = subparsers.add_parser("vessel-first-write")
    vessel_first_write_parser.add_argument("--root", default=".")
    vessel_first_write_parser.add_argument("--batch-id", default="manual_vessel_first_write")
    vessel_first_write_parser.add_argument("--turn-id", default="turn_vessel_first_write_0001")
    vessel_first_write_parser.add_argument("--uri", default=None)
    vessel_first_write_parser.add_argument("--user", default=None)
    vessel_first_write_parser.add_argument("--password", default=None)
    vessel_first_write_parser.add_argument("--database", default=None)
    vessel_first_write_parser.add_argument("--allow-no-auth", action="store_true")
    vessel_first_write_parser.add_argument("--include-source-manifest", action="store_true")
    vessel_first_write_parser.add_argument("--store-text-snapshots", action="store_true")

    vessel_readback_parser = subparsers.add_parser("vessel-readback")
    vessel_readback_parser.add_argument("--batch-id", default="manual_vessel_readback")
    vessel_readback_parser.add_argument("--turn-id", default="turn_vessel_readback_0001")
    vessel_readback_parser.add_argument("--uri", default=None)
    vessel_readback_parser.add_argument("--user", default=None)
    vessel_readback_parser.add_argument("--password", default=None)
    vessel_readback_parser.add_argument("--database", default=None)
    vessel_readback_parser.add_argument("--allow-no-auth", action="store_true")

    vessel_inspect_parser = subparsers.add_parser("vessel-inspect")
    vessel_inspect_parser.add_argument("--batch-id", default="manual_vessel_inspect")
    vessel_inspect_parser.add_argument("--turn-id", default="turn_vessel_inspect_0001")
    vessel_inspect_parser.add_argument("--uri", default=None)
    vessel_inspect_parser.add_argument("--user", default=None)
    vessel_inspect_parser.add_argument("--password", default=None)
    vessel_inspect_parser.add_argument("--database", default=None)
    vessel_inspect_parser.add_argument("--allow-no-auth", action="store_true")
    vessel_inspect_parser.add_argument("--limit", type=int, default=50)
    vessel_inspect_parser.add_argument("--format", choices=["json", "text"], default="json")

    vessel_summary_provenance_audit_parser = subparsers.add_parser(
        "vessel-summary-provenance-audit"
    )
    vessel_summary_provenance_audit_parser.add_argument(
        "--batch-id",
        default="manual_vessel_summary_provenance_audit",
    )
    vessel_summary_provenance_audit_parser.add_argument(
        "--turn-id",
        default="turn_vessel_summary_provenance_audit_0001",
    )
    vessel_summary_provenance_audit_parser.add_argument("--uri", default=None)
    vessel_summary_provenance_audit_parser.add_argument("--user", default=None)
    vessel_summary_provenance_audit_parser.add_argument("--password", default=None)
    vessel_summary_provenance_audit_parser.add_argument("--database", default=None)
    vessel_summary_provenance_audit_parser.add_argument("--allow-no-auth", action="store_true")
    vessel_summary_provenance_audit_parser.add_argument("--limit", type=int, default=50)
    vessel_summary_provenance_audit_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )

    vessel_summary_invalidation_candidate_audit_parser = subparsers.add_parser(
        "vessel-summary-invalidation-candidate-audit"
    )
    vessel_summary_invalidation_candidate_audit_parser.add_argument(
        "--batch-id",
        default="manual_vessel_summary_invalidation_candidate_audit",
    )
    vessel_summary_invalidation_candidate_audit_parser.add_argument(
        "--turn-id",
        default="turn_vessel_summary_invalidation_candidate_audit_0001",
    )
    vessel_summary_invalidation_candidate_audit_parser.add_argument("--uri", default=None)
    vessel_summary_invalidation_candidate_audit_parser.add_argument("--user", default=None)
    vessel_summary_invalidation_candidate_audit_parser.add_argument("--password", default=None)
    vessel_summary_invalidation_candidate_audit_parser.add_argument("--database", default=None)
    vessel_summary_invalidation_candidate_audit_parser.add_argument(
        "--allow-no-auth",
        action="store_true",
    )
    vessel_summary_invalidation_candidate_audit_parser.add_argument(
        "--limit",
        type=int,
        default=50,
    )
    vessel_summary_invalidation_candidate_audit_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )

    r_loop_vessel_read_packet_parser = subparsers.add_parser("vessel-r-read-packet")
    r_loop_vessel_read_packet_parser.add_argument(
        "--batch-id",
        default="manual_r_loop_vessel_read_packet",
    )
    r_loop_vessel_read_packet_parser.add_argument(
        "--turn-id",
        default="turn_r_loop_vessel_read_packet_0001",
    )
    r_loop_vessel_read_packet_parser.add_argument("--uri", default=None)
    r_loop_vessel_read_packet_parser.add_argument("--user", default=None)
    r_loop_vessel_read_packet_parser.add_argument("--password", default=None)
    r_loop_vessel_read_packet_parser.add_argument("--database", default=None)
    r_loop_vessel_read_packet_parser.add_argument("--allow-no-auth", action="store_true")
    r_loop_vessel_read_packet_parser.add_argument("--limit", type=int, default=50)
    r_loop_vessel_read_packet_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )

    r_loop_vessel_one_step_parser = subparsers.add_parser("vessel-r-one-step")
    r_loop_vessel_one_step_parser.add_argument("user_question")
    r_loop_vessel_one_step_parser.add_argument(
        "--batch-id",
        default="manual_r_loop_vessel_one_step",
    )
    r_loop_vessel_one_step_parser.add_argument(
        "--turn-id",
        default="turn_r_loop_vessel_one_step_0001",
    )
    r_loop_vessel_one_step_parser.add_argument("--uri", default=None)
    r_loop_vessel_one_step_parser.add_argument("--user", default=None)
    r_loop_vessel_one_step_parser.add_argument("--password", default=None)
    r_loop_vessel_one_step_parser.add_argument("--database", default=None)
    r_loop_vessel_one_step_parser.add_argument("--allow-no-auth", action="store_true")
    r_loop_vessel_one_step_parser.add_argument("--limit", type=int, default=50)
    r_loop_vessel_one_step_parser.add_argument(
        "--llm-mode",
        choices=["off", "fake", "qwen"],
        default="fake",
    )
    r_loop_vessel_one_step_parser.add_argument("--endpoint", default=None)
    r_loop_vessel_one_step_parser.add_argument("--model-id", default=None)
    r_loop_vessel_one_step_parser.add_argument("--timeout", type=int, default=None)
    r_loop_vessel_one_step_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )

    r_loop_vessel_traverse_parser = subparsers.add_parser("vessel-r-traverse")
    r_loop_vessel_traverse_parser.add_argument("user_question")
    r_loop_vessel_traverse_parser.add_argument(
        "--batch-id",
        default="manual_r_loop_vessel_traverse",
    )
    r_loop_vessel_traverse_parser.add_argument(
        "--turn-id",
        default="turn_r_loop_vessel_traverse_0001",
    )
    r_loop_vessel_traverse_parser.add_argument("--uri", default=None)
    r_loop_vessel_traverse_parser.add_argument("--user", default=None)
    r_loop_vessel_traverse_parser.add_argument("--password", default=None)
    r_loop_vessel_traverse_parser.add_argument("--database", default=None)
    r_loop_vessel_traverse_parser.add_argument("--allow-no-auth", action="store_true")
    r_loop_vessel_traverse_parser.add_argument("--limit", type=int, default=50)
    r_loop_vessel_traverse_parser.add_argument(
        "--llm-mode",
        choices=["off", "fake", "qwen"],
        default="fake",
    )
    r_loop_vessel_traverse_parser.add_argument("--endpoint", default=None)
    r_loop_vessel_traverse_parser.add_argument("--model-id", default=None)
    r_loop_vessel_traverse_parser.add_argument("--timeout", type=int, default=None)
    r_loop_vessel_traverse_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )

    r_loop_vessel_answer_demo_parser = subparsers.add_parser("vessel-r-answer-demo")
    r_loop_vessel_answer_demo_parser.add_argument("user_question")
    r_loop_vessel_answer_demo_parser.add_argument(
        "--batch-id",
        default="manual_r_loop_vessel_answer_demo",
    )
    r_loop_vessel_answer_demo_parser.add_argument(
        "--turn-id",
        default="turn_r_loop_vessel_answer_demo_0001",
    )
    r_loop_vessel_answer_demo_parser.add_argument("--uri", default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--user", default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--password", default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--database", default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--allow-no-auth", action="store_true")
    r_loop_vessel_answer_demo_parser.add_argument("--limit", type=int, default=50)
    r_loop_vessel_answer_demo_parser.add_argument("--max-node-reads", type=int, default=6)
    r_loop_vessel_answer_demo_parser.add_argument(
        "--max-raw-original-material-reads",
        type=int,
        default=5,
    )
    r_loop_vessel_answer_demo_parser.add_argument(
        "--llm-mode",
        choices=["fake", "qwen"],
        default="fake",
    )
    r_loop_vessel_answer_demo_parser.add_argument("--endpoint", default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--model-id", default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--timeout", type=int, default=None)
    r_loop_vessel_answer_demo_parser.add_argument("--write-trace-cache", action="store_true")
    r_loop_vessel_answer_demo_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
    )

    night_changed_sources_parser = subparsers.add_parser(
        "night-summarize-changed-sources"
    )
    night_changed_sources_parser.add_argument("--root", default=".")
    night_changed_sources_parser.add_argument(
        "--store-dir",
        default=DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR,
    )
    night_changed_sources_parser.add_argument("--batch-id", default=None)
    night_changed_sources_parser.add_argument("--turn-id", default=None)
    night_changed_sources_parser.add_argument(
        "--llm-mode",
        choices=["off", "fake", "qwen"],
        default="off",
    )
    night_changed_sources_parser.add_argument("--endpoint", default=None)
    night_changed_sources_parser.add_argument("--model-id", default=None)
    night_changed_sources_parser.add_argument("--timeout", type=int, default=None)
    night_changed_sources_parser.add_argument("--one-at-a-time", action="store_true")
    night_changed_sources_parser.add_argument("--write-vessel", action="store_true")
    night_changed_sources_parser.add_argument("--uri", default=None)
    night_changed_sources_parser.add_argument("--user", default=None)
    night_changed_sources_parser.add_argument("--password", default=None)
    night_changed_sources_parser.add_argument("--database", default=None)
    night_changed_sources_parser.add_argument("--allow-no-auth", action="store_true")

    night_token_layer_parser = subparsers.add_parser("night-summarize-token-layer")
    night_token_layer_parser.add_argument(
        "--store-dir",
        default=DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR,
    )
    night_token_layer_parser.add_argument("--batch-id", default=None)
    night_token_layer_parser.add_argument("--turn-id", default=None)
    night_token_layer_parser.add_argument(
        "--max-bundle-chars",
        type=int,
        default=DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_MAX_BUNDLE_CHARS,
    )
    night_token_layer_parser.add_argument(
        "--llm-mode",
        choices=["off", "fake", "qwen"],
        default="off",
    )
    night_token_layer_parser.add_argument("--endpoint", default=None)
    night_token_layer_parser.add_argument("--model-id", default=None)
    night_token_layer_parser.add_argument("--timeout", type=int, default=None)
    night_token_layer_parser.add_argument("--until-context-budget", action="store_true")
    night_token_layer_parser.add_argument(
        "--target-context-chars",
        type=int,
        default=DEFAULT_NIGHT_TOKEN_BUDGET_TARGET_CONTEXT_CHARS,
    )
    night_token_layer_parser.add_argument(
        "--max-layer-depth",
        type=int,
        default=DEFAULT_NIGHT_TOKEN_BUDGET_MAX_LAYER_DEPTH,
    )
    night_token_layer_parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_NIGHT_TOKEN_BUDGET_MAX_STEPS,
    )
    night_token_layer_parser.add_argument("--max-runtime-minutes", type=float, default=None)
    night_token_layer_parser.add_argument("--progress-jsonl", default=None)
    night_token_layer_parser.add_argument(
        "--vessel-write-mode",
        choices=["none", "every-step", "at-end"],
        default=None,
    )
    night_token_layer_parser.add_argument("--no-stop-on-failure", action="store_true")
    night_token_layer_parser.add_argument("--write-vessel", action="store_true")
    night_token_layer_parser.add_argument("--uri", default=None)
    night_token_layer_parser.add_argument("--user", default=None)
    night_token_layer_parser.add_argument("--password", default=None)
    night_token_layer_parser.add_argument("--database", default=None)
    night_token_layer_parser.add_argument("--allow-no-auth", action="store_true")

    args = parser.parse_args(cli_args)
    args.default_launch = default_launch

    # 여기부터는 실제 실행 분기다.
    # args.command 값에 따라 위에서 등록한 명령이 runtime 함수로 연결된다.
    if args.command == "dry-run":
        result = run_dry_turn(
            export_dir=args.export,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
            same_turn_r_reroute_enabled=args.same_turn_r_reroute,
            max_r_runs_per_turn=args.max_r_runs_per_turn,
            live_trace_sink=make_live_trace_sink(enabled=args.live_trace),
        )
        print("DRY_RUN_OK")
        print(json.dumps(_summary(result), ensure_ascii=False, indent=2))
    elif args.command == "search-docs":
        result = search_docs(root="Administrative_Reform_1", query=args.query, top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "show-orders":
        for path in sorted(Path("Administrative_Reform_1/04_Orders").glob("*.md")):
            print(path.as_posix())
    elif args.command == "workspace-check":
        frame = build_workspace_manifest(
            root_path=args.root,
            turn_id="workspace_check",
        )
        print(
            json.dumps(
                workspace_manifest_cli_payload(frame),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "replay":
        print(replay_run(args.run_dir))
    elif args.command == "qwen-ping":
        result = ping_qwen(
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "openai-ping":
        result = ping_openai(
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            reasoning_effort=args.reasoning_effort,
            max_output_tokens=args.max_output_tokens,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "codex-sdk-ping":
        result = ping_codex_sdk(
            model_id=args.model_id,
            reasoning_effort=args.reasoning_effort,
            codex_bin=args.codex_bin,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "codex-sdk-turn":
        result = _run_codex_sdk_turn_from_args(args, user_input=args.user_input)
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
        else:
            print(
                json.dumps(
                    _turn_summary(result, include_report=args.include_report),
                    ensure_ascii=False,
                    indent=2,
                )
            )
    elif args.command == "codex-sdk-chat":
        _run_codex_sdk_chat(args)
    elif args.command == "hybrid-turn":
        result = _run_hybrid_turn_from_args(args, user_input=args.user_input)
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
        else:
            print(
                json.dumps(
                    _turn_summary(result, include_report=args.include_report),
                    ensure_ascii=False,
                    indent=2,
                )
            )
    elif args.command == "hybrid-chat":
        _run_hybrid_chat(args)
    elif args.command == "qwen-l-loop-smoke":
        result = run_qwen_l_loop_smoke(
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            export_dir=args.export,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "fake-turn":
        result = run_fake_user_turn(
            user_input=args.user_input,
            export_dir=args.export,
            max_tool_calls=args.max_tool_calls,
            search_top_k=args.search_top_k,
            max_query_attempts=args.max_query_attempts,
            max_query_candidates=args.max_query_candidates,
            max_read_doc_calls=args.max_read_doc_calls,
            max_input_chars=args.max_input_chars,
            max_document_context_chars=args.max_document_context_chars,
            include_data_records=args.pretty or args.compact,
            force_l_route=args.force_l,
            force_vessel_r_route=args.force_vessel_r_route,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
            same_turn_r_reroute_enabled=args.same_turn_r_reroute,
            max_r_runs_per_turn=args.max_r_runs_per_turn,
            enable_r_route_experimental=args.enable_r_route_experimental,
            enable_vessel_r_route=args.enable_vessel_r_route,
            vessel_r_uri=args.vessel_uri,
            vessel_r_user=args.vessel_user,
            vessel_r_password=args.vessel_password,
            vessel_r_database=args.database,
            vessel_r_allow_no_auth=args.vessel_allow_no_auth,
            vessel_r_limit=args.vessel_limit,
            vessel_r_max_node_reads=args.vessel_max_node_reads,
            vessel_r_max_raw_original_material_reads=(
                args.vessel_max_raw_original_material_reads
            ),
            live_trace=args.live_trace,
            workspace_root=args.workspace,
        )
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
        elif args.compact:
            print(render_compact_turn(result, user_input=args.user_input))
        else:
            print(json.dumps(_turn_summary(result, include_report=args.include_report), ensure_ascii=False, indent=2))
    elif args.command == "qwen-turn":
        result = run_qwen_user_turn(
            user_input=args.user_input,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            export_dir=args.export,
            max_tool_calls=args.max_tool_calls,
            search_top_k=args.search_top_k,
            max_query_attempts=args.max_query_attempts,
            max_query_candidates=args.max_query_candidates,
            max_read_doc_calls=args.max_read_doc_calls,
            max_input_chars=args.max_input_chars,
            max_document_context_chars=args.max_document_context_chars,
            include_data_records=args.pretty or args.compact,
            force_l_route=args.force_l,
            force_vessel_r_route=args.force_vessel_r_route,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
            same_turn_r_reroute_enabled=args.same_turn_r_reroute,
            max_r_runs_per_turn=args.max_r_runs_per_turn,
            enable_r_route_experimental=args.enable_r_route_experimental,
            enable_vessel_r_route=args.enable_vessel_r_route,
            vessel_r_uri=args.vessel_uri,
            vessel_r_user=args.vessel_user,
            vessel_r_password=args.vessel_password,
            vessel_r_database=args.database,
            vessel_r_allow_no_auth=args.vessel_allow_no_auth,
            vessel_r_limit=args.vessel_limit,
            vessel_r_max_node_reads=args.vessel_max_node_reads,
            vessel_r_max_raw_original_material_reads=(
                args.vessel_max_raw_original_material_reads
            ),
            live_trace=args.live_trace,
            workspace_root=args.workspace,
        )
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
        elif args.compact:
            print(render_compact_turn(result, user_input=args.user_input))
        else:
            print(json.dumps(_turn_summary(result, include_report=args.include_report), ensure_ascii=False, indent=2))
    elif args.command == "qwen-chat":
        _run_qwen_chat(args)
    elif args.command == "openai-turn":
        result = _run_openai_turn_from_args(args, user_input=args.user_input)
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
        else:
            print(
                json.dumps(
                    _turn_summary(result, include_report=args.include_report),
                    ensure_ascii=False,
                    indent=2,
                )
            )
    elif args.command == "openai-chat":
        _run_openai_chat(args)
    elif args.command == "competition-demo":
        result = run_competition_demo()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(render_competition_demo(result))
        if result.get("passed") is not True:
            raise SystemExit(1)
    elif args.command == "quick-smoke":
        print(json.dumps(run_quick_smoke_tests(), ensure_ascii=False, indent=2))
    elif args.command == "smoke-test":
        print(json.dumps(run_smoke_tests(), ensure_ascii=False, indent=2))
    elif args.command == "full-smoke":
        print(json.dumps(run_smoke_tests(), ensure_ascii=False, indent=2))
    elif args.command == "fast-test":
        result = run_fast_tests(
            profile=args.profile,
            skip_compileall=args.skip_compileall,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] == "FAST_TEST_FAILED":
            raise SystemExit(1)
    elif args.command == "vessel-first-write":
        result = run_local_vessel_first_write(
            root_path=args.root,
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            include_source_manifest=args.include_source_manifest,
            store_text_snapshots=args.store_text_snapshots,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["write_status"] == "write_failed":
            raise SystemExit(1)
    elif args.command == "vessel-readback":
        result = run_local_vessel_readback(
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["readback_status"] in {"read_failed", "failed"}:
            raise SystemExit(1)
    elif args.command == "vessel-inspect":
        result = run_local_vessel_inspect(
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
        )
        if args.format == "text":
            print(render_vessel_inspect_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["inspect_status"] == "read_failed":
            raise SystemExit(1)
    elif args.command == "vessel-summary-provenance-audit":
        result = run_local_vessel_summary_provenance_audit(
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
        )
        if args.format == "text":
            print(render_vessel_summary_provenance_audit_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["audit_status"] == "read_failed":
            raise SystemExit(1)
    elif args.command == "vessel-summary-invalidation-candidate-audit":
        result = run_local_vessel_summary_invalidation_candidate_audit(
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
        )
        if args.format == "text":
            print(render_vessel_summary_invalidation_candidate_audit_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["audit_status"] == "read_failed":
            raise SystemExit(1)
    elif args.command == "vessel-r-read-packet":
        result = run_local_r_loop_vessel_read_packet(
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
        )
        if args.format == "text":
            print(render_r_loop_vessel_read_packet_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["read_status"] == "read_failed":
            raise SystemExit(1)
    elif args.command == "vessel-r-one-step":
        result = run_local_r_loop_vessel_one_step(
            user_question=args.user_question,
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
            llm_mode=args.llm_mode,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
        )
        if args.format == "text":
            print(render_r_loop_vessel_one_step_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["one_step_status"] == "failed":
            raise SystemExit(1)
    elif args.command == "vessel-r-traverse":
        result = run_local_r_loop_vessel_traverse(
            user_question=args.user_question,
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
            llm_mode=args.llm_mode,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
        )
        if args.format == "text":
            print(render_r_loop_vessel_traverse_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["traverse_status"] == "failed":
            raise SystemExit(1)
    elif args.command == "vessel-r-answer-demo":
        result = run_local_r_loop_vessel_answer_demo(
            user_question=args.user_question,
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
            limit=args.limit,
            max_node_reads=args.max_node_reads,
            max_raw_original_material_reads=args.max_raw_original_material_reads,
            llm_mode=args.llm_mode,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            write_trace_cache=args.write_trace_cache,
        )
        if args.format == "text":
            print(render_r_loop_vessel_answer_demo_text(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["demo_status"] == "blocked":
            raise SystemExit(1)
    elif args.command == "night-summarize-changed-sources":
        result = run_night_changed_source_summary(
            root_path=args.root,
            store_dir=args.store_dir,
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            llm_mode=args.llm_mode,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            one_at_a_time=args.one_at_a_time,
            write_vessel=args.write_vessel,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if (
            result.get("write_result") is not None
            and isinstance(result.get("write_result"), dict)
            and result["write_result"].get("write_status") == "write_failed"
        ):
            raise SystemExit(1)
    elif args.command == "night-summarize-token-layer":
        result = run_night_token_budget_layer_summary(
            store_dir=args.store_dir,
            batch_id=args.batch_id,
            turn_id=args.turn_id,
            max_bundle_chars=args.max_bundle_chars,
            llm_mode=args.llm_mode,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            until_context_budget=args.until_context_budget,
            target_context_chars=args.target_context_chars,
            max_layer_depth=args.max_layer_depth,
            max_steps=args.max_steps,
            max_runtime_minutes=args.max_runtime_minutes,
            progress_jsonl=args.progress_jsonl,
            vessel_write_mode=args.vessel_write_mode,
            stop_on_failure=not args.no_stop_on_failure,
            write_vessel=args.write_vessel,
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            allow_no_auth=args.allow_no_auth,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if (
            result.get("write_result") is not None
            and isinstance(result.get("write_result"), dict)
            and result["write_result"].get("write_status") == "write_failed"
        ):
            raise SystemExit(1)


def _add_turn_runtime_args(
    parser: argparse.ArgumentParser,
    *,
    include_qwen_args: bool,
    include_workspace: bool = False,
) -> None:
    # fake-turn/qwen-turn/qwen-chat이 공유하는 실행 옵션을 한 곳에서 붙인다.
    # 이렇게 해두면 max_tool_calls 같은 기본값을 명령마다 따로 고치지 않아도 된다.
    parser.add_argument("--export", default=None)
    parser.add_argument("--include-report", action="store_true")
    display_group = parser.add_mutually_exclusive_group()
    display_group.add_argument("--pretty", action="store_true")
    display_group.add_argument("--compact", action="store_true")
    parser.add_argument("--max-tool-calls", type=int, default=DEFAULT_MAX_TOOL_CALLS)
    parser.add_argument("--search-top-k", type=int, default=DEFAULT_SEARCH_TOP_K)
    parser.add_argument("--max-query-attempts", type=int, default=DEFAULT_MAX_QUERY_ATTEMPTS)
    parser.add_argument("--max-query-candidates", type=int, default=None)
    parser.add_argument("--max-read-doc-calls", type=int, default=DEFAULT_MAX_READ_DOC_CALLS)
    parser.add_argument("--max-input-chars", type=int, default=DEFAULT_MAX_INPUT_CHARS)
    parser.add_argument(
        "--max-document-context-chars",
        type=int,
        default=DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    )
    parser.add_argument("--force-l", action="store_true")
    parser.add_argument("--force-vessel-r-route", action="store_true")
    parser.add_argument("--same-turn-l-reroute", action="store_true")
    parser.add_argument("--max-l-runs-per-turn", type=int, default=1)
    parser.add_argument("--same-turn-r-reroute", action="store_true")
    parser.add_argument("--max-r-runs-per-turn", type=int, default=2)
    parser.add_argument("--enable-r-route-experimental", action="store_true")
    parser.add_argument("--enable-vessel-r-route", action="store_true")
    parser.add_argument("--vessel-uri", default=None)
    parser.add_argument("--vessel-user", default=None)
    parser.add_argument("--vessel-password", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--vessel-allow-no-auth", action="store_true")
    parser.add_argument("--vessel-limit", type=int, default=50)
    parser.add_argument("--vessel-max-node-reads", type=int, default=6)
    parser.add_argument("--vessel-max-raw-original-material-reads", type=int, default=5)
    parser.add_argument("--live-trace", action="store_true")
    if include_workspace:
        parser.add_argument(
            "--workspace",
            default=None,
            help="로컬 fake/Qwen이 읽기 전용으로 조사할 업무 폴더",
        )
    if include_qwen_args:
        parser.add_argument("--endpoint", default=None)
        parser.add_argument("--model-id", default=None)
        parser.add_argument("--timeout", type=int, default=None)


def _add_openai_turn_runtime_args(parser: argparse.ArgumentParser) -> None:
    """외부 API 실험 옵션은 qwen endpoint 옵션과 섞지 않는다."""

    _add_turn_runtime_args(parser, include_qwen_args=False)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high", "xhigh"],
        default=None,
    )
    parser.add_argument("--max-output-tokens", type=int, default=None)


def _add_codex_sdk_turn_runtime_args(parser: argparse.ArgumentParser) -> None:
    _add_turn_runtime_args(parser, include_qwen_args=False)
    parser.add_argument("--model-id", default="gpt-5.4")
    parser.add_argument("--codex-bin", default=None)
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        default="low",
    )


def _add_hybrid_turn_runtime_args(parser: argparse.ArgumentParser) -> None:
    _add_turn_runtime_args(parser, include_qwen_args=False)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--qwen-model-id", default="qwen3:14b")
    parser.add_argument("--qwen-timeout", type=int, default=None)
    parser.add_argument("--codex-model-id", default="gpt-5.6-sol")
    parser.add_argument("--codex-bin", default=None)
    parser.add_argument(
        "--codex-reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        default="low",
    )


def _run_openai_turn_from_args(
    args: argparse.Namespace,
    *,
    user_input: str,
    turn_id: str | None = None,
    export_dir: str | None = None,
    previous_turn_capsules: list | None = None,
    recent_raw_conversation: list | None = None,
) -> dict[str, object]:
    return run_openai_user_turn(
        user_input=user_input,
        turn_id=turn_id,
        model_id=args.model_id,
        timeout_seconds=args.timeout,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
        export_dir=export_dir if export_dir is not None else args.export,
        max_tool_calls=args.max_tool_calls,
        search_top_k=args.search_top_k,
        max_query_attempts=args.max_query_attempts,
        max_query_candidates=args.max_query_candidates,
        max_read_doc_calls=args.max_read_doc_calls,
        max_input_chars=args.max_input_chars,
        max_document_context_chars=args.max_document_context_chars,
        include_data_records=args.pretty or turn_id is not None,
        force_l_route=args.force_l,
        force_vessel_r_route=args.force_vessel_r_route,
        same_turn_l_reroute_enabled=args.same_turn_l_reroute,
        max_l_runs_per_turn=args.max_l_runs_per_turn,
        same_turn_r_reroute_enabled=args.same_turn_r_reroute,
        max_r_runs_per_turn=args.max_r_runs_per_turn,
        enable_r_route_experimental=args.enable_r_route_experimental,
        enable_vessel_r_route=args.enable_vessel_r_route,
        vessel_r_uri=args.vessel_uri,
        vessel_r_user=args.vessel_user,
        vessel_r_password=args.vessel_password,
        vessel_r_database=args.database,
        vessel_r_allow_no_auth=args.vessel_allow_no_auth,
        vessel_r_limit=args.vessel_limit,
        vessel_r_max_node_reads=args.vessel_max_node_reads,
        vessel_r_max_raw_original_material_reads=(
            args.vessel_max_raw_original_material_reads
        ),
        previous_turn_capsules=previous_turn_capsules,
        recent_raw_conversation=recent_raw_conversation,
        live_trace=args.live_trace,
    )


def _run_codex_sdk_turn_from_args(
    args: argparse.Namespace,
    *,
    user_input: str,
    turn_id: str | None = None,
    export_dir: str | None = None,
    previous_turn_capsules: list | None = None,
    recent_raw_conversation: list | None = None,
) -> dict[str, object]:
    return run_codex_sdk_user_turn(
        user_input=user_input,
        turn_id=turn_id,
        model_id=args.model_id,
        reasoning_effort=args.reasoning_effort,
        codex_bin=args.codex_bin,
        export_dir=export_dir if export_dir is not None else args.export,
        max_tool_calls=args.max_tool_calls,
        search_top_k=args.search_top_k,
        max_query_attempts=args.max_query_attempts,
        max_query_candidates=args.max_query_candidates,
        max_read_doc_calls=args.max_read_doc_calls,
        max_input_chars=args.max_input_chars,
        max_document_context_chars=args.max_document_context_chars,
        include_data_records=args.pretty or turn_id is not None,
        force_l_route=args.force_l,
        force_vessel_r_route=args.force_vessel_r_route,
        same_turn_l_reroute_enabled=args.same_turn_l_reroute,
        max_l_runs_per_turn=args.max_l_runs_per_turn,
        same_turn_r_reroute_enabled=args.same_turn_r_reroute,
        max_r_runs_per_turn=args.max_r_runs_per_turn,
        enable_r_route_experimental=args.enable_r_route_experimental,
        enable_vessel_r_route=args.enable_vessel_r_route,
        vessel_r_uri=args.vessel_uri,
        vessel_r_user=args.vessel_user,
        vessel_r_password=args.vessel_password,
        vessel_r_database=args.database,
        vessel_r_allow_no_auth=args.vessel_allow_no_auth,
        vessel_r_limit=args.vessel_limit,
        vessel_r_max_node_reads=args.vessel_max_node_reads,
        vessel_r_max_raw_original_material_reads=(
            args.vessel_max_raw_original_material_reads
        ),
        previous_turn_capsules=previous_turn_capsules,
        recent_raw_conversation=recent_raw_conversation,
        live_trace=args.live_trace,
    )


def _run_hybrid_turn_from_args(
    args: argparse.Namespace,
    *,
    user_input: str,
    turn_id: str | None = None,
    export_dir: str | None = None,
    previous_turn_capsules: list | None = None,
    recent_raw_conversation: list | None = None,
) -> dict[str, object]:
    return run_qwen_codex_hybrid_user_turn(
        user_input=user_input,
        turn_id=turn_id,
        qwen_endpoint=args.endpoint,
        qwen_model_id=args.qwen_model_id,
        qwen_timeout_seconds=args.qwen_timeout,
        codex_model_id=args.codex_model_id,
        codex_reasoning_effort=args.codex_reasoning_effort,
        codex_bin=args.codex_bin,
        export_dir=export_dir if export_dir is not None else args.export,
        max_tool_calls=args.max_tool_calls,
        search_top_k=args.search_top_k,
        max_query_attempts=args.max_query_attempts,
        max_query_candidates=args.max_query_candidates,
        max_read_doc_calls=args.max_read_doc_calls,
        max_input_chars=args.max_input_chars,
        max_document_context_chars=args.max_document_context_chars,
        include_data_records=args.pretty or turn_id is not None,
        force_l_route=args.force_l,
        force_vessel_r_route=args.force_vessel_r_route,
        same_turn_l_reroute_enabled=args.same_turn_l_reroute,
        max_l_runs_per_turn=args.max_l_runs_per_turn,
        same_turn_r_reroute_enabled=args.same_turn_r_reroute,
        max_r_runs_per_turn=args.max_r_runs_per_turn,
        enable_r_route_experimental=args.enable_r_route_experimental,
        enable_vessel_r_route=args.enable_vessel_r_route,
        vessel_r_uri=args.vessel_uri,
        vessel_r_user=args.vessel_user,
        vessel_r_password=args.vessel_password,
        vessel_r_database=args.database,
        vessel_r_allow_no_auth=args.vessel_allow_no_auth,
        vessel_r_limit=args.vessel_limit,
        vessel_r_max_node_reads=args.vessel_max_node_reads,
        vessel_r_max_raw_original_material_reads=(
            args.vessel_max_raw_original_material_reads
        ),
        previous_turn_capsules=previous_turn_capsules,
        recent_raw_conversation=recent_raw_conversation,
        live_trace=args.live_trace,
    )


def _run_qwen_chat(args: argparse.Namespace) -> None:
    # 대화형 모드다. 사용자가 /exit 또는 /quit을 입력할 때까지 반복한다.
    # 세션 안 raw conversation과 capsule을 다음 턴의 ZeroState로 다시 주입한다.
    #H 따라서 차후 0의 기억과 다른 노드의 기억 패킷을 학습하고 이에 연동하여 최적의 공용 기억에 최근 대화랑 이전 작업 기억을 각 노드별로 나눠서 적절히 배분하는 방안이 필요하다.
    #H llm의 시야를 다루는 관점과는 달리, 송련은 본점의 헌법 문서에 명시돼 있듯 주요 구성 요소 중 하나가 데이터이기에, 코드랑 시스템은 노드별로 분산하여 배분되는 기억과 무관하게 통합적으로 관리할 체계가 필요하다.
    #H 장기기억과 DB는 본점의 노하우를 참조하면 시간 절약 및 효율적인 관리가 가능하다.
    print("SongRyeon qwen-chat")
    if getattr(args, "default_launch", False):
        vessel_status = "켜짐" if args.enable_vessel_r_route else "꺼짐"
        trace_status = "켜짐" if args.live_trace else "꺼짐"
        workspace_status = Path(args.workspace).name if args.workspace else "미설정"
        print(
            "간편 실행: "
            f"Qwen / Vessel R={vessel_status} / 실시간 진행={trace_status} / "
            f"workspace={workspace_status} / timeout={args.timeout}초"
        )
    print("종료하려면 /exit 또는 /quit 입력")
    print("")

    session_memory = ChatSessionMemory()
    while True:
        try:
            user_input = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            print("송련> 종료")
            return
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            print("송련> 종료")
            return

        export_dir = _chat_export_dir(args.export, session_memory.turn_index)
        current_turn_id = current_chat_turn_id(session_memory)
        print("송련> 처리 중...")
        # 실제 한 턴 실행은 runtime/user_turn.py로 넘어간다.
        # main.py는 입력값과 옵션을 모아서 넘기는 얇은 연결부로 남기는 것이 좋다.
        result = run_qwen_user_turn(
            user_input=user_input,
            turn_id=current_turn_id,
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
            export_dir=export_dir,
            max_tool_calls=args.max_tool_calls,
            search_top_k=args.search_top_k,
            max_query_attempts=args.max_query_attempts,
            max_query_candidates=args.max_query_candidates,
            max_read_doc_calls=args.max_read_doc_calls,
            max_input_chars=args.max_input_chars,
            max_document_context_chars=args.max_document_context_chars,
            include_data_records=True,
            force_l_route=args.force_l,
            force_vessel_r_route=args.force_vessel_r_route,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
            same_turn_r_reroute_enabled=args.same_turn_r_reroute,
            max_r_runs_per_turn=args.max_r_runs_per_turn,
            enable_r_route_experimental=args.enable_r_route_experimental,
            enable_vessel_r_route=args.enable_vessel_r_route,
            vessel_r_uri=args.vessel_uri,
            vessel_r_user=args.vessel_user,
            vessel_r_password=args.vessel_password,
            vessel_r_database=args.database,
            vessel_r_allow_no_auth=args.vessel_allow_no_auth,
            vessel_r_limit=args.vessel_limit,
            vessel_r_max_node_reads=args.vessel_max_node_reads,
            vessel_r_max_raw_original_material_reads=(
                args.vessel_max_raw_original_material_reads
            ),
            recent_raw_conversation=session_memory.recent_raw_conversation,
            previous_turn_capsules=session_memory.previous_turn_capsules,
            live_trace=args.live_trace,
            workspace_root=args.workspace,
        )
        attach_chat_session_snapshot(
            result=result,
            session_memory=session_memory,
            current_turn_id=current_turn_id,
        )
        if args.compact:
            print(render_compact_turn(result, user_input=user_input))
        else:
            print(render_pretty_turn(result, user_input=user_input))
        print("")
        store_chat_turn_result(
            session_memory=session_memory,
            current_turn_id=current_turn_id,
            user_input=user_input,
            result=result,
        )


def _run_openai_chat(args: argparse.Namespace) -> None:
    """외부 API 비교용 대화 모드. 세션 기억 규칙은 qwen-chat과 같다."""

    print("SongRyeon openai-chat")
    print("외부 API 호출마다 과금될 수 있습니다. 종료: /exit 또는 /quit")
    print("")

    session_memory = ChatSessionMemory()
    while True:
        try:
            user_input = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            print("송련> 종료")
            return
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            print("송련> 종료")
            return

        export_dir = _chat_export_dir(args.export, session_memory.turn_index)
        current_turn_id = current_chat_turn_id(session_memory)
        print("송련> 외부 API로 처리 중...")
        result = _run_openai_turn_from_args(
            args,
            user_input=user_input,
            turn_id=current_turn_id,
            export_dir=export_dir,
            previous_turn_capsules=session_memory.previous_turn_capsules,
            recent_raw_conversation=session_memory.recent_raw_conversation,
        )
        attach_chat_session_snapshot(
            result=result,
            session_memory=session_memory,
            current_turn_id=current_turn_id,
        )
        print(render_pretty_turn(result, user_input=user_input))
        print("")
        store_chat_turn_result(
            session_memory=session_memory,
            current_turn_id=current_turn_id,
            user_input=user_input,
            result=result,
        )


def _run_codex_sdk_chat(args: argparse.Namespace) -> None:
    """ChatGPT 구독 사용량을 쓰는 명시적 비교 대화 모드."""

    print("SongRyeon codex-sdk-chat")
    print("각 송련 노드가 별도 Codex turn을 사용합니다. 종료: /exit 또는 /quit")
    print("")

    session_memory = ChatSessionMemory()
    while True:
        try:
            user_input = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            print("송련> 종료")
            return
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            print("송련> 종료")
            return

        export_dir = _chat_export_dir(args.export, session_memory.turn_index)
        current_turn_id = current_chat_turn_id(session_memory)
        print("송련> Codex SDK로 처리 중...")
        result = _run_codex_sdk_turn_from_args(
            args,
            user_input=user_input,
            turn_id=current_turn_id,
            export_dir=export_dir,
            previous_turn_capsules=session_memory.previous_turn_capsules,
            recent_raw_conversation=session_memory.recent_raw_conversation,
        )
        attach_chat_session_snapshot(
            result=result,
            session_memory=session_memory,
            current_turn_id=current_turn_id,
        )
        print(render_pretty_turn(result, user_input=user_input))
        print("")
        store_chat_turn_result(
            session_memory=session_memory,
            current_turn_id=current_turn_id,
            user_input=user_input,
            result=result,
        )


def _run_hybrid_chat(args: argparse.Namespace) -> None:
    """Qwen 작업 노드와 Codex 판단 노드를 함께 쓰는 대화 모드."""

    print("SongRyeon hybrid-chat")
    print(
        f"작업={args.qwen_model_id} / 판단={args.codex_model_id} / "
        "종료: /exit 또는 /quit"
    )
    print("")

    session_memory = ChatSessionMemory()
    while True:
        try:
            user_input = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            print("송련> 종료")
            return
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            print("송련> 종료")
            return

        export_dir = _chat_export_dir(args.export, session_memory.turn_index)
        current_turn_id = current_chat_turn_id(session_memory)
        print("송련> Qwen 작업 + Codex 판단으로 처리 중...")
        result = _run_hybrid_turn_from_args(
            args,
            user_input=user_input,
            turn_id=current_turn_id,
            export_dir=export_dir,
            previous_turn_capsules=session_memory.previous_turn_capsules,
            recent_raw_conversation=session_memory.recent_raw_conversation,
        )
        attach_chat_session_snapshot(
            result=result,
            session_memory=session_memory,
            current_turn_id=current_turn_id,
        )
        print(render_pretty_turn(result, user_input=user_input))
        print("")
        store_chat_turn_result(
            session_memory=session_memory,
            current_turn_id=current_turn_id,
            user_input=user_input,
            result=result,
        )


def _chat_export_dir(base_export_dir: str | None, turn_index: int) -> str | None:
    # qwen-chat에서 export를 켜면 턴마다 별도 폴더에 실행 기록을 저장한다.
    if base_export_dir is None:
        return None
    return str(Path(base_export_dir) / f"turn_{turn_index:04d}")


#H 나중에 사용자/개발자 용도로 분리해야 하고 개발자 용도는 이 프로젝트에 매우 중요한 기능이므로, 신중하게 인간이 직접 학습하여 꼼꼼히 관리돼야 한다.
def _summary(result: dict[str, object]) -> dict[str, object]:
    # dry-run 결과 중 사람이 빠르게 볼 핵심 숫자만 추린다.
    return {
        "turn_id": result["turn_id"],
        "trace_count": result["trace_count"],
        "data_record_count": result["data_record_count"],
        "mixed_info_count": result.get("mixed_info_count"),
        "movement_count": result["movement_count"],
        "task_frame_count": result.get("task_frame_count"),
        "task_result_count": result.get("task_result_count"),
        "current_route": result["current_route"],
        "capsule_trace_count": result["capsule_trace_count"],
        "llm_call_count": result.get("llm_call_count"),
        "tool_result_count": result.get("tool_result_count"),
        "tool_distillation_count": result.get("tool_distillation_count"),
        "tool_budget_frame_count": result.get("tool_budget_frame_count"),
        "l_loop_budget_plan_count": result.get("l_loop_budget_plan_count"),
        "search_top_k": result.get("search_top_k"),
        "max_query_attempts": result.get("max_query_attempts"),
        "max_document_context_chars": result.get("max_document_context_chars"),
        "l_loop_final_decision": result.get("l_loop_final_decision"),
        "l_loop_final_continuation_status": result.get("l_loop_final_continuation_status"),
        "l_loop_continuation_count": result.get("l_loop_continuation_count"),
        "l_loop_revision_query_count": result.get("l_loop_revision_query_count"),
        "l_loop_run_count": result.get("l_loop_run_count"),
        "same_turn_l_reroute_enabled": result.get("same_turn_l_reroute_enabled"),
        "max_l_runs_per_turn": result.get("max_l_runs_per_turn"),
        "effective_max_l_runs_per_turn": result.get("effective_max_l_runs_per_turn"),
        "same_turn_r_reroute_enabled": result.get("same_turn_r_reroute_enabled"),
        "max_r_runs_per_turn": result.get("max_r_runs_per_turn"),
        "effective_max_r_runs_per_turn": result.get("effective_max_r_runs_per_turn"),
        "vessel_r_run_count": result.get("vessel_r_run_count"),
        "same_turn_rerun_allowed": result.get("same_turn_rerun_allowed"),
        "rerun_block_reason": result.get("rerun_block_reason"),
        "planned_next_step": result.get("planned_next_step"),
        "reroute_controller_decision": result.get("reroute_controller_decision"),
        "reroute_controller_reason": result.get("reroute_controller_reason"),
        "l2_query_source": result.get("l2_query_source"),
        "node1_llm_routing_count": result.get("node1_llm_routing_count"),
        "node1_llm_routing_failed_count": result.get("node1_llm_routing_failed_count"),
        "node1_router_fallback_count": result.get("node1_router_fallback_count"),
        "node1_router_fallback_policy": result.get("node1_router_fallback_policy"),
        "r_route_experimental_enabled": result.get("r_route_experimental_enabled"),
        "r_route_experimental_status": result.get("r_route_experimental_status"),
        "r_route_experimental_return_summary_id": result.get(
            "r_route_experimental_return_summary_id"
        ),
        "r_route_experimental_close_route_id": result.get(
            "r_route_experimental_close_route_id"
        ),
        "recent_memory_relevance_selection_status": result.get(
            "recent_memory_relevance_selection_status"
        ),
        "recent_memory_relevance_selection_candidate_count": result.get(
            "recent_memory_relevance_selection_candidate_count"
        ),
        "recent_memory_relevance_selection_selected_count": result.get(
            "recent_memory_relevance_selection_selected_count"
        ),
        "selected_recent_memory_context_count": result.get(
            "selected_recent_memory_context_count"
        ),
        "missing_selected_memory_context_count": result.get(
            "missing_selected_memory_context_count"
        ),
        "raw_memory_compression_candidate_status": result.get(
            "raw_memory_compression_candidate_status"
        ),
        "raw_memory_compression_candidate_turn_ids": result.get(
            "raw_memory_compression_candidate_turn_ids"
        ),
        "raw_memory_retained_raw_turn_ids": result.get("raw_memory_retained_raw_turn_ids"),
        "older_unmanaged_raw_turn_count": result.get("older_unmanaged_raw_turn_count"),
        "node4_recent_memory_guard_status": result.get(
            "node4_recent_memory_guard_status"
        ),
        "node4_unsupported_recent_memory_claim_count": result.get(
            "node4_unsupported_recent_memory_claim_count"
        ),
        "node2_answer_basis_mode": result.get("node2_answer_basis_mode"),
        "node2_answer_basis_generated_by": result.get("node2_answer_basis_generated_by"),
        "node2_answer_basis_reason_codes": result.get("node2_answer_basis_reason_codes"),
        "node2_answer_basis_semantic_judgement_status": result.get(
            "node2_answer_basis_semantic_judgement_status"
        ),
        "node2_answer_basis_failure_type": result.get("node2_answer_basis_failure_type"),
        "node2_answer_basis_llm_call_data_id": result.get(
            "node2_answer_basis_llm_call_data_id"
        ),
        "node2_answer_basis_trace_event_id": result.get(
            "node2_answer_basis_trace_event_id"
        ),
        "node2_answer_basis_payload_parse_status": result.get(
            "node2_answer_basis_payload_parse_status"
        ),
        "export_dir": result.get("export_dir"),
    }


def _turn_summary(result: dict[str, object], *, include_report: bool) -> dict[str, object]:
    # qwen-turn/fake-turn의 JSON 출력이 너무 길어지지 않도록 report 본문은 기본적으로 preview만 보여준다.
    summary = dict(result)
    report = summary.pop("report", None)
    if isinstance(report, str):
        summary["report_char_count"] = len(report)
        node4_gate_status = summary.get("node4_gate_status")
        report_blocked = node4_gate_status in {"needs_revision", "failed"}
        if report_blocked:
            summary["report_blocked_by_node4"] = True
            summary["report_preview"] = "[blocked: node_4 gatekeeper did not pass this report]"
        else:
            summary["report_preview"] = report[:800]
        if include_report:
            summary["report"] = report
    return summary


def _configure_stdio() -> None:
    """Windows 터미널과 Python 입출력 인코딩을 UTF-8로 맞춘다.

    Python만 UTF-8로 쓰고 Windows 콘솔 코드페이지가 CP949로 남아 있으면
    pretty 출력의 한글이 `?대? 臾몄꽌`처럼 깨져 보일 수 있다.
    """

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    main()
