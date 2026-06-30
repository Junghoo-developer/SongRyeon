from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schemas import SchemaBinding


@dataclass
class PromptRecord:
    """노드에 주입될 프롬프트의 위치와 목적을 기록하는 설정 정보."""

    # 어떤 노드에 연결되는 프롬프트인지.
    node_id: str
    # 프롬프트 이름.
    prompt_name: str
    # 프롬프트 버전.
    version: str
    # 이 프롬프트가 어떤 용도인지.
    purpose: str
    # 실제 프롬프트 전문이 저장될 위치나 이름.
    system_prompt_ref: str
    # 0번처럼 조건부 프롬프트가 필요한 경우 사용할 규칙 이름 목록.
    conditional_prompt_rules: list[str] = field(default_factory=list)


@dataclass
class SchemaRecord:
    """노드 출력에 강제할 스키마 설정 정보."""

    # 스키마 이름.
    schema_name: str
    # 스키마 버전.
    version: str
    # 이 스키마가 적용될 대상 노드.
    target_node: str
    # 반드시 적용해야 하는지.
    required: bool
    # 필드 이름 목록. 지금은 사람이 읽는 설정으로만 둔다.
    fields: list[str] = field(default_factory=list)
    # 검증 정책 이름.
    validation_policy: str = "manual_minimal"


class PromptRegistry:
    """PromptRecord를 node_id 기준으로 찾아주는 작은 레지스트리."""

    def __init__(self, records: list[PromptRecord] | None = None) -> None:
        self._records = {record.node_id: record for record in records or []}

    def get(self, node_id: str) -> PromptRecord | None:
        return self._records.get(node_id)

    def register(self, record: PromptRecord) -> None:
        self._records[record.node_id] = record


class SchemaRegistry:
    """SchemaRecord를 node_id 기준으로 SchemaBinding으로 바꿔주는 레지스트리."""

    def __init__(self, records: list[SchemaRecord] | None = None) -> None:
        self._records = {record.target_node: record for record in records or []}

    def get_record(self, target_node: str) -> SchemaRecord | None:
        return self._records.get(target_node)

    def binding_for(self, target_node: str) -> SchemaBinding | None:
        record = self.get_record(target_node)
        if record is None:
            return None
        return SchemaBinding(
            schema_name=record.schema_name,
            schema_version=record.version,
            required=record.required,
            validation_status="not_checked",
        )

    def register(self, record: SchemaRecord) -> None:
        self._records[record.target_node] = record


def build_default_prompt_registry() -> PromptRegistry:
    """드라이런에서 사용할 기본 프롬프트 레지스트리를 만든다."""

    return PromptRegistry(
        [
            PromptRecord(
                node_id="node_0",
                prompt_name="memory_supplier",
                version="0.1",
                purpose="trace와 0.state를 근거로 다음 노드에 기억 패킷을 공급한다.",
                system_prompt_ref="songryeon_core/prompts/node_0_memory_supplier_v0.md",
                conditional_prompt_rules=[
                    "pre_route_report",
                    "targeted_memory_supply",
                    "loop_return_summary",
                    "final_trace_for_2",
                ],
            ),
            PromptRecord(
                node_id="node_1",
                prompt_name="router",
                version="0.1",
                purpose="다음 라우팅 대상을 고른다.",
                system_prompt_ref="songryeon_core/prompts/node_1_router_v0.md",
            ),
            PromptRecord(
                node_id="memory_relevance_selector",
                prompt_name="memory_relevance_selector",
                version="0.1",
                purpose="최근 memory relevance candidate frame 중 현재 입력과 관련 있어 보이는 후보를 고른다.",
                system_prompt_ref="songryeon_core/prompts/memory_relevance_selector_v0.md",
            ),
            PromptRecord(
                node_id="node_2",
                prompt_name="metainfo_boundary",
                version="0.1",
                purpose="절대정보 경계를 만든다.",
                system_prompt_ref="songryeon_core/prompts/node_2_metainfo_boundary_v0.md",
            ),
            PromptRecord(
                node_id="node_2_answer_basis",
                prompt_name="answer_basis_selector",
                version="0.1",
                purpose="node_3 최종 답변의 근거 말하기 모드를 고른다.",
                system_prompt_ref="songryeon_core/prompts/node_2_answer_basis_selector_v0.md",
            ),
            PromptRecord(
                node_id="node_3",
                prompt_name="reporter",
                version="0.1",
                purpose="허용된 절대정보만 보고한다.",
                system_prompt_ref="songryeon_core/prompts/node_3_reporter_v0.md",
            ),
        ]
    )


