from __future__ import annotations

import json

from songryeon_core.llm.base import LLMRequest, LLMResponse


class FakeLLMAdapter:
    """테스트용 LLM adapter."""

    model_id = "fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "echo": request.input_payload,
            "response_format": request.response_format,
            "adapter": self.model_id,
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class BrokenJSONFakeLLMAdapter:
    """재시도/파싱 실패 테스트용 adapter."""

    model_id = "broken-json-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text="this is not json",
            model_id=self.model_id,
            raw={"broken": True, "response_format": request.response_format},
        )


class MemoryRelevanceSelectedFakeLLMAdapter:
    """Memory relevance selector selected smoke용 adapter."""

    model_id = "memory-relevance-selected-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        candidates = request.input_payload.get("relevance_candidate_frames")
        first_candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
        frame_id = (
            first_candidate.get("frame_id")
            if isinstance(first_candidate, dict)
            else None
        )
        turn_id = (
            first_candidate.get("candidate_turn_id")
            if isinstance(first_candidate, dict)
            else None
        )
        payload = {
            "selection_status": "selected" if frame_id and turn_id else "none_selected",
            "selected_candidate_turn_ids": [turn_id] if isinstance(turn_id, str) and turn_id else [],
            "selected_candidate_frame_ids": [frame_id] if isinstance(frame_id, str) and frame_id else [],
            "selection_reason": (
                "fake selector selected the first supplied candidate for smoke testing."
                if frame_id and turn_id
                else "fake selector received no candidates."
            ),
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class MemoryRelevanceNoneSelectedFakeLLMAdapter:
    """Memory relevance selector none_selected smoke용 adapter."""

    model_id = "memory-relevance-none-selected-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "selection_status": "none_selected",
            "selected_candidate_turn_ids": [],
            "selected_candidate_frame_ids": [],
            "selection_reason": "fake selector intentionally selected no candidates for smoke testing.",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class QueryPlannerFakeLLMAdapter:
    """L2 query planner smoke test용 adapter."""

    model_id = "query-planner-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        user_input = str(request.input_payload.get("user_input") or "").strip()
        source_data_ids = request.input_payload.get("source_data_ids")
        if not isinstance(source_data_ids, list) or not source_data_ids:
            source_data_ids = ["L1:goal_frame"]

        base_query = user_input or "내부 문서 검색"
        payload = {
            "planner_mode": "llm",
            "selected_candidate_id": "L2:query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:query_candidate_0001",
                    "query_text": base_query,
                    "purpose": "사용자 입력과 L1 목표를 직접 반영해 내부 문서에서 관련 근거를 찾는다.",
                    "expected_signal": "사용자 요청과 직접 연결된 문서 chunk",
                    "priority": 1,
                    "target_tool_name": "search_docs",
                    "source_data_ids": source_data_ids,
                },
                {
                    "candidate_id": "L2:query_candidate_0002",
                    "query_text": f"{base_query} 구조 스키마 trace",
                    "purpose": "구조, 스키마, trace 관련 내부 문서를 함께 찾는다.",
                    "expected_signal": "스키마나 trace 설계와 연결된 문서 chunk",
                    "priority": 2,
                    "target_tool_name": "search_docs",
                    "source_data_ids": source_data_ids,
                },
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class ExactArtifactQueryPlannerFakeLLMAdapter:
    """L2 read_artifact routing smoke test용 adapter."""

    model_id = "exact-artifact-query-planner-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        source_data_ids = request.input_payload.get("source_data_ids")
        if not isinstance(source_data_ids, list) or not source_data_ids:
            source_data_ids = ["L1:goal_frame"]

        payload = {
            "planner_mode": "llm",
            "selected_candidate_id": "L2:query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:query_candidate_0001",
                    "query_text": "CODE_STRUCTURE_MAP_v1",
                    "purpose": "사용자가 명시한 문서명을 의미 검색 없이 정확 참조로 읽는다.",
                    "expected_signal": "filename_stem_exact로 하나의 Markdown artifact가 선택된다.",
                    "priority": 1,
                    "target_tool_name": "read_artifact",
                    "source_data_ids": source_data_ids,
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class MixedToolQueryPlannerFakeLLMAdapter:
    """Qwen처럼 L2 밖의 도구 후보를 섞어 내는 상황을 재현하는 adapter."""

    model_id = "mixed-tool-query-planner-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        source_data_ids = request.input_payload.get("source_data_ids")
        if not isinstance(source_data_ids, list) or not source_data_ids:
            source_data_ids = ["L1:goal_frame"]

        payload = {
            "planner_mode": "llm",
            "selected_candidate_id": "L2:query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:query_candidate_0001",
                    "query_text": "문서 목록 확인",
                    "purpose": "문서 목록을 먼저 보고 검색 범위를 좁히려는 후보다.",
                    "expected_signal": "문서 ID 목록",
                    "priority": 1,
                    "target_tool_name": "list_docs",
                    "source_data_ids": source_data_ids,
                },
                {
                    "candidate_id": "L2:query_candidate_0002",
                    "query_text": "송련 문서 메모리 인덱스 읽는 문서 종류",
                    "purpose": "현재 L2 단계에서 허용된 search_docs로 관련 근거 chunk를 찾는다.",
                    "expected_signal": "문서 메모리 인덱스가 읽는 문서 종류와 경로를 설명한 chunk",
                    "priority": 2,
                    "target_tool_name": "search_docs",
                    "source_data_ids": source_data_ids,
                },
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class RevisionQueryPlannerFakeLLMAdapter:
    """L2 revision query planner smoke test용 adapter."""

    model_id = "revision-query-planner-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        revision_input = request.input_payload.get("revision_input")
        if not isinstance(revision_input, dict):
            revision_input = {}
        source_data_ids = request.input_payload.get("source_data_ids")
        if not isinstance(source_data_ids, list) or not source_data_ids:
            source_data_ids = ["L2:revision_input:0001"]

        macro_goal = str(revision_input.get("macro_goal") or "internal document evidence").strip()
        l3_status = str(revision_input.get("l3_goal_status") or "partial").strip()
        previous_query = str(revision_input.get("previous_query_text") or "").strip()
        revised_query = f"{macro_goal} revised evidence after {l3_status}"
        if previous_query and revised_query == previous_query:
            revised_query = f"{previous_query} alternate evidence"

        payload = {
            "planner_mode": "revision_llm",
            "selected_candidate_id": "L2:revision_query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:revision_query_candidate_0001",
                    "query_text": revised_query,
                    "purpose": "L3 partial/failed feedback 이후 이전 검색 범위를 조정해 다시 근거 후보를 찾는다.",
                    "expected_signal": "이전 시도에서 부족했던 목표와 더 직접 연결된 내부 문서 chunk",
                    "priority": 1,
                    "target_tool_name": "search_docs",
                    "source_data_ids": source_data_ids,
                },
                {
                    "candidate_id": "L2:revision_query_candidate_0002",
                    "query_text": f"{macro_goal} unread candidate",
                    "purpose": "아직 읽지 않은 후보와 목표를 함께 고려해 보조 검색 후보를 만든다.",
                    "expected_signal": "unread candidate 또는 목표 보완과 연결된 내부 문서 chunk",
                    "priority": 2,
                    "target_tool_name": "search_docs",
                    "source_data_ids": source_data_ids,
                },
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class SongRyeonAllNodesFakeLLMAdapter:
    """전체 LLM 노드 배선 smoke test용 deterministic adapter."""

    model_id = "songryeon-all-nodes-fake-llm-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        prompt = request.prompt
        if "node_1 Router" in prompt:
            payload = self._node_1_payload(request)
        elif "L1 Goal Setter" in prompt:
            payload = self._l1_payload()
        elif "L3 Result Keeper" in prompt:
            payload = self._l3_payload(request)
        elif "node_2 Metainfo Boundary" in prompt:
            payload = self._node_2_payload(request)
        elif "node_3 Reporter" in prompt or "Final Reporter" in prompt:
            payload = self._node_3_payload(request)
        elif "node_4 Gatekeeper" in prompt:
            payload = self._node_4_payload()
        elif "Memory Relevance Selector" in prompt:
            payload = MemoryRelevanceNoneSelectedFakeLLMAdapter().complete(request).raw
        elif "L2" in prompt or "query" in prompt.lower():
            payload = QueryPlannerFakeLLMAdapter().complete(request).raw
        else:
            payload = {"response": "ok"}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )

    def _node_1_payload(self, request: LLMRequest) -> dict[str, object]:
        user_input = str(request.input_payload.get("user_input") or "")
        selected_recent_memory_count = self._selected_recent_memory_count(request.input_payload)
        document_required = any(
            keyword in user_input
            for keyword in ("문서", "검색", "내부", "송련", "너는", "누구", "정체", "소개")
        )
        memory_lookup_requested = any(keyword in user_input for keyword in ("기억", "방금", "이전"))
        if selected_recent_memory_count > 0 and not document_required:
            route = "2"
        elif document_required or memory_lookup_requested:
            route = "L"
        else:
            route = "2"
        return {
            "route": route,
            "route_reason": "사용자 입력이 내부 문서/기억 확인과 연결되는지 기준으로 라우팅했다.",
            "expected_next_0_mode": "targeted_memory_supply" if route == "L" else "final_trace_for_2",
            "route_confidence": 0.82,
            "needs_more_memory": False,
            "policy_flag": None,
        }

    def _selected_recent_memory_count(self, input_payload: dict[str, object]) -> int:
        context = input_payload.get("recent_memory_router_context")
        if not isinstance(context, dict):
            return 0
        value = context.get("selected_recent_memory_context_count")
        return value if isinstance(value, int) else 0

    def _l1_payload(self) -> dict[str, object]:
        return {
            "macro_goal": "produce_l_loop_evidence_material_for_current_request",
            "macro_goal_reason": "이번 L루프의 최종 목표는 사용자 요청에 답할 수 있도록 검색 후보, 읽은 문서, 부족 신호를 구분한 근거 재료를 확보하는 것이다.",
            "micro_goal": "prepare_first_document_lookup_action",
            "micro_goal_reason": "다음 단계인 L2가 사용자 요청 조건을 반영해 search_docs 또는 read_artifact에 넣을 첫 조회 조건을 준비해야 한다.",
            "evidence_requirement_kind": "multi_doc_relationship",
            "minimum_read_documents": 2,
            "requires_cross_document_analysis": True,
            "randomness_mode": "semantic_exploration",
            "l_loop_success_condition": "최소 2개 이상의 읽은 문서 추출본이나 그 부족 신호가 있어야 L루프가 정직하게 반환할 수 있다.",
            "requested_search_top_k": 5,
            "requested_max_tool_calls": 4,
            "requested_max_read_doc_calls": 2,
            "requested_max_query_attempts": 2,
            "budget_request_reason": "fake smoke에서는 여러 후보와 최소 2개 문서 열람 요청을 재현하기 위해 보수적 추가 예산을 요청한다.",
        }

    def _l3_payload(self, request: LLMRequest) -> dict[str, object]:
        candidate_count = int(request.input_payload.get("candidate_count") or 0)
        controller_decision = request.input_payload.get("controller_decision")
        status = "achieved" if candidate_count > 0 and controller_decision == "stop_success" else "partial"
        return {
            "achievement_status": status,
            "reason": "검색 후보 보존 여부와 controller 종료 신호를 구분해 운영 목표 달성 여부를 판정했다.",
            "macro_achievement_status": status,
            "macro_achievement_reason": "이번 L루프의 최종 근거 재료가 후보 또는 읽은 문서 형태로 확보되었는지 확인했다.",
            "micro_achievement_status": "achieved" if candidate_count > 0 else "partial",
            "micro_achievement_reason": "첫 조회 조건 실행과 후보 보존 결과가 있는지 확인했다.",
            "goal_match_status": "not_applicable",
            "goal_match_reason": "CODE_STATUS:no_specific_doc_hint_detected",
            "semantic_goal_match_status": "matched" if candidate_count > 0 else "partial",
            "semantic_goal_match_reason": "fake adapter confirms semantic fit for smoke testing.",
        }

    def _node_2_payload(self, request: LLMRequest) -> dict[str, object]:
        absolute_count = request.input_payload.get("absolute_info_count")
        relative_count = request.input_payload.get("relative_info_count")
        mixed_count = request.input_payload.get("mixed_info_count")
        return {
            "ready_for_report": True,
            "boundary_summary": (
                f"absolute_info {absolute_count}개, relative_info {relative_count}개, "
                f"mixed_info {mixed_count}개가 보고 경계에 들어왔다."
            ),
            "warnings": [],
            "excluded_claims": [],
        }

    def _node_3_payload(self, request: LLMRequest) -> dict[str, object]:
        extracts = request.input_payload.get("read_documents")
        if not isinstance(extracts, list):
            extracts = request.input_payload.get("document_extracts")
        selected_contexts = request.input_payload.get("selected_recent_memory_contexts")
        read_count = int(request.input_payload.get("available_document_extract_count") or 0)
        search_candidate_count = int(request.input_payload.get("available_search_candidate_document_count") or 0)
        runtime_task_count = int(request.input_payload.get("available_runtime_task_count") or 0)
        if isinstance(selected_contexts, list) and selected_contexts:
            first_context = selected_contexts[0] if isinstance(selected_contexts[0], dict) else {}
            raw_user_text = str(first_context.get("raw_user_text") or "")
            raw_assistant_text = str(first_context.get("raw_assistant_text") or "")
            combined = f"{raw_user_text}\n{raw_assistant_text}"
            if "파란노트" in combined:
                body_markdown = (
                    "선택된 최근 기억에 따르면, 네가 방금 말한 테스트 암호는 `파란노트`야.\n\n"
                    "근거 기준: 선택된 최근 기억의 복사된 이전 턴 원문 안에 그 표현이 있어."
                )
            else:
                body_markdown = (
                    "선택된 최근 기억은 들어왔지만, 그 복사본 안에서 테스트 암호를 확정할 수는 없어."
                )
        elif isinstance(extracts, list) and extracts:
            first = extracts[0] if isinstance(extracts[0], dict) else {}
            doc_id = first.get("document_name") or first.get("doc_id") or "읽은 문서"
            text = str(first.get("text") or "").strip()
            preview = " ".join(text.split())[:600]
            body_markdown = (
                f"이번 턴에서는 `{doc_id}` 문서를 읽은 문서 근거로 사용했어.\n\n"
                f"읽은 원문 미리보기: {preview}\n\n"
                "주의: 이것은 문서와 도구 결과에 근거한 보고이며, 문서 내용의 최종 진실성 판정은 아니다."
            )
        else:
            body_markdown = (
                "이번 턴에서는 보고 가능한 문서 원문 추출이 부족해. 사용자에게 답하려면 내부 문서 근거가 더 필요해."
            )
        return {"body_markdown": body_markdown}

    def _node_4_payload(self) -> dict[str, object]:
        return {
            "gate_status": "pass",
            "reason": "보고문이 제공된 node3_input_brief 범위 안에서 작성되었다.",
            "checked_claims": ["document_extract_grounding"],
            "unsupported_claims": [],
            "contradictions": [],
            "revision_targets": [],
        }
