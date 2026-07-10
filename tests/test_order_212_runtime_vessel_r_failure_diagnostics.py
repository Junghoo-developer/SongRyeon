from __future__ import annotations

from songryeon_core.runtime.terminal_view import render_runtime_view


def test_runtime_view_surfaces_vessel_r_failure_diagnostics() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "vessel_r_failure_stage": "R2:step_0001",
            "vessel_r_failure_type": "schema_failed",
            "vessel_r_failure_reason": (
                "R2 expected_information_granularity is invalid"
            ),
            "data_records": [
                {
                    "data_id": "node_3:input_brief_frame",
                    "data_type": "node_output:node3_input_brief_frame",
                    "payload": {
                        "vessel_r_material": {
                            "material_status": "failed",
                            "r_loop_task_status": "failed",
                            "failure_type": "schema_failed",
                            "failure_reason": (
                                "R2 expected_information_granularity is invalid"
                            ),
                            "material_items": [],
                        },
                    },
                }
            ],
        },
        user_input="R 실패 진단 표시 테스트",
    )

    assert "R/Vessel 실패 진단: stage=R2:step_0001" in rendered
    assert "type=schema_failed" in rendered
    assert "reason=R2 expected_information_granularity is invalid" in rendered
    assert "Vessel R failure: type=schema_failed" in rendered
