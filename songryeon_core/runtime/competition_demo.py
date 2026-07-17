from __future__ import annotations

from typing import Any

from songryeon_core.llm.fake import (
    BrokenJSONFakeLLMAdapter,
    SongRyeonAllNodesFakeLLMAdapter,
)
from songryeon_core.runtime.defaults import DEFAULT_MAX_READ_DOC_CALLS
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_chat_answer


COMPETITION_DEMO_USER_INPUT = "내부 문서에서 송련의 근거 처리 방식을 확인해줘"


class CompetitionRoleMismatchAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """LLM 판정 뒤의 CODE guard를 재현하는 결정론적 대회 시연 adapter.

    이 adapter는 실제 모델 품질을 흉내 내지 않는다. 검색 후보 문서를 실제로 읽은
    문서라고 잘못 주장하고, LLM gate 판단은 의도적으로 pass를 반환한다. 그 뒤
    Node 4의 CODE guard가 이 명시적 역할 충돌을 잡는지 확인하는 테스트 더블이다.
    """

    model_id = "competition-role-mismatch-adapter"

    def _node_2_answer_basis_payload(self, request):  # type: ignore[override]
        payload = super()._node_2_answer_basis_payload(request)
        sources = request.input_payload.get("available_evidence_sources")
        if not isinstance(sources, list):
            return payload
        document_ledger = next(
            (
                source
                for source in sources
                if isinstance(source, dict)
                and source.get("source_kind") == "document_material_packet"
            ),
            None,
        )
        if not isinstance(document_ledger, dict):
            return payload
        evidence_ref = document_ledger.get("evidence_ref")
        if not isinstance(evidence_ref, str) or not evidence_ref:
            return payload
        payload["evidence_roles"] = [
            {
                "evidence_ref": evidence_ref,
                "evidence_role": "primary_answer_basis",
                "role_reason": "대회 시연용 문서 역할 장부를 선택했다.",
                "role_reason_info_class": "relative",
            }
        ]
        return payload

    def _node_3_payload(self, request):  # type: ignore[override]
        packet = request.input_payload.get("document_material_packet")
        items = packet.get("items") if isinstance(packet, dict) else None
        if not isinstance(items, list):
            return super()._node_3_payload(request)
        unread = next(
            (
                item
                for item in items
                if isinstance(item, dict)
                and item.get("was_unread_candidate") is True
                and item.get("was_actual_tool_read_doc") is not True
            ),
            None,
        )
        if not isinstance(unread, dict):
            return super()._node_3_payload(request)
        document_name = str(unread.get("document_name") or "읽지 않은 후보 문서")
        return {
            "body_markdown": (
                f"`{document_name}`는 actual_tool_read_doc으로 읽힌 문서다."
            )
        }

    def _node_4_payload(self, request):  # type: ignore[override]
        _ = request
        return {
            "gate_status": "pass",
            "reason": "시연용 LLM 판정은 이 주장을 의도적으로 통과시켰다.",
            "checked_claims": [],
            "unsupported_claims": [],
            "contradictions": [],
            "revision_targets": [],
            "task_fulfillment_status": "fulfilled",
            "grounding_consistency_status": "consistent",
            "task_failure_reasons": [],
        }


def run_competition_demo() -> dict[str, object]:
    """외부 API와 Neo4j 없이 세 가지 신뢰 경계를 한 번에 검증한다."""

    ordinary_adapter = SongRyeonAllNodesFakeLLMAdapter()
    local_result = _run_with_adapters(
        user_input="송련이 뭔지 짧게 설명해줘",
        adapter=ordinary_adapter,
    )
    fallback_result = _run_with_adapters(
        user_input=COMPETITION_DEMO_USER_INPUT,
        adapter=ordinary_adapter,
        node_2_boundary_adapter=BrokenJSONFakeLLMAdapter(),
        force_l_route=True,
    )
    mismatch_adapter = CompetitionRoleMismatchAdapter()
    guard_result = _run_with_adapters(
        user_input=COMPETITION_DEMO_USER_INPUT,
        adapter=mismatch_adapter,
        force_l_route=True,
        search_top_k=5,
        max_read_doc_calls=2,
    )

    gate = _latest_payload(guard_result, "node_output:node4_gatekeeper_frame")
    material_packet = _latest_payload(
        guard_result,
        "node_output:node0_document_material_packet_frame",
    )
    first_contradiction = _first_string(gate.get("contradictions"))
    guard_answer = render_chat_answer(
        guard_result,
        user_input=COMPETITION_DEMO_USER_INPUT,
    )
    public_answer = (
        "blocked"
        if "FINAL_BLOCKED_BY_GATEKEEPER" in guard_answer
        else "released"
    )

    scenarios = {
        "local_path": {
            "passed": local_result.get("node4_gate_status") == "pass",
            "external_api_calls": 0,
            "neo4j_connections": 0,
            "trace_count": local_result.get("trace_count"),
            "data_record_count": local_result.get("data_record_count"),
            "final_gate": local_result.get("node4_gate_status"),
        },
        "honest_fallback": {
            "passed": (
                fallback_result.get("node2_answer_basis_generated_by")
                == "CODE:FALLBACK"
                and fallback_result.get("node2_answer_basis_semantic_judgement_status")
                == "failed"
            ),
            "model_output": "invalid_json",
            "generated_by": fallback_result.get("node2_answer_basis_generated_by"),
            "semantic_judgement_status": fallback_result.get(
                "node2_answer_basis_semantic_judgement_status"
            ),
            "failure_type": fallback_result.get("node2_answer_basis_failure_type"),
        },
        "code_guard": {
            "passed": (
                _int(material_packet.get("unread_candidate_count")) > 0
                and gate.get("gate_status") == "needs_revision"
                and "CODE:DOCUMENT_EVIDENCE_ROLE_GUARD"
                in str(gate.get("gate_generation_source") or "")
                and first_contradiction.startswith(
                    "read_doc_claim_without_actual_tool_read_doc:"
                )
                and public_answer == "blocked"
            ),
            "controlled_llm_decision": "pass",
            "llm_gate_execution": gate.get("llm_gate_status"),
            "final_gate": gate.get("gate_status"),
            "generated_by": gate.get("gate_generation_source"),
            "contradiction": first_contradiction,
            "search_candidate_count": _int(
                material_packet.get("search_candidate_count")
            ),
            "actual_tool_read_doc_count": _int(
                material_packet.get("actual_tool_read_doc_count")
            ),
            "unread_candidate_count": _int(
                material_packet.get("unread_candidate_count")
            ),
            "guard_scope": "explicit_document_evidence_role_conflict_only",
            "public_answer": public_answer,
            "blocking_renderer_marker_present": (
                "FINAL_BLOCKED_BY_GATEKEEPER" in guard_answer
            ),
        },
    }
    passed = all(
        isinstance(scenario, dict) and scenario.get("passed") is True
        for scenario in scenarios.values()
    )
    return {
        "status": "SONGRYEON_COMPETITION_DEMO_OK" if passed else "SONGRYEON_COMPETITION_DEMO_FAILED",
        "passed": passed,
        "scope": "deterministic_test_harness",
        "external_api_calls": 0,
        "neo4j_connections": 0,
        "scenarios": scenarios,
    }


