from __future__ import annotations

from songryeon_core.night_government.runtime import (
    ingest_memory_record,
    load_active_memory_packet,
    render_active_memory_packet_markdown,
    run_night_government,
)
from songryeon_core.night_government.store import NightGovernmentStore


def test_night_government_preserves_records_and_builds_active_packet(tmp_path) -> None:
    db_dir = tmp_path / "night_db"

    ingest_memory_record(
        db_dir=db_dir,
        record_id="mem_fact_001",
        text="node_4 blocks count mismatch reports.",
        memory_role="fact",
        confidence_label="verified",
        human_review_status="human_approved",
        tags=["node4"],
    )
    ingest_memory_record(
        db_dir=db_dir,
        record_id="mem_failure_001",
        text="A broad one-shot implementation caused project control loss.",
        memory_role="failure",
        tags=["process"],
    )
    ingest_memory_record(
        db_dir=db_dir,
        record_id="mem_hypothesis_001",
        text="A nightly external packet may help the next coding session.",
        memory_role="hypothesis",
        tags=["night-government"],
    )
    ingest_memory_record(
        db_dir=db_dir,
        record_id="mem_association_001",
        text="False memories can still work as warning material.",
        memory_role="association",
        tags=["memory"],
    )

    result = run_night_government(
        db_dir=db_dir,
        day_id="2026-06-30",
        active_goal="prepare next coding session",
    )

    assert result["status"] == "NIGHT_GOVERNMENT_OK"
    assert result["input_record_count"] == 4
    assert result["active_memory_item_count"] == 4
    assert result["role_counts"]["fact"] == 1
    assert result["role_counts"]["failure"] == 1
    assert result["role_counts"]["hypothesis"] == 1
    assert result["role_counts"]["association"] == 1

    active_packet = load_active_memory_packet(db_dir=db_dir)
    assert active_packet is not None
    assert active_packet["active_goal"] == "prepare next coding session"

    items = {
        item["source_record_id"]: item
        for item in active_packet["active_memory_items"]
    }
    assert items["mem_fact_001"]["use_as"] == "fact"
    assert items["mem_failure_001"]["use_as"] == "warning"
    assert items["mem_hypothesis_001"]["use_as"] == "hypothesis"
    assert items["mem_association_001"]["use_as"] == "association"
    assert "not_current_fact" in items["mem_failure_001"]["activation_reason"]

    store = NightGovernmentStore(db_dir)
    assert len(store.list_records()) == 4
    assert len(store.list_packets()) == 1

    rendered = render_active_memory_packet_markdown(active_packet)
    assert "Active Memory Packet" in rendered
    assert "mem_failure_001" in rendered


def test_night_government_selection_keeps_role_diversity(tmp_path) -> None:
    db_dir = tmp_path / "night_db"

    for index in range(1, 6):
        ingest_memory_record(
            db_dir=db_dir,
            record_id=f"mem_fact_{index:03d}",
            text=f"verified fact {index}",
            memory_role="fact",
            confidence_label="verified",
            created_at=f"2026-06-30T10:0{index}:00+00:00",
        )
    ingest_memory_record(
        db_dir=db_dir,
        record_id="mem_failure_001",
        text="old failure must not be crowded out by facts",
        memory_role="failure",
        created_at="2026-06-30T09:00:00+00:00",
    )

    result = run_night_government(
        db_dir=db_dir,
        day_id="2026-06-30",
        max_records=2,
    )

    source_ids = [
        item["source_record_id"]
        for item in result["active_packet"]["active_memory_items"]
    ]
    assert "mem_failure_001" in source_ids
    assert len([source_id for source_id in source_ids if source_id.startswith("mem_fact_")]) == 1
