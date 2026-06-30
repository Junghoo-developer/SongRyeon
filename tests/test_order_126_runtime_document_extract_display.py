from __future__ import annotations

from songryeon_core.runtime.terminal_view import render_runtime_view


def test_runtime_view_lists_all_document_extract_records() -> None:
    output = render_runtime_view(
        {
            "status": "ok",
            "trace_count": 3,
            "data_record_count": 3,
            "data_records": [
                _document_extract_record(
                    data_id="tool_result:read_doc:A",
                    data_type="tool_result:read_doc",
                    doc_id="docs/A.md",
                    text="A 원문",
                ),
                _document_extract_record(
                    data_id="tool_result:read_doc:B",
                    data_type="tool_result:read_doc",
                    doc_id="docs/B.md",
                    text="B 원문",
                ),
                _document_extract_record(
                    data_id="tool_result:read_artifact:C",
                    data_type="tool_result:read_artifact",
                    doc_id="docs/C.md",
                    text="C 원문",
                ),
            ],
        },
        user_input="문서 읽기 표시 확인",
    )

    assert "source=tool_result:read_doc:A" in output
    assert "source=tool_result:read_doc:B" in output
    assert "source=tool_result:read_artifact:C" in output
    assert output.count("[TOOL_RESULT:DOCUMENT_EXTRACT") == 3


def test_runtime_view_prefers_latest_run_scoped_document_extract_records() -> None:
    output = render_runtime_view(
        {
            "status": "ok",
            "trace_count": 4,
            "data_record_count": 4,
            "data_records": [
                {
                    "data_id": "L:run:0001:frame",
                    "data_type": "node_output:L_loop_run_frame",
                    "payload": {"run_index": 1},
                },
                {
                    "data_id": "L:run:0002:frame",
                    "data_type": "node_output:L_loop_run_frame",
                    "payload": {"run_index": 2},
                },
                _document_extract_record(
                    data_id="L:run:0001:tool_result:read_doc:OLD",
                    data_type="tool_result:read_doc",
                    doc_id="docs/OLD.md",
                    text="old",
                ),
                _document_extract_record(
                    data_id="L:run:0002:tool_result:read_doc:NEW",
                    data_type="tool_result:read_doc",
                    doc_id="docs/NEW.md",
                    text="new",
                ),
            ],
        },
        user_input="최신 L run 문서 읽기 표시 확인",
    )

    assert "source=L:run:0002:tool_result:read_doc:NEW" in output
    assert "source=L:run:0001:tool_result:read_doc:OLD" not in output


def _document_extract_record(
    *,
    data_id: str,
    data_type: str,
    doc_id: str,
    text: str,
) -> dict[str, object]:
    return {
        "data_id": data_id,
        "data_type": data_type,
        "payload": {
            "doc_id": doc_id,
            "text": text,
            "char_count": len(text),
        },
    }
