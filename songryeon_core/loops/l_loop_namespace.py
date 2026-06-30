from __future__ import annotations

from dataclasses import dataclass


L_REROUTE_REMAINING_BLOCK_REASON = (
    "CODE_STATUS:same_turn_L_reroute_disabled_by_policy"
)
L_REROUTE_PLANNED_NEXT_STEP = (
    "CODE_STATUS:same_turn_L_reroute_runtime_flow_closed_by_policy"
)


@dataclass(frozen=True)
class LRunIds:
    """L루프 1회 실행이 사용할 주요 DataStore ID 묶음.

    v0에서는 첫 번째 L 실행만 기존 고정 ID를 그대로 사용한다. 이렇게 해야
    기존 실행 기록, smoke test, 사람이 익숙한 런타임 출력이 한 번에 깨지지
    않는다. 대신 run_index가 2 이상이면 같은 ID family를 run scope 안으로
    넣어, 다음 단계에서 상위 L 재라우팅을 열 수 있는 경로를 제공한다.
    """

    run_index: int
    # 이 L루프 실행 자체를 기록하는 프레임 ID.
    run_frame_data_id: str
    # 현재 ID 정책 이름. 1회차 호환 정책인지, 2회차 이상 scoped 정책인지 드러낸다.
    namespace_policy: str
    # 아래 primary ID들은 L1/L2/L3가 직접 만드는 핵심 node output ID다.
    # control/tool/revision 같은 나머지 ID는 메서드로 만든다.
    # 한 실행에서 나온 모든 주요 기록이 같은 run 이름표를 갖게 하려는 구조다.
    l1_goal_data_id: str
    l2_query_plan_data_id: str
    l2_query_data_id: str
    l3_preserved_data_id: str
    l3_achievement_data_id: str
    budget_plan_data_id: str

    @property
    def run_prefix(self) -> str:
        """2회차부터 DataStore ID 앞에 붙일 실행 이름표."""

        return f"L:run:{self.run_index:04d}"

    @property
    def uses_scoped_ids(self) -> bool:
        """이 실행이 legacy ID 앞에 run 이름표를 붙이는지 알려준다."""

        return self.run_index > 1

    def scoped_data_id(self, legacy_data_id: str) -> str:
        """legacy ID를 이 L 실행의 ID로 바꾼다.

        1회차는 일부러 그대로 둔다. 2회차부터만 앞에 `L:run:0002:` 같은
        이름표를 붙인다. 같은 이름표를 붙여야 DataStore가 두 번째 L 실행에서
        나온 기록을 첫 번째 실행 기록과 헷갈리지 않는다.
        """

        if not legacy_data_id:
            raise ValueError("legacy_data_id must not be empty")
        if not self.uses_scoped_ids:
            return legacy_data_id
        return f"{self.run_prefix}:{legacy_data_id}"

    def owns_data_id(self, data_id: str) -> bool:
        """DataStore ID가 이 L 실행 이름표에 속하는지 확인한다."""

        if not self.uses_scoped_ids:
            return not data_id.startswith("L:run:")
        return data_id.startswith(f"{self.run_prefix}:")

    def control_data_id(self, iteration_index: int) -> str:
        return self.scoped_data_id(f"L:control:{iteration_index:04d}")

    def continuation_data_id(self, attempt_index: int) -> str:
        return self.scoped_data_id(f"L:continuation:{attempt_index:04d}")

    def l2_revision_input_data_id(self, attempt_index: int) -> str:
        return self.scoped_data_id(f"L2:revision_input:{attempt_index:04d}")

    def l2_revision_query_plan_data_id(self, attempt_index: int) -> str:
        return self.scoped_data_id(f"L2:revision_query_plan:{attempt_index:04d}")

    def l2_revision_query_frame_data_id(self, attempt_index: int) -> str:
        return self.scoped_data_id(f"L2:revision_query_frame:{attempt_index:04d}")

    def l3_revision_preserved_data_id(self, attempt_index: int) -> str:
        return self.scoped_data_id(f"L3:revision_preserved_info:{attempt_index:04d}")

    def l3_revision_achievement_data_id(self, attempt_index: int) -> str:
        return self.scoped_data_id(f"L3:revision_achievement:{attempt_index:04d}")

    def tool_catalog_data_id(self, turn_id: str) -> str:
        return self.scoped_data_id(f"tool_catalog:{turn_id}")

    def tool_choice_data_id(self, chooser_node_id: str, tool_name: str) -> str:
        return self.scoped_data_id(f"tool_choice:{chooser_node_id}:{tool_name}")

    def tool_budget_data_id(self, turn_id: str, sequence_index: int) -> str:
        return self.scoped_data_id(f"tool_budget:{turn_id}:{sequence_index:04d}")

    def tool_efficiency_failure_data_id(
        self,
        *,
        turn_id: str,
        duplicate_kind: str,
        sequence_index: int,
    ) -> str:
        legacy_id = (
            f"failure:tool_efficiency:{turn_id}:duplicate_{duplicate_kind}:"
            f"{sequence_index:04d}"
        )
        return self.scoped_data_id(legacy_id)

    def l_loop_failure_data_id(self, *, turn_id: str, signal_index: int) -> str:
        return self.scoped_data_id(f"failure:L_loop:{turn_id}:{signal_index:04d}")

    def tool_result_data_id(self, *, tool_name: str, event_id: str) -> str:
        return self.scoped_data_id(f"tool_result:{tool_name}:{event_id}")

    def tool_distillation_data_id(self, *, tool_name: str, original_trace_id: str) -> str:
        return self.scoped_data_id(f"tool_distillation:{tool_name}:{original_trace_id}")

    def return_summary_frame_id(self) -> str:
        return self.scoped_data_id("L:return_summary_frame")

    def loop_return_memory_packet_id(self) -> str:
        return self.scoped_data_id("memory_packet:node_1:loop_return_summary")

    def route_decision_id(self, route: str) -> str:
        return self.scoped_data_id(f"route:{route}")

    def return_route_decision_id(self, route: str) -> str:
        """L 복귀 이후 node_1 route 기록 ID를 만든다.

        1회차 진입 route=L은 이미 `route:L`을 쓰므로, 1회차 L 복귀가 다시
        route=L을 고르는 새 v0 흐름에서는 별도 ID를 써야 DataStore 충돌이 없다.
        route=2는 기존 legacy ID를 유지해 기존 smoke 기대값을 보존한다.
        """

        if self.run_index == 1 and route == "L":
            return "L:reroute:route:L"
        return self.route_decision_id(route)

    def reroute_controller_data_id(self) -> str:
        return self.scoped_data_id("L:reroute_controller:0001")

    def node2_input_frame_id(self, turn_id: str) -> str:
        return self.scoped_data_id(f"node2_input:{turn_id}")

    def route2_handoff_frame_id(self) -> str:
        return self.scoped_data_id("node_2:handoff_frame")

    def node3_input_brief_frame_id(self) -> str:
        return self.scoped_data_id("node_3:input_brief_frame")

    def node2_answer_basis_frame_id(self) -> str:
        return self.scoped_data_id("node_2:answer_basis_frame")

    def node3_report_id(self) -> str:
        return self.scoped_data_id("report_dry_001")

    def node4_gatekeeper_frame_id(self) -> str:
        return self.scoped_data_id("node_4:gatekeeper_frame")

    def turn_outcome_id(self, turn_id: str) -> str:
        return self.scoped_data_id(f"turn_outcome:{turn_id}")

    def metainfo_boundary_id(self) -> str:
        return self.scoped_data_id("boundary_dry_001")

    def memory_packet_data_id(
        self,
        *,
        target: str,
        mode: str,
        packet_id_suffix: str | None = None,
    ) -> str:
        base_id = f"memory_packet:{target}:{mode}"
        if packet_id_suffix is not None:
            base_id = f"{base_id}:{packet_id_suffix}"
        return self.scoped_data_id(base_id)


