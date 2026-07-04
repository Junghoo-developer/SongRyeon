from __future__ import annotations

import importlib


def test_core_import_baseline() -> None:
    module_names = [
        "songryeon_core",
        "songryeon_core.core.schema_parts",
        "songryeon_core.core.schema_parts.base",
        "songryeon_core.core.schema_parts.loop_activity",
        "songryeon_core.core.schema_parts.task_ledger",
        "songryeon_core.core.schema_parts.trace_data",
        "songryeon_core.core.schemas",
        "songryeon_core.core.graph_memory_export",
        "songryeon_core.core.graph_memory_integrity",
        "songryeon_core.core.graph_source_ingest",
        "songryeon_core.core.graph_vessel_neo4j",
        "songryeon_core.core.graph_vessel_inspect",
        "songryeon_core.core.graph_vessel_readback",
        "songryeon_core.core.graph_vessel_adapter",
        "songryeon_core.core.songryeon_source_manifest",
        "songryeon_core.core.trace_store",
        "songryeon_core.core.turn_activity_graph_links",
        "songryeon_core.runtime.fast_test",
        "songryeon_core.runtime.graph_vessel_first_write",
        "songryeon_core.runtime.graph_vessel_inspect",
        "songryeon_core.runtime.graph_vessel_readback",
        "songryeon_core.runtime.r_loop_vessel_answer_demo",
        "songryeon_core.runtime.r_loop_vessel_live_route",
        "songryeon_core.runtime.dry_run",
        "songryeon_core.runtime.smoke_cases.document_memory",
        "songryeon_core.runtime.smoke_cases.router_fallback",
        "songryeon_core.runtime.smoke_cases.runtime_view",
        "songryeon_core.runtime.smoke_test",
        "main",
    ]

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None
