"""네 노드의 프롬프트·스키마·파서를 한곳에서 연결한다.

``runner.py``는 노드 이동만 읽을 수 있게 하고, 모델에게 무엇을 보내는지는
이 파일에서 확인할 수 있게 분리했다. 매 메서드는 호출 직전에 턴 시작 때
고정한 기준점부터 현재 끝까지의 같은 시야를 다시 읽는다.
"""

from functools import partial
from pathlib import Path

from llm.structured import request_structured_output
from memory import (
    AgentMemoryFloor,
    TurnMemoryContext,
    format_agent_memory,
    load_frozen_agent_memory,
)
from nodes import (
    DEFAULT_MAX_SELECTED_CHARACTERS,
    NODE1_ACTION_SCHEMA,
    NODE1_RECOVERY_CHOICE_SCHEMA,
    NODE3_ANSWER_SCHEMA,
    REVIEW_DECISION_SCHEMA,
    parse_node1_action,
    parse_node1_recovery_choice,
    parse_node1_recovery_retention,
    parse_node1_tool_decision,
    parse_node3_answer,
    parse_review_decision,
    build_text_chunks,
    node1_recovery_retention_schema,
    node1_tool_decision_schema,
)
from prompts import (
    build_node1_action_prompts,
    build_node1_recovery_choice_prompts,
    build_node1_recovery_retention_prompts,
    build_node1_tool_prompts,
    build_node2_prompts,
    build_node3_prompts,
    build_node4_prompts,
)

from .state import (
    NODE1,
    NODE2,
    NODE3,
    NODE4,
    OmittedToolCandidate,
)


NODE1_NUM_PREDICT = 1_024
REVIEW_NUM_PREDICT = 256
NODE3_NUM_PREDICT = 2_048


