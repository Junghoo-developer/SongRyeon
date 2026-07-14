from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import L3PreservedInfoFrame, Node3InputBriefFrame
from songryeon_core.nodes.l3_result_keeper import (
    _apply_goal_match_guard,
    _build_goal_match_context,
)
from songryeon_core.nodes.node_1_router import _route_capability_cards
from songryeon_core.nodes.node_3_reporter import assemble_node3_report_markdown
from songryeon_core.nodes.node_4_gatekeeper import _grounding_count_violations
from songryeon_core.tools.document_context_pack import (
    build_explicit_artifact_reference_frame,
    extract_explicit_artifact_references,
)


def test_node1_r_card_exposes_ingested_rawsource_original_text_boundary() -> None:
    cards = _route_capability_cards(
        allow_r_route_experimental=True,
        r_execution_mode="vessel_live",
    )
    by_route = {str(card["route"]): card for card in cards}

    r_card = by_route["R"]
    l_card = by_route["L"]

    assert "RawSource" in str(r_card["raw_source_original_text_access"])
    assert "already-ingested" in " ".join(str(item) for item in r_card["best_for"])
    assert "newer on-disk version" in str(r_card["freshness_boundary"])
    assert "not already ingested" in " ".join(str(item) for item in l_card["best_for"])


def test_order_space_reference_resolves_to_existing_order_file(tmp_path: Path) -> None:
    order_dir = tmp_path / "Administrative_Reform_1" / "04_Orders"
    order_dir.mkdir(parents=True)
    target = order_dir / "ORDER_090_L_LOOP_BUDGET_PLAN_V0.md"
    target.write_text("# ORDER 090\n\n예산 계획 원문", encoding="utf-8")

    assert extract_explicit_artifact_references("ORDER 090 문서를 읽어줘") == ["ORDER 090"]

    frame = build_explicit_artifact_reference_frame(
        turn_id="turn_order_243",
        user_text="ORDER 090 문서를 읽어줘",
        document_root=tmp_path,
        frame_id="L:explicit_artifact_reference_frame",
        source_trace_ids=["trace:user"],
        source_data_ids=["data:user"],
    )

    assert frame.unique_count == 1
    assert frame.resolved_references[0].raw_ref == "ORDER 090"
    assert frame.resolved_references[0].normalized_ref == "order_090"
    assert frame.resolved_references[0].selected_doc_id == (
        "Administrative_Reform_1/04_Orders/ORDER_090_L_LOOP_BUDGET_PLAN_V0.md"
    )


def test_l3_uses_explicit_resolver_id_and_downgrades_unrelated_read() -> None:
    data_store = DataStore()
    explicit_frame = build_explicit_artifact_reference_frame(
        turn_id="turn_order_243",
        user_text="ORDER 090 문서를 읽어줘",
        document_root=Path.cwd(),
        frame_id="L:explicit_artifact_reference_frame",
        source_trace_ids=["trace:user"],
        source_data_ids=["data:user"],
    )
    data_store.create_record(
        data_id=explicit_frame.frame_id,
        data_type="node_output:explicit_artifact_reference_frame",
        payload=asdict(explicit_frame),
    )
    data_store.create_record(
        data_id="tool_result:read_doc:unrelated",
        data_type="tool_result:read_doc",
        payload={"doc_id": "04_Orders/README.md", "text": "unrelated"},
    )

    goal_match = _build_goal_match_context(
        user_query="ORDER 090 문서를 설명해줘",
        preserved_frame=L3PreservedInfoFrame(frame_id="L:preserved", turn_id="turn_order_243"),
        data_store=data_store,
    )

    assert goal_match["requested_doc_hint_source"] == "explicit_artifact_reference_frame"
    assert goal_match["requested_doc_hint"] == (
        "Administrative_Reform_1/04_Orders/ORDER_090_L_LOOP_BUDGET_PLAN_V0.md"
    )
    assert goal_match["goal_match_status"] == "partial"

    guarded = _apply_goal_match_guard(
        achievement_status="achieved",
        reason="LLM claimed success",
        macro_status="achieved",
        macro_reason="LLM claimed macro success",
        micro_status="achieved",
        micro_reason="LLM claimed micro success",
        goal_match=goal_match,
    )
    assert guarded[0] == "partial"
    assert guarded[2] == "partial"
    assert guarded[4] == "partial"


def test_node3_strips_accidental_grounding_block_from_middle_of_body() -> None:
    brief = _brief()

    rendered = assemble_node3_report_markdown(
        brief_frame=brief,
        body_markdown=(
            "도입 문장이다.\n\n"
            "**근거 기준:**\n"
            "- 실제 read_doc 도구 원문 읽기: 99개\n\n"
            "의미 본문은 남는다."
        ),
    )

    assert rendered.count("근거 기준:") == 1
    assert "99개" not in rendered
    assert "도입 문장이다." in rendered
    assert "의미 본문은 남는다." in rendered


def test_node4_rejects_duplicate_grounding_heading() -> None:
    brief = _brief()
    rendered = assemble_node3_report_markdown(
        brief_frame=brief,
        body_markdown="정상 본문이다.",
    )
    rendered += "\n\n**근거 기준:**\n- 실제 read_doc 도구 원문 읽기: 0개"

    violations = _grounding_count_violations(
        rendered_markdown=rendered,
        brief_frame=brief,
    )

    assert "grounding_block_heading_count:2_expected_1" in violations


def _brief() -> Node3InputBriefFrame:
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_243",
        user_question="ORDER 090을 설명해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        source_data_ids=["node_2:handoff_frame"],
    )
