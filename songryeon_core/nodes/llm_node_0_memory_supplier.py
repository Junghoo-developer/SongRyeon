from __future__ import annotations

from pathlib import Path

from songryeon_core.llm.fake import FakeLLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutionResult, LLMNodeExecutor


def run_llm_memory_supplier_probe(input_payload: dict[str, object]) -> LLMNodeExecutionResult:
    """0 기억공급관 LLM화를 위한 안전한 Fake adapter probe."""

    prompt = Path("songryeon_core/prompts/node_0_memory_supplier_v0.md").read_text(
        encoding="utf-8"
    )
    return LLMNodeExecutor(FakeLLMAdapter()).run(
        node_id="node_0",
        prompt=prompt,
        input_payload=input_payload,
    )
