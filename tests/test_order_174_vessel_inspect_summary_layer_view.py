from __future__ import annotations

import json

from songryeon_core.core.graph_vessel_inspect import inspect_graph_vessel_from_neo4j
from songryeon_core.runtime.graph_vessel_inspect import render_vessel_inspect_text

from tests.test_order_163_vessel_inspect_manual_walk import (
    INSPECTED_AT,
    FakeInspectDriverFactory,
    _config,
)


def test_vessel_inspect_reads_summary_layer_counts_and_samples() -> None:
    result = inspect_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_174_summary_layer",
        created_at=INSPECTED_AT,
        driver_factory=FakeInspectDriverFactory(
            counts={"summary_count": 2},
            summary_rows=_summary_rows(),
        ),
    )

    assert result.inspect_status == "passed"
    assert result.summary_count == 2
    assert result.active_summary_count == 2
    assert result.invalidated_summary_count == 0
    assert result.summary_count_by_data_kind == {
        "source_leaf_summary": 1,
        "token_budget_bundle_summary": 1,
    }
    assert result.summary_count_by_depth == {"1": 1, "2": 1}
    assert len(result.summary_sample_items) == 2
    assert result.summary_sample_items[0]["summary_text_preview"].startswith(
        "Leaf summary for code tool file"
    )
    assert "graph:summary:source_leaf:code_tools" in result.source_data_ids
    assert "graph:raw_source:code_tools" in result.source_data_ids


def test_vessel_inspect_text_renderer_prints_summary_section() -> None:
    result = {
        "status": "VESSEL_INSPECT_OK",
        "inspect_status": "passed",
        "failure_type": None,
        "failure_reason": None,
        "graph_namespace": "songryeon_core_graph_v0",
        "inspected_path_count": 1,
        "summary_count": 2,
        "active_summary_count": 2,
        "invalidated_summary_count": 0,
        "summary_count_by_data_kind": {"source_leaf_summary": 1},
        "summary_count_by_depth": {"1": 1},
        "tree_text": "CoreEgo [graph:core_ego:root]",
        "summary_lines": [
            "Summary samples",
            "  source_leaf_summary(depth=1, info=relative) [graph:summary:source_leaf:code_tools]",
            "    preview: Leaf summary for code tool file.",
        ],
    }

    rendered = render_vessel_inspect_text(result)

    assert "summary_count: 2" in rendered
    assert "summary_count_by_depth: {'1': 1}" in rendered
    assert "Summary samples" in rendered
    assert "Leaf summary for code tool file" in rendered


def _summary_rows() -> list[dict[str, object]]:
    return [
        {
            "summary_data_id": "graph:summary:source_leaf:code_tools",
            "summary_display_name": "Summary: graph:raw_source:code_tools",
            "summary_data_kind": "source_leaf_summary",
            "summary_info_class": "relative",
            "summary_generated_by": "LLM:fake:night_summarize_source_leaf",
            "summary_payload_json": json.dumps(
                {
                    "data_kind": "source_leaf_summary",
                    "summary_depth": 1,
                    "summary_status": "ran",
                    "validity_status": "active",
                    "review_status": "not_reviewed",
                    "target_graph_node_id": "graph:raw_source:code_tools",
                    "target_node_kind": "raw_source",
                    "source_leaf_count": 1,
                    "source_summary_count": 0,
                    "info_class": "relative",
                    "generated_by": "LLM:fake:night_summarize_source_leaf",
                    "summary_text": "Leaf summary for code tool file.",
                },
                ensure_ascii=False,
            ),
            "target_graph_node_id": "graph:raw_source:code_tools",
            "target_display_name": "Raw Source: code_tools.py",
            "target_node_kind": "raw_source",
        },
        {
            "summary_data_id": "graph:summary:token_bundle:001",
            "summary_display_name": "Summary: graph:token_budget_bundle:001",
            "summary_data_kind": "token_budget_bundle_summary",
            "summary_info_class": "mixed",
            "summary_generated_by": "LLM:fake:night_summarize_token_budget_bundle",
            "summary_payload_json": json.dumps(
                {
                    "data_kind": "token_budget_bundle_summary",
                    "summary_depth": 2,
                    "summary_status": "ran",
                    "validity_status": "active",
                    "review_status": "not_reviewed",
                    "target_graph_node_id": "graph:token_budget_bundle:001",
                    "target_node_kind": "token_budget_summary_bundle",
                    "source_leaf_count": 8,
                    "source_summary_count": 8,
                    "info_class": "mixed",
                    "generated_by": "LLM:fake:night_summarize_token_budget_bundle",
                    "summary_text": "Layer summary over eight source leaf summaries.",
                },
                ensure_ascii=False,
            ),
            "target_graph_node_id": "graph:token_budget_bundle:001",
            "target_display_name": "Token Budget Bundle 001",
            "target_node_kind": "token_budget_summary_bundle",
        },
    ]
