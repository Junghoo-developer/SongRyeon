from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_node3_prompt_separates_proposal_from_current_runtime_fact() -> None:
    prompt = (ROOT / "songryeon_core/prompts/node_3_reporter_v0.md").read_text(
        encoding="utf-8"
    )

    assert "Preserve the source's modal status" in prompt
    assert "current turn actually executed or approved" in prompt
    assert "Do not rewrite examples as" in prompt


def test_node4_prompt_accepts_vessel_raw_as_proposal_grounding_channel() -> None:
    prompt = (ROOT / "songryeon_core/prompts/node_4_gatekeeper_v0.md").read_text(
        encoding="utf-8"
    )

    assert "node3_input_brief.vessel_r_material` as the checkable grounding" in prompt
    assert "material_kind=raw_original" in prompt
    assert "supports proposal-language claims" in prompt
    assert "Do not invent" in prompt
