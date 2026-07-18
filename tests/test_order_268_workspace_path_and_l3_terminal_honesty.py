from __future__ import annotations

from pathlib import Path

from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools.code_tools import explicit_code_file_paths_from_text


def test_explicit_workspace_path_accepts_korean_particle_without_semantic_guess(
    tmp_path: Path,
) -> None:
    (tmp_path / "workspace_policy.py").write_text("POLICY = True\n", encoding="utf-8")
    (tmp_path / "workspace_policy.py백업.py").write_text("BACKUP = True\n", encoding="utf-8")

    assert explicit_code_file_paths_from_text(
        root=tmp_path,
        text="workspace_policy.py를 실제로 읽어줘",
    ) == ["workspace_policy.py"]
    assert explicit_code_file_paths_from_text(
        root=tmp_path,
        text="workspace_policy.py 를 실제로 읽어줘",
    ) == ["workspace_policy.py"]
    assert explicit_code_file_paths_from_text(
        root=tmp_path,
        text="'workspace_policy.py'를 실제로 읽어줘",
    ) == ["workspace_policy.py"]
    assert explicit_code_file_paths_from_text(
        root=tmp_path,
        text="workspace_policy.py백업.py를 실제로 읽어줘",
    ) == ["workspace_policy.py백업.py"]


def test_terminal_distinguishes_initial_and_latest_l3_achievement() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "data_records": [
                {
                    "data_id": "L3:achievement_frame",
                    "data_type": "node_output:L3_achievement_frame",
                    "payload": {
                        "achievement_status": "failed",
                        "evidence_acquisition_status": "none",
                        "original_material_count": 0,
                        "achievement_generation_source": "CODE:OPERATION_CHECK",
                        "llm_semantic_judgement_status": "not_run",
                    },
                },
                {
                    "data_id": "L3:revision_achievement:0001",
                    "data_type": "node_output:L3_revision_achievement_frame",
                    "payload": {
                        "frame_id": "L3:revision_achievement:0001",
                        "achievement_status": "partial",
                        "evidence_acquisition_status": "candidates_only",
                        "original_material_count": 0,
                        "achievement_generation_source": "CODE:OPERATION_CHECK",
                        "llm_semantic_judgement_status": "not_run",
                    },
                },
                {
                    "data_id": "L3:revision_achievement:0002",
                    "data_type": "node_output:L3_revision_achievement_frame",
                    "payload": {
                        "frame_id": "L3:revision_achievement:0002",
                        "achievement_status": "achieved",
                        "evidence_acquisition_status": "original_material_acquired",
                        "original_material_count": 1,
                        "achievement_generation_source": "CODE:OPERATION_CHECK",
                        "llm_semantic_judgement_status": "not_run",
                    },
                },
            ],
        },
        user_input="L3 표시 테스트",
    )

    assert "L3 최초 달성 판단: failed / none / original_materials=0" in rendered
    assert "L3 최신 달성 판단" in rendered
    assert "L3 근거 확보 절대상태: original_material_acquired" in rendered
    assert "original_materials=1" in rendered


def test_terminal_surfaces_existing_l2_l3_llm_call_failures_only() -> None:
    rendered = render_runtime_view(
        {
            "status": "model_fallback",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "data_records": [
                _llm_call_record(
                    data_id="llm_call:L2:trace_001",
                    node_id="L2",
                    failure_type="schema_failed",
                    parse_status="passed",
                    validation_status="failed",
                    error_message="read_code_file path is not in the allowed list",
                ),
                _llm_call_record(
                    data_id="llm_call:L3:trace_002",
                    node_id="L3",
                    failure_type="parse_failed",
                    parse_status="failed",
                    validation_status="not_checked",
                    error_message="invalid JSON",
                ),
                _llm_call_record(
                    data_id="llm_call:node_3:trace_003",
                    node_id="node_3",
                    failure_type="schema_failed",
                    parse_status="passed",
                    validation_status="failed",
                    error_message="not part of the L fallback audit",
                ),
            ],
        },
        user_input="fallback 진단 테스트",
    )

    assert "L LLM fallback diagnostics [CODE/LLM_CALL_RECORD]" in rendered
    assert "node=L2 failure=schema_failed parse=passed validation=failed" in rendered
    assert "node=L3 failure=parse_failed parse=failed validation=not_checked" in rendered
    assert "read_code_file path is not in the allowed list" in rendered
    assert "not part of the L fallback audit" not in rendered


def _llm_call_record(
    *,
    data_id: str,
    node_id: str,
    failure_type: str,
    parse_status: str,
    validation_status: str,
    error_message: str,
) -> dict[str, object]:
    return {
        "data_id": data_id,
        "data_type": "llm_call",
        "payload": {
            "node_id": node_id,
            "prompt_ref": f"prompt/{node_id}.md",
            "failure_type": failure_type,
            "parse_status": parse_status,
            "validation_status": validation_status,
            "error_message": error_message,
        },
    }