class NodeCaller:
    """현재 사용자 턴에 고정된 모델 호출 도우미."""

    def __init__(
        self,
        *,
        client,
        user_input,
        turn_id,
        memory_path,
        memory_floor,
        turn_memory_context,
    ):
        if not isinstance(memory_floor, AgentMemoryFloor):
            raise TypeError("memory_floor는 AgentMemoryFloor여야 합니다.")
        if not isinstance(turn_memory_context, TurnMemoryContext):
            raise TypeError(
                "turn_memory_context는 TurnMemoryContext여야 합니다."
            )

        self.client = client
        self.user_input = user_input
        self.turn_id = turn_id
        self.memory_path = Path(memory_path)
        self.memory_floor = memory_floor
        self.turn_memory_context = turn_memory_context

    def _shared_memory(self):
        """원본이 아니라 가공된 공통 에이전트 시야만 문자열로 만든다."""

        return format_agent_memory(
            load_frozen_agent_memory(
                self.memory_floor,
                self.memory_path,
            )
        )

    def _ask(
        self,
        *,
        node_name,
        prompts,
        schema,
        parser,
        num_predict,
    ):
        system_prompt, user_prompt = prompts
        return request_structured_output(
            client=self.client,
            node_name=node_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=schema,
            parser=parser,
            num_predict=num_predict,
            turn_id=self.turn_id,
            memory_path=self.memory_path,
        )

    def ask_node1_action(self):
        """Node1이 도구를 쓸지 Node2로 갈지 묻는다."""

        return self._ask(
            node_name=NODE1,
            prompts=build_node1_action_prompts(
                self.user_input,
                self._shared_memory(),
                turn_memory_context=self.turn_memory_context,
            ),
            schema=NODE1_ACTION_SCHEMA,
            parser=parse_node1_action,
            num_predict=NODE1_NUM_PREDICT,
        )

    def ask_node1_after_tool(self, observation):
        """이번 도구 원문만 일시적으로 보여주고 보존·다음 행동을 묻는다."""

        raw_text = observation.result.observation_text
        allow_full = (
            len(raw_text) <= DEFAULT_MAX_SELECTED_CHARACTERS
        )
        chunk_ids = None

        if not allow_full:
            chunk_ids = [
                chunk.chunk_id
                for chunk in build_text_chunks(
                    raw_text,
                    DEFAULT_MAX_SELECTED_CHARACTERS,
                )
            ]

        response_schema = node1_tool_decision_schema(
            allow_full=allow_full,
            chunk_ids=chunk_ids,
        )
        return self._ask(
            node_name=NODE1,
            prompts=build_node1_tool_prompts(
                self.user_input,
                self._shared_memory(),
                turn_memory_context=self.turn_memory_context,
                tool_name=observation.result.tool_name,
                tool_success=observation.result.success,
                raw_text=raw_text,
                response_schema=response_schema,
            ),
            schema=response_schema,
            parser=partial(
                parse_node1_tool_decision,
                raw_text=raw_text,
            ),
            num_predict=NODE1_NUM_PREDICT,
        )

    @staticmethod
    def _recovery_candidate_summaries(candidates):
        """원문 ID를 숨긴 채 Node1이 후보를 구별할 작은 목록을 만든다."""

        if not isinstance(candidates, list) or not candidates:
            raise ValueError("복구 후보가 하나 이상 필요합니다.")

        summaries = []

        for candidate_number, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, OmittedToolCandidate):
                raise TypeError(
                    "모든 복구 후보는 OmittedToolCandidate여야 합니다."
                )

            observation = candidate.observation
            raw_text = observation.result.observation_text
            summaries.append(
                {
                    "arguments": observation.result.arguments,
                    "candidate_number": candidate_number,
                    "character_length": len(raw_text),
                    "previous_review": candidate.review,
                    "tool_name": observation.result.tool_name,
                }
            )

        return summaries

    def ask_node1_recovery_choice(self, candidates):
        """전부 omit된 성공 원문 중 다시 공개할 후보 하나를 고르게 한다."""

        summaries = self._recovery_candidate_summaries(candidates)
        return self._ask(
            node_name=NODE1,
            prompts=build_node1_recovery_choice_prompts(
                self.user_input,
                self._shared_memory(),
                summaries,
                turn_memory_context=self.turn_memory_context,
            ),
            schema=NODE1_RECOVERY_CHOICE_SCHEMA,
            parser=partial(
                parse_node1_recovery_choice,
                candidate_count=len(candidates),
            ),
            num_predict=REVIEW_NUM_PREDICT,
        )

    def ask_node1_recovery_retention(
        self,
        candidate,
        candidate_number,
    ):
        """고른 원문 하나를 다시 보여주고 full/excerpt만 선택하게 한다."""

        if not isinstance(candidate, OmittedToolCandidate):
            raise TypeError("candidate는 OmittedToolCandidate여야 합니다.")

        summaries = self._recovery_candidate_summaries([candidate])
        candidate_summary = {
            **summaries[0],
            "candidate_number": candidate_number,
        }
        raw_text = candidate.observation.result.observation_text
        allow_full = (
            len(raw_text) <= DEFAULT_MAX_SELECTED_CHARACTERS
        )
        chunk_ids = None

        if not allow_full:
            chunk_ids = [
                chunk.chunk_id
                for chunk in build_text_chunks(
                    raw_text,
                    DEFAULT_MAX_SELECTED_CHARACTERS,
                )
            ]

        response_schema = node1_recovery_retention_schema(
            allow_full=allow_full,
            chunk_ids=chunk_ids,
        )
        return self._ask(
            node_name=NODE1,
            prompts=build_node1_recovery_retention_prompts(
                self.user_input,
                self._shared_memory(),
                candidate_summary=candidate_summary,
                raw_text=raw_text,
                turn_memory_context=self.turn_memory_context,
                response_schema=response_schema,
            ),
            schema=response_schema,
            parser=partial(
                parse_node1_recovery_retention,
                raw_text=raw_text,
            ),
            num_predict=NODE1_NUM_PREDICT,
        )

    def ask_node2_review(self):
        """Node2에게 현재 공개 증거의 충분성을 묻는다."""

        return self._ask(
            node_name=NODE2,
            prompts=build_node2_prompts(
                self.user_input,
                self._shared_memory(),
                turn_memory_context=self.turn_memory_context,
            ),
            schema=REVIEW_DECISION_SCHEMA,
            parser=parse_review_decision,
            num_predict=REVIEW_NUM_PREDICT,
        )

    def ask_node3_answer(self):
        """Node3에게 사용자 답변 후보를 작성하게 한다."""

        return self._ask(
            node_name=NODE3,
            prompts=build_node3_prompts(
                self.user_input,
                self._shared_memory(),
                turn_memory_context=self.turn_memory_context,
            ),
            schema=NODE3_ANSWER_SCHEMA,
            parser=parse_node3_answer,
            num_predict=NODE3_NUM_PREDICT,
        )

    def ask_node4_review(self, candidate_answer):
        """Node4에게 현재 답변과 A 기록의 일치 여부를 묻는다."""

        return self._ask(
            node_name=NODE4,
            prompts=build_node4_prompts(
                self.user_input,
                self._shared_memory(),
                candidate_answer,
                turn_memory_context=self.turn_memory_context,
            ),
            schema=REVIEW_DECISION_SCHEMA,
            parser=parse_review_decision,
            num_predict=REVIEW_NUM_PREDICT,
        )
