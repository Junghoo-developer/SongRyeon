from __future__ import annotations

from pathlib import Path

from songryeon_core.nodes.node_1_router import _route_capability_cards


def test_node1_r_card_names_recent_development_status_as_graph_memory_surface() -> None:
    cards = _route_capability_cards(
        allow_r_route_experimental=True,
        r_execution_mode="vessel_live",
    )
    by_route = {card["route"]: card for card in cards}

    r_card = by_route["R"]
    r_best_for = " ".join(str(item) for item in r_card["best_for"])
    r_not_for = " ".join(str(item) for item in r_card["not_for"])

    assert "current or recent SongRyeon Core development-status briefing" in r_best_for
    assert "recent order history or implementation timeline briefing" in r_best_for
    assert "already-ingested Vessel graph memory" in r_best_for
    assert "freshly changed source files or order documents" in r_not_for


def test_node1_l_card_separates_fresh_lookup_from_ingested_status_briefing() -> None:
    cards = _route_capability_cards(
        allow_r_route_experimental=True,
        r_execution_mode="vessel_live",
    )
    by_route = {card["route"]: card for card in cards}

    l_card = by_route["L"]
    l_best_for = " ".join(str(item) for item in l_card["best_for"])
    l_not_for = " ".join(str(item) for item in l_card["not_for"])

    assert "source evidence not already ingested" in l_best_for
    assert "latest disk state" in l_best_for
    assert "current or recent development-status briefing" in l_not_for
    assert "already-ingested Vessel graph memory" in l_not_for


def test_node1_prompt_keeps_recent_status_as_evidence_surface_comparison() -> None:
    text = Path("songryeon_core/prompts/node_1_router_v0.md").read_text(
        encoding="utf-8"
    )

    assert "Do not choose by keyword alone" in text
    assert "current/recent SongRyeon Core development status" in text
    assert "already-ingested Vessel graph memory" in text
    assert "files/orders" in text
    assert "may be newer than the graph observation" in text
