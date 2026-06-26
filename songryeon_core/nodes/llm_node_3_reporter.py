from __future__ import annotations

from pathlib import Path

from songryeon_core.llm.fake import FakeLLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutionResult, LLMNodeExecutor


def run_llm_reporter_probe(input_payload: dict[str, object]) -> LLMNodeExecutionResult:
    """3 보고관 LLM화를 위한 안전한 Fake adapter probe."""

    prompt = Path("songryeon_core/prompts/node_3_reporter_v0.md").read_text(encoding="utf-8")
    return LLMNodeExecutor(FakeLLMAdapter()).run(
        node_id="node_3",
        prompt=prompt,
        input_payload=input_payload,
    )
