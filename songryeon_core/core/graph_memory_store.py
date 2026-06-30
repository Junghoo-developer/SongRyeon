from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

from songryeon_core.core.graph_memory import CORE_EGO_ROOT_NODE_ID, TIME_AXIS_NODE_ID
from songryeon_core.core.schemas import (
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    GraphMemorySnapshotFrame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
    validate_graph_memory_snapshot_frame,
)


SONGRYEON_VESSEL_SERVICE_NAME = "songryeon-neo4j-vessel"
SONGRYEON_VESSEL_DATABASE_NAME = "songryeon_vessel"
SONGRYEON_GRAPH_NAMESPACE = "songryeon_core_graph_v0"


class GraphMemoryStoreProtocol(Protocol):
    """Storage boundary for graph memory frames.

    Implementations may use memory, JSONL, Neo4j, or another DB later, but they
    must accept and return SongRyeon graph-memory frames without inventing
    semantic fields.
    """

    def upsert_node(self, node: GraphMemoryNodeFrame) -> str:
        ...

    def upsert_edge(self, edge: GraphMemoryEdgeFrame) -> str:
        ...

    def get_node(self, node_id: str) -> GraphMemoryNodeFrame | None:
        ...

    def get_edge(self, edge_id: str) -> GraphMemoryEdgeFrame | None:
        ...

    def list_children(self, node_id: str, *, edge_kind: str | None = None) -> list[GraphMemoryNodeFrame]:
        ...

    def list_core_ego_entries(self, *, axis: str = "time") -> list[GraphMemoryNodeFrame]:
        ...

    def snapshot(self, *, snapshot_id: str, batch_id: str) -> GraphMemorySnapshotFrame:
        ...


class InMemoryGraphMemoryStore:
    """In-memory graph-memory adapter used to lock the external DB boundary."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphMemoryNodeFrame] = {}
        self._edges: dict[str, GraphMemoryEdgeFrame] = {}

    def upsert_node(self, node: GraphMemoryNodeFrame) -> str:
        validate_graph_memory_node_frame(node)
        existing = self._nodes.get(node.node_id)
        if existing is not None:
            if asdict(existing) != asdict(node):
                raise ValueError(f"graph memory node collision with different payload: {node.node_id}")
            return node.node_id
        self._nodes[node.node_id] = _copy_node(node)
        return node.node_id

    def upsert_edge(self, edge: GraphMemoryEdgeFrame) -> str:
        validate_graph_memory_edge_frame(edge)
        if edge.from_node_id not in self._nodes:
            raise ValueError(f"edge source node is missing: {edge.from_node_id}")
        if edge.to_node_id not in self._nodes:
            raise ValueError(f"edge target node is missing: {edge.to_node_id}")
        existing = self._edges.get(edge.edge_id)
        if existing is not None:
            if asdict(existing) != asdict(edge):
                raise ValueError(f"graph memory edge collision with different payload: {edge.edge_id}")
            return edge.edge_id
        self._edges[edge.edge_id] = _copy_edge(edge)
        return edge.edge_id

    def get_node(self, node_id: str) -> GraphMemoryNodeFrame | None:
        node = self._nodes.get(node_id)
        return _copy_node(node) if node is not None else None

    def get_edge(self, edge_id: str) -> GraphMemoryEdgeFrame | None:
        edge = self._edges.get(edge_id)
        return _copy_edge(edge) if edge is not None else None

    def list_children(
        self,
        node_id: str,
        *,
        edge_kind: str | None = None,
    ) -> list[GraphMemoryNodeFrame]:
        children: list[GraphMemoryNodeFrame] = []
        for edge in self._edges.values():
            if edge.from_node_id != node_id:
                continue
            if edge_kind is not None and edge.edge_kind != edge_kind:
                continue
            child = self._nodes.get(edge.to_node_id)
            if child is not None:
                children.append(_copy_node(child))
        return children

    def list_core_ego_entries(self, *, axis: str = "time") -> list[GraphMemoryNodeFrame]:
        if axis != "time":
            return []
        entries: list[GraphMemoryNodeFrame] = []
        for child in self.list_children(CORE_EGO_ROOT_NODE_ID):
            if child.node_id == TIME_AXIS_NODE_ID:
                entries.append(child)
        return entries

    def snapshot(self, *, snapshot_id: str, batch_id: str) -> GraphMemorySnapshotFrame:
        if not snapshot_id:
            raise ValueError("snapshot_id must not be empty")
        if not batch_id:
            raise ValueError("batch_id must not be empty")
        graph_node_ids = list(self._nodes.keys())
        graph_edge_ids = list(self._edges.keys())
        source_trace_ids = _unique_strings(
            [trace_id for node in self._nodes.values() for trace_id in node.source_trace_ids]
        )
        snapshot = GraphMemorySnapshotFrame(
            snapshot_id=snapshot_id,
            batch_id=batch_id,
            root_node_id=CORE_EGO_ROOT_NODE_ID,
            time_axis_node_id=TIME_AXIS_NODE_ID,
            graph_node_ids=graph_node_ids,
            graph_edge_ids=graph_edge_ids,
            node_kind_counts=_count_by(self._nodes.values(), "node_kind"),
            edge_kind_counts=_count_by(self._edges.values(), "edge_kind"),
            data_kind_counts=_count_by(self._nodes.values(), "data_kind"),
            source_graph_node_ids=list(graph_node_ids),
            source_trace_ids=source_trace_ids,
            source_data_ids=_unique_strings([*graph_node_ids, *graph_edge_ids]),
        )
        validate_graph_memory_snapshot_frame(snapshot)
        return snapshot

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)


def _copy_node(node: GraphMemoryNodeFrame) -> GraphMemoryNodeFrame:
    return GraphMemoryNodeFrame(**asdict(node))


def _copy_edge(edge: GraphMemoryEdgeFrame) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(**asdict(edge))


def _count_by(items: object, attr_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attr_name)
        if isinstance(value, str):
            counts[value] = counts.get(value, 0) + 1
    return counts


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = [
    "GraphMemoryStoreProtocol",
    "InMemoryGraphMemoryStore",
    "SONGRYEON_GRAPH_NAMESPACE",
    "SONGRYEON_VESSEL_DATABASE_NAME",
    "SONGRYEON_VESSEL_SERVICE_NAME",
]
