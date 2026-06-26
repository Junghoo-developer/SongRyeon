from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.l_loop_smoke import run_qwen_l_loop_smoke
from songryeon_core.runtime.replay import replay_run
from songryeon_core.runtime.smoke_test import run_smoke_tests
from songryeon_core.runtime.terminal_view import render_pretty_turn
from songryeon_core.runtime.user_turn import run_fake_user_turn, run_qwen_user_turn
from songryeon_core.runtime.defaults import (
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_QUERY_ATTEMPTS,
    DEFAULT_MAX_READ_DOC_CALLS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_SEARCH_TOP_K,
)
from songryeon_core.llm.runtime import ping_qwen
from songryeon_core.tools.document_tools import search_docs


def main() -> None:
    # 이 파일은 SongRyeon Core의 CLI 입구다.
    # 사용자가 `python main.py qwen-chat`처럼 명령을 치면 여기서 명령을 해석하고
    # 실제 작업은 runtime/nodes/tools 모듈에 넘긴다.
    _configure_stdio()

    # argparse는 "터미널 명령어를 파이썬 함수 호출로 바꾸는 장치"라고 보면 된다.
    # subparser 하나가 CLI 명령 하나에 대응한다.
    parser = argparse.ArgumentParser(prog="songryeon-core")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # dry-run은 Qwen 없이도 한 턴 실행 구조와 trace/data가 살아있는지 보는 기본 점검이다.
    dry_run_parser = subparsers.add_parser("dry-run")
    dry_run_parser.add_argument("--export", default=None)
    dry_run_parser.add_argument("--same-turn-l-reroute", action="store_true")
    dry_run_parser.add_argument("--max-l-runs-per-turn", type=int, default=1)

    # search-docs는 L루프 전체를 돌리지 않고 문서 검색 도구만 직접 확인할 때 쓴다.
    # qwen-chat은 송련 전체를 돌려보는 모드이고, search-docs는 문서 검색 엔진만 따로 뜯어보는 모드다.
    # 따라서 "송련이 못 찾은 것인지, 검색 도구가 못 찾은 것인지"를 분리해서 진단할 때 중요하다.
    search_parser = subparsers.add_parser("search-docs")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=3)

    # show-orders는 현재 발주서 목록을 빠르게 훑기 위한 작은 보조 명령이다.
    subparsers.add_parser("show-orders")

    # replay는 export로 저장한 실행 기록을 다시 읽을 때 쓴다.
    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("run_dir")

    # qwen-ping은 로컬 Qwen/Ollama 연결이 살아있는지 확인하는 가장 작은 LLM 호출이다.
    qwen_ping_parser = subparsers.add_parser("qwen-ping")
    qwen_ping_parser.add_argument("--endpoint", default=None)
    qwen_ping_parser.add_argument("--model-id", default=None)
    qwen_ping_parser.add_argument("--timeout", type=int, default=None)

    # qwen-l-loop-smoke는 Qwen이 붙은 L루프만 좁게 점검한다.
    qwen_l_loop_parser = subparsers.add_parser("qwen-l-loop-smoke")
    qwen_l_loop_parser.add_argument("--endpoint", default=None)
    qwen_l_loop_parser.add_argument("--model-id", default=None)
    qwen_l_loop_parser.add_argument("--timeout", type=int, default=None)
    qwen_l_loop_parser.add_argument("--export", default=None)

    # fake-turn은 가짜 LLM adapter로 한 턴을 돌린다. 구조 회귀 테스트에 가깝다.
    fake_turn_parser = subparsers.add_parser("fake-turn")
    fake_turn_parser.add_argument("user_input")
    _add_turn_runtime_args(fake_turn_parser, include_qwen_args=False)

    # qwen-turn은 사용자 입력 하나를 Qwen 기반 한 턴으로 실행한다.
    qwen_turn_parser = subparsers.add_parser("qwen-turn")
    qwen_turn_parser.add_argument("user_input")
    _add_turn_runtime_args(qwen_turn_parser, include_qwen_args=True)

    # qwen-chat은 qwen-turn을 반복 호출하는 대화형 껍데기다.
    # 현재는 각 입력이 독립 턴에 가깝고, 직전 대화를 풍부하게 기억하지 않는다.
    qwen_chat_parser = subparsers.add_parser("qwen-chat")
    _add_turn_runtime_args(qwen_chat_parser, include_qwen_args=True)

    # smoke-test는 "지금 기준선이 깨졌는가?"를 빠르게 확인하는 자동 점검이다.
    subparsers.add_parser("smoke-test")

    args = parser.parse_args()

    # 여기부터는 실제 실행 분기다.
    # args.command 값에 따라 위에서 등록한 명령이 runtime 함수로 연결된다.
    if args.command == "dry-run":
        result = run_dry_turn(
            export_dir=args.export,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
        )
        print("DRY_RUN_OK")
        print(json.dumps(_summary(result), ensure_ascii=False, indent=2))
    elif args.command == "search-docs":
        result = search_docs(root="Administrative_Reform_1", query=args.query, top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "show-orders":
        for path in sorted(Path("Administrative_Reform_1/04_Orders").glob("*.md")):
            print(path.as_posix())
    elif args.command == "replay":
        print(replay_run(args.run_dir))
    elif args.command == "qwen-ping":
        result = ping_qwen(
            endpoint=args.endpoint,
            model_id=args.model_id,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
            include_data_records=args.pretty,
            force_l_route=args.force_l,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
        )
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
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
            include_data_records=args.pretty,
            force_l_route=args.force_l,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
        )
        if args.pretty:
            print(render_pretty_turn(result, user_input=args.user_input))
        else:
            print(json.dumps(_turn_summary(result, include_report=args.include_report), ensure_ascii=False, indent=2))
    elif args.command == "qwen-chat":
        _run_qwen_chat(args)
    elif args.command == "smoke-test":
        print(json.dumps(run_smoke_tests(), ensure_ascii=False, indent=2))