def build_default_schema_registry() -> SchemaRegistry:
    """드라이런에서 사용할 기본 스키마 레지스트리를 만든다."""

    return SchemaRegistry(
        [
            SchemaRecord(
                schema_name="MemoryPacketFrom0",
                version="0.1",
                target_node="node_0",
                required=True,
                fields=["target", "trace_evidence_ids", "insufficient_signal_id"],
            ),
            SchemaRecord(
                schema_name="RoutingDecision",
                version="0.1",
                target_node="node_1",
                required=True,
                fields=["route", "required_schema", "expected_next_0_mode"],
            ),
            SchemaRecord(
                schema_name="MetainfoBoundary",
                version="0.1",
                target_node="node_2",
                required=True,
                fields=["absolute_info"],
            ),
            SchemaRecord(
                schema_name="Node2AnswerBasisFrame",
                version="0.1",
                target_node="node_2_answer_basis",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "answer_basis_mode",
                    "basis_reason_codes",
                    "mode_selection_reason",
                    "mode_selection_reason_info_class",
                    "evidence_roles",
                    "generated_by",
                    "info_class",
                    "semantic_judgement_status",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="Node2InputFrame",
                version="0.1",
                target_node="node_2_input",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "final_memory_packet_id",
                    "turn_outcome_id",
                    "route_ids",
                    "l_loop_output_ids",
                    "source_trace_ids",
                    "source_data_ids",
                    "boundary_policy",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="LLMCallFrame",
                version="0.1",
                target_node="llm_call",
                required=True,
                fields=[
                    "call_id",
                    "turn_id",
                    "node_id",
                    "prompt_ref",
                    "input_data_ids",
                    "model_id",
                    "response_format",
                    "raw_text",
                    "parse_status",
                    "validation_status",
                    "retry_count",
                    "failure_type",
                    "error_message",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="MemoryRelevanceSelectionFrame",
                version="0.1",
                target_node="memory_relevance_selector",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "selector_target_node",
                    "current_user_input_trace_id",
                    "source_memory_packet_id",
                    "candidate_frame_ids",
                    "selected_candidate_turn_ids",
                    "selected_candidate_frame_ids",
                    "selection_status",
                    "selection_reason",
                    "judged_by",
                    "generated_by",
                    "llm_call_data_id",
                    "llm_trace_event_id",
                    "source_trace_ids",
                    "source_data_ids",
                    "source_memory_item_ids",
                    "info_class",
                    "source_mode",
                    "claim_alignment",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="RawMemoryCompressionCandidateFrame",
                version="0.1",
                target_node="node_0:raw_memory_compression_candidate",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "policy_id",
                    "raw_conversation_count",
                    "max_raw_window",
                    "min_raw_guarantee",
                    "post_compression_keep",
                    "compression_batch_size",
                    "candidate_status",
                    "candidate_turn_ids",
                    "candidate_raw_entry_count",
                    "retained_raw_turn_ids",
                    "retained_raw_entry_count",
                    "older_unmanaged_raw_turn_count",
                    "source_memory_item_ids",
                    "source_trace_ids",
                    "source_data_ids",
                    "generated_by",
                    "info_class",
                    "semantic_judgement_status",
                    "node5_compression_status",
                    "node4_approval_status",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="SelectedRecentMemoryContextFrame",
                version="0.1",
                target_node="node_0:selected_recent_memory_context",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "selection_frame_id",
                    "selection_status",
                    "selected_turn_count",
                    "items",
                    "missing_selected_memory_context_count",
                    "generated_by",
                    "info_class",
                    "semantic_judgement_status",
                    "source_data_ids",
                    "source_trace_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="ToolCatalogFrame",
                version="0.1",
                target_node="tool_catalog",
                required=True,
                fields=[
                    "catalog_id",
                    "turn_id",
                    "tools",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="ToolChoiceFrame",
                version="0.1",
                target_node="tool_choice",
                required=True,
                fields=[
                    "choice_id",
                    "turn_id",
                    "chooser_node_id",
                    "tool_name",
                    "reason",
                    "expected_use",
                    "catalog_id",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="L1GoalFrame",
                version="0.2",
                target_node="L1",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "macro_goal",
                    "macro_goal_reason",
                    "micro_goal",
                    "micro_goal_reason",
                    "goal_source",
                    "target_loop",
                    "evidence_requirement_kind",
                    "minimum_read_documents",
                    "requires_cross_document_analysis",
                    "randomness_mode",
                    "l_loop_success_condition",
                    "requested_search_top_k",
                    "requested_max_tool_calls",
                    "requested_max_read_doc_calls",
                    "requested_max_query_attempts",
                    "budget_request_reason",
                    "goal_generation_source",
                    "llm_goal_judgement_status",
                    "schema_name",
                    "schema_version",
                    "source_trace_ids",
                    "source_data_ids",
                ],
            ),
            SchemaRecord(
                schema_name="L2QueryFrame",
                version="0.1",
                target_node="L2",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "query_text",
                    "query_source",
                    "query_mode",
                    "target_tool_name",
                    "schema_name",
                    "schema_version",
                    "source_trace_ids",
                    "source_data_ids",
                ],
            ),
            SchemaRecord(
                schema_name="LLoopRunFrame",
                version="0.1",
                target_node="L",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "loop_id",
                    "run_index",
                    "namespace_policy",
                    "primary_ids_are_attempt_scoped",
                    "same_turn_rerun_allowed",
                    "rerun_block_reason",
                    "planned_next_step",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="LLoopReturnSummaryFrame",
                version="0.1",
                target_node="node_0",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "loop_id",
                    "l_loop_task_status",
                    "failure_level",
                    "evidence_requirement_kind",
                    "required_min_read_documents",
                    "actual_read_doc_count",
                    "search_candidate_count",
                    "final_continuation_status",
                    "budget_stop_reason",
                    "remaining_tool_calls",
                    "remaining_read_doc_calls",
                    "remaining_query_attempts",
                    "l3_goal_match_status",
                    "l3_semantic_goal_match_status",
                    "recommended_next_route_for_node1",
                    "route_hint_reason",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="L2QueryPlanFrame",
                version="0.1",
                target_node="L2_query_planner",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "planner_mode",
                    "selected_candidate_id",
                    "candidates",
                    "source_trace_ids",
                    "source_data_ids",
                    "achievement_generation_source",
                    "llm_semantic_judgement_status",
                    "schema_name",
                    "schema_version",
                ],
            ),
            SchemaRecord(
                schema_name="L3PreservedInfoFrame",
                version="0.1",
                target_node="L3",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "schema_name",
                    "schema_version",
                    "source_trace_ids",
                    "source_data_ids",
                    "judgement_status",
                    "candidates",
                ],
            ),
            SchemaRecord(
                schema_name="L3AchievementFrame",
                version="0.1",
                target_node="L3_achievement",
                required=True,
                fields=[
                    "frame_id",
                    "turn_id",
                    "achievement_status",
                    "reason",
                    "target_goal_data_id",
                    "preserved_info_frame_id",
                    "candidate_count",
                    "evidence_trace_ids",
                    "evidence_data_ids",
                    "source_trace_ids",
                    "source_data_ids",
                    "schema_name",
                    "schema_version",
                ],
            ),
        ]
    )
