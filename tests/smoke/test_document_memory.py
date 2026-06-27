from __future__ import annotations

import pytest

from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.smoke_cases.document_memory import check_document_memory_index
from songryeon_core.tools.document_tools import search_docs


@pytest.mark.smoke
def test_document_memory_smoke_case() -> None:
    result = run_dry_turn()
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    search_result = search_docs(
        root="Administrative_Reform_1",
        query="L3PreservedInfoFrame",
        top_k=1,
    )

    smoke = check_document_memory_index(records, search_result)

    assert smoke["has_order"] is True
    assert smoke["l3_metadata"] is True
    assert smoke["document_count"] >= 1
