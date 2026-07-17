from __future__ import annotations

from songryeon_core.runtime.terminal_view import render_compact_turn
from songryeon_core.runtime.user_turn import run_fake_user_turn


def test_compact_turn_keeps_core_audit_counts_and_answer_without_full_ledger() -> None:
    result = run_fake_user_turn(
        user_input="송련이 뭔지 짧게 설명해줘",
        include_data_records=True,
    )

    rendered = render_compact_turn(
        result,
        user_input="송련이 뭔지 짧게 설명해줘",
    )

    assert "[runtime:compact]" in rendered
    assert "학습용 절대정보 감사판" in rendered
    assert "route: sequence=['2']" in rendered
    assert "node_4 검사: gate=pass" in rendered
    assert "[answer]" in rendered
    assert "실제 Qwen 답변이 아니라" in rendered

    # 전체 장부는 result에 보존하되, 첫 시연 화면에는 반복 상세를 펼치지 않는다.
    assert "L loop run namespace:" not in rendered
    assert "graph memory guide:" not in rendered
    assert "source_data_ids:" not in rendered
