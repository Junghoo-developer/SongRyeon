from pathlib import Path


PROMPT_PATH = Path("songryeon_core/prompts/r2_vessel_node_selector_v0.md")


def test_r2_prompt_does_not_contain_copyable_fake_graph_id_examples() -> None:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "graph:summary:source_leaf:example" not in prompt
    assert "surface:summary:data:source_leaf_summary:depth:1:info:relative" not in prompt
    assert "```json" not in prompt
    assert "runtime candidate record `node_ref`" in prompt
    assert "The only selectable IDs are in the runtime input payload." in prompt