def render_competition_demo(result: dict[str, object]) -> str:
    """심사 화면 한 장에 들어가는 대회용 요약을 만든다."""

    scenarios = result.get("scenarios")
    if not isinstance(scenarios, dict):
        scenarios = {}
    local = _dict(scenarios.get("local_path"))
    fallback = _dict(scenarios.get("honest_fallback"))
    guard = _dict(scenarios.get("code_guard"))
    lines = [
        "SongRyeon Core — 감사 가능한 로컬 조사 에이전트",
        "작은 모델의 답을 그대로 믿지 않고, 무엇을 읽었는지 CODE가 다시 확인합니다.",
        "",
        _scenario_heading(1, "LOCAL", local),
        "  외부 API 0회 · Neo4j 0회 · 전체 노드 경로 완료",
        f"  trace/data={local.get('trace_count', 0)}/{local.get('data_record_count', 0)} · 최종 판정={local.get('final_gate', 'unknown')}",
        "",
        _scenario_heading(2, "HONEST FALLBACK", fallback),
        "  모델 출력=깨진 JSON",
        (
            "  기록="
            f"{fallback.get('generated_by', 'unknown')} · "
            f"semantic={fallback.get('semantic_judgement_status', 'unknown')} · "
            f"failure={fallback.get('failure_type', 'unknown')}"
        ),
        "",
        _scenario_heading(3, "CODE GUARD", guard),
        (
            "  후보="
            f"{guard.get('search_candidate_count', 0)} · "
            f"실제 read_doc={guard.get('actual_tool_read_doc_count', 0)} · "
            f"미열람 후보={guard.get('unread_candidate_count', 0)}"
        ),
        "  통제된 모델 판정=pass · CODE 확인=미열람 후보를 읽었다고 잘못 주장",
        f"  최종 판정={guard.get('final_gate', 'unknown')} · 사용자 공개={guard.get('public_answer', 'unknown')}",
        f"  충돌={guard.get('contradiction', 'none')}",
        "",
        "※ 실제 모델 성능 비교가 아니라, 실패·출처·차단 경계를 재현하는 결정론적 테스트입니다.",
        str(result.get("status") or "SONGRYEON_COMPETITION_DEMO_FAILED"),
    ]
    return "\n".join(lines)


def _run_with_adapters(
    *,
    user_input: str,
    adapter: SongRyeonAllNodesFakeLLMAdapter,
    node_2_boundary_adapter: Any | None = None,
    force_l_route: bool = False,
    search_top_k: int = 3,
    max_read_doc_calls: int = DEFAULT_MAX_READ_DOC_CALLS,
) -> dict[str, object]:
    return run_dry_turn(
        user_input=user_input,
        node_1_router_adapter=adapter,
        memory_relevance_selector_adapter=adapter,
        l1_goal_adapter=adapter,
        l_tool_scope_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=node_2_boundary_adapter or adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        force_l_route=force_l_route,
        search_top_k=search_top_k,
        max_read_doc_calls=max_read_doc_calls,
    )


def _latest_payload(result: dict[str, object], data_type: str) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}
    for record in reversed(records):
        if not isinstance(record, dict) or record.get("data_type") != data_type:
            continue
        payload = record.get("payload")
        return payload if isinstance(payload, dict) else {}
    return {}


def _first_string(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return next((item for item in value if isinstance(item, str)), "")


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _scenario_heading(index: int, label: str, scenario: dict[str, object]) -> str:
    status = "PASS" if scenario.get("passed") is True else "FAIL"
    return f"[{index}/3 {label}] {status}"
