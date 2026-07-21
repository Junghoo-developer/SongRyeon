from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    ToolCatalogFrame,
    ToolCatalogItem,
    validate_tool_catalog_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.tools.source_time_tools import inspect_source_time_metadata
from songryeon_core.tools.tool_runner import ToolRunner, build_document_tool_registry


OBSERVED_AT = "2026-07-21T12:00:00+00:00"
MODIFIED_TIMESTAMP = 1_750_000_000


def test_exact_document_time_metadata_is_absolute_and_hash_bound(tmp_path: Path) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    document = document_root / "guide.md"
    content = "시간 근거 원문\n".encode("utf-8")
    document.write_bytes(content)
    os.utime(document, (MODIFIED_TIMESTAMP, MODIFIED_TIMESTAMP))

    result = inspect_source_time_metadata(
        document_root=document_root,
        code_root=code_root,
        source_scope="document",
        source_path="guide.md",
        observed_at_utc=OBSERVED_AT,
    )

    assert result["inspection_status"] == "ok"
    assert result["exists"] is True
    assert result["relative_path"] == "guide.md"
    assert result["observed_at_utc"] == OBSERVED_AT
    assert result["modified_at_utc"] == datetime.fromtimestamp(
        MODIFIED_TIMESTAMP,
        tz=timezone.utc,
    ).isoformat()
    assert result["size_bytes"] == len(content)
    assert result["content_hash_sha256"] == hashlib.sha256(content).hexdigest()
    assert result["source_kind"] == "workspace_document"
    assert result["generated_by"] == "CODE:SOURCE_TIME_METADATA_INSPECTOR"
    assert result["info_class"] == "absolute"
    assert result["semantic_judgement_status"] == "not_run"


def test_exact_code_time_metadata_uses_code_root(tmp_path: Path) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    source = code_root / "module.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")

    result = inspect_source_time_metadata(
        document_root=document_root,
        code_root=code_root,
        source_scope="code",
        source_path="module.py",
        observed_at_utc=OBSERVED_AT,
    )

    assert result["inspection_status"] == "ok"
    assert result["relative_path"] == "module.py"
    assert result["source_kind"] == "workspace_code_or_config"


@pytest.mark.parametrize(
    ("source_path", "expected_status"),
    [
        ("", "empty_source_path"),
        ("../outside.md", "path_outside_workspace_rejected"),
        (".env.local", "secret_filename_policy"),
        ("image.png", "unsupported_extension"),
    ],
)
def test_time_metadata_rejects_unsafe_or_unsupported_paths(
    tmp_path: Path,
    source_path: str,
    expected_status: str,
) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    (tmp_path / "outside.md").write_text("outside", encoding="utf-8")
    (document_root / ".env.local").write_text("SECRET=1", encoding="utf-8")
    (document_root / "image.png").write_bytes(b"png")

    result = inspect_source_time_metadata(
        document_root=document_root,
        code_root=code_root,
        source_scope="document",
        source_path=source_path,
        observed_at_utc=OBSERVED_AT,
    )

    assert result["inspection_status"] == expected_status
    assert result["exists"] is False
    assert result["content_hash_sha256"] is None


def test_time_metadata_rejects_absolute_path(tmp_path: Path) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    document = document_root / "guide.md"
    document.write_text("guide", encoding="utf-8")

    result = inspect_source_time_metadata(
        document_root=document_root,
        code_root=code_root,
        source_scope="document",
        source_path=str(document.resolve()),
        observed_at_utc=OBSERVED_AT,
    )

    assert result["inspection_status"] == "absolute_path_rejected"


def test_time_metadata_rejects_symbolic_link(tmp_path: Path) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    target = document_root / "target.md"
    link = document_root / "link.md"
    target.write_text("target", encoding="utf-8")
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symbolic link creation is unavailable on this Windows host")

    result = inspect_source_time_metadata(
        document_root=document_root,
        code_root=code_root,
        source_scope="document",
        source_path="link.md",
        observed_at_utc=OBSERVED_AT,
    )

    assert result["inspection_status"] == "symbolic_link_rejected"


def test_tool_catalog_preserves_temporal_capabilities(tmp_path: Path) -> None:
    registry = build_document_tool_registry(tmp_path, code_root=tmp_path)
    item = next(
        item
        for item in registry.to_catalog_items()
        if item.tool_name == "inspect_source_time_metadata"
    )
    frame = ToolCatalogFrame(
        catalog_id="tool_catalog:turn_order_283",
        turn_id="turn_order_283",
        tools=registry.to_catalog_items(),
    )

    validate_tool_catalog_frame(frame)
    assert item.read_only is True
    assert item.input_fields == ["source_scope", "source_path"]
    assert item.output_data_type == "tool_result:inspect_source_time_metadata"
    assert item.capabilities == [
        "temporal_metadata",
        "content_hash",
        "exact_source_path",
    ]
    assert frame.schema_version == "0.2"


@pytest.mark.parametrize("capabilities", [[""], ["temporal_metadata", "temporal_metadata"]])
def test_tool_catalog_rejects_empty_or_duplicate_capability(
    capabilities: list[str],
) -> None:
    frame = ToolCatalogFrame(
        catalog_id="tool_catalog:invalid",
        turn_id="turn_order_283",
        tools=[
            ToolCatalogItem(
                tool_name="invalid_tool",
                description="invalid capability test",
                read_only=True,
                output_data_type="tool_result:invalid",
                capabilities=capabilities,
            )
        ],
    )

    with pytest.raises(ValueError, match="capabilities"):
        validate_tool_catalog_frame(frame)


def test_tool_runner_records_time_metadata_result(tmp_path: Path) -> None:
    document = tmp_path / "guide.md"
    document.write_text("guide", encoding="utf-8")
    registry = build_document_tool_registry(tmp_path, code_root=tmp_path)
    trace_store = TraceStore()
    data_store = DataStore()

    result = ToolRunner(registry).run(
        tool_name="inspect_source_time_metadata",
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_283",
        source_scope="document",
        source_path="guide.md",
    )

    record = data_store.require_record(result.data_ref.data_id)
    assert record.data_type == "tool_result:inspect_source_time_metadata"
    assert isinstance(record.payload, dict)
    assert record.payload["inspection_status"] == "ok"
    assert record.source_trace_id == result.trace_event_id