def _add_turn_runtime_args(parser: argparse.ArgumentParser, *, include_qwen_args: bool) -> None:
    # fake-turn/qwen-turn/qwen-chat이 공유하는 실행 옵션을 한 곳에서 붙인다.
    # 이렇게 해두면 max_tool_calls 같은 기본값을 명령마다 따로 고치지 않아도 된다.
    parser.add_argument("--export", default=None)
    parser.add_argument("--include-report", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--max-tool-calls", type=int, default=DEFAULT_MAX_TOOL_CALLS)
    parser.add_argument("--search-top-k", type=int, default=DEFAULT_SEARCH_TOP_K)
    parser.add_argument("--max-query-attempts", type=int, default=DEFAULT_MAX_QUERY_ATTEMPTS)
    parser.add_argument("--max-query-candidates", type=int, default=None)
    parser.add_argument("--max-read-doc-calls", type=int, default=DEFAULT_MAX_READ_DOC_CALLS)
    parser.add_argument("--max-input-chars", type=int, default=DEFAULT_MAX_INPUT_CHARS)
    parser.add_argument("--force-l", action="store_true")
    parser.add_argument("--same-turn-l-reroute", action="store_true")
    parser.add_argument("--max-l-runs-per-turn", type=int, default=1)
    if include_qwen_args:
        parser.add_argument("--endpoint", default=None)
        parser.add_argument("--model-id", default=None)
        parser.add_argument("--timeout", type=int, default=None)


def _run_qwen_chat(args: argparse.Namespace) -> None:
    # 대화형 모드다. 사용자가 /exit 또는 /quit을 입력할 때까지 반복한다.
    # 주의: 지금 구조에서는 매 입력마다 run_qwen_user_turn을 새로 호출하므로
    # "아까 2번" 같은 직전 대화 참조는 아직 약하다.
    #H 따라서 차후 0의 기억과 다른 노드의 기억 패킷을 학습하고 이에 연동하여 최적의 공용 기억에 최근 대화랑 이전 작업 기억을 각 노드별로 나눠서 적절히 배분하는 방안이 필요하다.
    #H llm의 시야를 다루는 관점과는 달리, 송련은 본점의 헌법 문서에 명시돼 있듯 주요 구성 요소 중 하나가 데이터이기에, 코드랑 시스템은 노드별로 분산하여 배분되는 기억과 무관하게 통합적으로 관리할 체계가 필요하다.
    #H 장기기억과 DB는 본점의 노하우를 참조하면 시간 절약 및 효율적인 관리가 가능하다.
    print("SongRyeon qwen-chat")
    print("종료하려면 /exit 또는 /quit 입력")
    print("")

    turn_index = 1
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

        export_dir = _chat_export_dir(args.export, turn_index)
        print("송련> 처리 중...")
        # 실제 한 턴 실행은 runtime/user_turn.py로 넘어간다.
        # main.py는 입력값과 옵션을 모아서 넘기는 얇은 연결부로 남기는 것이 좋다.
        result = run_qwen_user_turn(
            user_input=user_input,
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
            include_data_records=True,
            force_l_route=args.force_l,
            same_turn_l_reroute_enabled=args.same_turn_l_reroute,
            max_l_runs_per_turn=args.max_l_runs_per_turn,
        )
        print(render_pretty_turn(result, user_input=user_input))
        print("")
        turn_index += 1


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
        "l_loop_final_decision": result.get("l_loop_final_decision"),
        "l_loop_final_continuation_status": result.get("l_loop_final_continuation_status"),
        "l_loop_continuation_count": result.get("l_loop_continuation_count"),
        "l_loop_revision_query_count": result.get("l_loop_revision_query_count"),
        "l_loop_run_count": result.get("l_loop_run_count"),
        "same_turn_l_reroute_enabled": result.get("same_turn_l_reroute_enabled"),
        "max_l_runs_per_turn": result.get("max_l_runs_per_turn"),
        "effective_max_l_runs_per_turn": result.get("effective_max_l_runs_per_turn"),
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
