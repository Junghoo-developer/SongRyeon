import json

import pytest

from songryeon_core.core.r_loop_vessel_read_packet import (
    R_LOOP_VESSEL_SOURCE_TEXT_RESOLUTION_POLICY_ID,
    build_r_loop_vessel_read_packet_from_neo4j,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    _candidate_records_by_id,
    _has_raw_original_text_material,
    _r3_selected_candidate_record_view,
    _selected_candidate_record,
    _validate_r3_payload,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeResult,
    FakeRLoopVesselDriver,
    FakeRLoopVesselSession,
    FakeRLoopVesselTransaction,
    _config,
)
from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
    _time_bundle_row,
)
from tests.test_order_188_r_vessel_raw_original_cap import _raw_source_chain_row
from tests.test_order_233_r_source_leaf_exact_raw_resolution import (
    RAW_ID,
    SUMMARY_ID,
    _source_leaf_summary_row,
)


SOURCE_TEXT_ID = "source_text:internal_document:order_234"
SOURCE_TEXT = "ORDER 234가 R3에 공급해야 하는 실제 원문이다."


def test_exact_source_text_is_copied_only_into_selected_raw_record() -> None:
    raw_row = _raw_source_chain_row(
        raw_id=RAW_ID,
        next_raw_id=None,
        parent_id="graph:source_kind_bundle:order_234",
    )
    raw_payload = json.loads(str(raw_row["payload_json"]))
    raw_payload["source_data_ids"] = [SOURCE_TEXT_ID]
    raw_row["payload_json"] = json.dumps(raw_payload, ensure_ascii=False)

    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_234_source_text",
        created_at=READ_AT,
        limit=3,
        driver_factory=_SourceTextDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[]),
                _time_bundle_row(),
                raw_row,
            ],
            summary_rows=[_source_leaf_summary_row(RAW_ID)],
            source_text_rows=[_source_text_row()],
        ),
    )

    assert packet.source_text_resolution_policy_id == (
        R_LOOP_VESSEL_SOURCE_TEXT_RESOLUTION_POLICY_ID
    )
    assert packet.source_text_target_data_ids == [SOURCE_TEXT_ID]
    assert packet.source_text_resolved_data_ids == [SOURCE_TEXT_ID]
    assert packet.source_text_missing_data_ids == []

    selected_raw = _selected_candidate_record(packet, RAW_ID)
    assert selected_raw["raw_original_text_status"] == "available"
    assert selected_raw["raw_original_text_data_ids"] == [SOURCE_TEXT_ID]
    assert selected_raw["raw_original_text_char_count"] == len(SOURCE_TEXT)
    assert selected_raw["raw_original_text_materials"][0]["text"] == SOURCE_TEXT
    assert _has_raw_original_text_material(selected_raw) is True

    r3_view = _r3_selected_candidate_record_view(selected_raw)
    assert r3_view["raw_original_text_materials"][0]["text"] == SOURCE_TEXT

    r2_metadata_view = _candidate_records_by_id(packet)[RAW_ID]
    assert "raw_original_text_materials" not in r2_metadata_view
    assert SOURCE_TEXT not in json.dumps(r2_metadata_view, ensure_ascii=False)


def test_raw_source_does_not_treat_its_derived_summary_as_lower_child() -> None:
    raw_row = _raw_source_chain_row(
        raw_id=RAW_ID,
        next_raw_id=None,
        parent_id="graph:source_kind_bundle:order_234",
    )
    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_234_hierarchy_direction",
        created_at=READ_AT,
        limit=4,
        driver_factory=_SourceTextDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[]),
                _time_bundle_row(),
                raw_row,
            ],
            summary_rows=[_source_leaf_summary_row(RAW_ID)],
            source_text_rows=[],
        ),
    )

    selected_summary = _selected_candidate_record(packet, SUMMARY_ID)
    assert selected_summary["hierarchy_child_node_ids"] == [RAW_ID]

    selected_raw = _selected_candidate_record(packet, RAW_ID)
    assert selected_raw["hierarchy_child_node_ids"] == []
    assert selected_raw["hierarchy_child_candidate_records"] == []


def test_r3_rejects_deeper_without_child_and_non_raw_label_for_original_text() -> None:
    input_contract = {
        "hierarchy_child_candidate_count": 0,
        "selected_candidate_record": {
            "node_kind": "raw_source",
            "raw_original_text_status": "available",
            "raw_original_text_char_count": len(SOURCE_TEXT),
        },
    }
    base_payload = {
        "current_information_granularity": "raw",
        "sufficiency_status": "sufficient",
        "granularity_problem_status": "none",
        "branch_problem_status": "none",
        "recommended_next_action": "stop",
        "inspection_reason": "The supplied original text answers the goal.",
    }
    _validate_r3_payload(base_payload, input_contract_payload=input_contract)

    with pytest.raises(ValueError, match="actionable child"):
        _validate_r3_payload(
            {**base_payload, "recommended_next_action": "deeper"},
            input_contract_payload=input_contract,
        )
    with pytest.raises(ValueError, match="must be raw"):
        _validate_r3_payload(
            {**base_payload, "current_information_granularity": "low_summary"},
            input_contract_payload=input_contract,
        )


def _source_text_row() -> dict[str, object]:
    return {
        "source_text_data_id": SOURCE_TEXT_ID,
        "payload_json": json.dumps(
            {
                "text": SOURCE_TEXT,
                "path": "Administrative_Reform_1/04_Orders/ORDER_234.md",
                "source_kind": "internal_document",
                "generated_by": "CODE:SOURCE_INGEST",
                "info_class": "absolute",
                "semantic_judgement_status": "not_run",
            },
            ensure_ascii=False,
        ),
    }


class _SourceTextDriverFactory:
    def __init__(
        self,
        *,
        entry_rows: list[dict[str, object]],
        summary_rows: list[dict[str, object]],
        source_text_rows: list[dict[str, object]],
    ) -> None:
        self.entry_rows = entry_rows
        self.summary_rows = summary_rows
        self.source_text_rows = source_text_rows

    def __call__(self, uri: str, *, auth: object) -> "_SourceTextDriver":
        return _SourceTextDriver(
            entry_rows=self.entry_rows,
            summary_rows=self.summary_rows,
            source_text_rows=self.source_text_rows,
        )


class _SourceTextDriver(FakeRLoopVesselDriver):
    def __init__(
        self,
        *,
        entry_rows: list[dict[str, object]],
        summary_rows: list[dict[str, object]],
        source_text_rows: list[dict[str, object]],
    ) -> None:
        super().__init__(entry_rows=entry_rows, summary_rows=summary_rows)
        self.source_text_rows = source_text_rows

    def session(self, *, database: str) -> "_SourceTextSession":
        return _SourceTextSession(self, database=database)


class _SourceTextSession(FakeRLoopVesselSession):
    def execute_read(self, fn, *args):
        return fn(_SourceTextTransaction(self.driver), *args)


class _SourceTextTransaction(FakeRLoopVesselTransaction):
    def run(self, query: str, **kwargs):
        compact = " ".join(query.split())
        if "MATCH (source:GraphMemorySource" in compact:
            requested = set(kwargs.get("source_text_data_ids") or [])
            rows = [
                row
                for row in self.driver.source_text_rows
                if row.get("source_text_data_id") in requested
            ]
            return FakeResult(rows)
        return super().run(query, **kwargs)
