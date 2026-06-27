from __future__ import annotations

import importlib


def test_core_import_baseline() -> None:
    module_names = [
        "songryeon_core",
        "songryeon_core.core.schema_parts",
        "songryeon_core.core.schema_parts.base",
        "songryeon_core.core.schema_parts.task_ledger",
        "songryeon_core.core.schema_parts.trace_data",
        "songryeon_core.core.schemas",
        "songryeon_core.core.trace_store",
        "songryeon_core.runtime.dry_run",
        "songryeon_core.runtime.smoke_cases.document_memory",
        "songryeon_core.runtime.smoke_cases.router_fallback",
        "songryeon_core.runtime.smoke_cases.runtime_view",
        "songryeon_core.runtime.smoke_test",
        "main",
    ]

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None