def build_l_run_ids(*, run_index: int) -> LRunIds:
    """L루프 실행 번호에 맞는 DataStore ID 묶음을 만든다."""

    if run_index < 1:
        raise ValueError("run_index must be positive")

    if run_index == 1:
        # 1회차는 의도적으로 예전 ID를 유지한다.
        # 기존 smoke, replay, 사람이 읽는 runtime 출력이 한 번에 깨지는 것을 막기 위한 호환층이다.
        return LRunIds(
            run_index=run_index,
            run_frame_data_id="L:run_frame:0001",
            namespace_policy="fixed_primary_ids_v0",
            l1_goal_data_id="L1:goal_frame",
            l2_query_plan_data_id="L2:query_plan_frame",
            l2_query_data_id="L2:query_frame",
            l3_preserved_data_id="L3:preserved_info_frame",
            l3_achievement_data_id="L3:achievement_frame",
            budget_plan_data_id="L:budget_plan_frame",
        )

    prefix = f"L:run:{run_index:04d}"
    # 2회차부터는 주요 output ID를 run scope 안으로 넣는다.
    # 이름 앞에 L:run:0002를 붙이면 같은 턴에서 L루프를 다시 실행해도
    # DataStore가 첫 번째 실행 record와 두 번째 실행 record를 같은 것으로 보지 않는다.
    return LRunIds(
        run_index=run_index,
        run_frame_data_id=f"L:run_frame:{run_index:04d}",
            namespace_policy="run_scoped_l_internal_return_and_downstream_ids_v1",
        l1_goal_data_id=f"{prefix}:L1:goal_frame",
        l2_query_plan_data_id=f"{prefix}:L2:query_plan_frame",
        l2_query_data_id=f"{prefix}:L2:query_frame",
        l3_preserved_data_id=f"{prefix}:L3:preserved_info_frame",
        l3_achievement_data_id=f"{prefix}:L3:achievement_frame",
        budget_plan_data_id=f"{prefix}:L:budget_plan_frame",
    )
