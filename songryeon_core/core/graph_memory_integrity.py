from __future__ import annotations

from dataclasses import asdict, dataclass

from songryeon_core.core.data_store import DataStore


GRAPH_MEMORY_REFERENCE_PREFIXES = ("graph:", "rloop:")
GRAPH_MEMORY_EDGE_DATA_TYPE_PREFIX = "graph_memory:edge:"


@dataclass(frozen=True)
class GraphMemoryIntegrityIssue:
    record_data_id: str
    record_data_type: str
    field_name: str
    missing_ref: str


@dataclass(frozen=True)
class GraphMemoryIntegrityReport:
    checked_record_count: int
    checked_source_ref_count: int
    checked_edge_count: int
    missing_source_refs: list[GraphMemoryIntegrityIssue]
    missing_edge_endpoints: list[GraphMemoryIntegrityIssue]

    @property
    def passed(self) -> bool:
        return not self.missing_source_refs and not self.missing_edge_endpoints

    def to_summary(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checked_record_count": self.checked_record_count,
            "checked_source_ref_count": self.checked_source_ref_count,
            "checked_edge_count": self.checked_edge_count,
            "missing_source_ref_count": len(self.missing_source_refs),
            "missing_edge_endpoint_count": len(self.missing_edge_endpoints),
            "missing_source_refs": [asdict(issue) for issue in self.missing_source_refs],
            "missing_edge_endpoints": [asdict(issue) for issue in self.missing_edge_endpoints],
        }


def audit_graph_memory_integrity(data_store: DataStore) -> GraphMemoryIntegrityReport:
    """Read-only graph/rloop reference audit for pre-export DataStore records."""

    records = data_store.list_records()
    record_ids = {record.data_id for record in records}
    checked_record_count = 0
    checked_source_ref_count = 0
    checked_edge_count = 0
    missing_source_refs: list[GraphMemoryIntegrityIssue] = []
    missing_edge_endpoints: list[GraphMemoryIntegrityIssue] = []

    for record in records:
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        checked_record_count += 1

        source_data_ids = payload.get("source_data_ids")
        if isinstance(source_data_ids, list):
            for index, ref in enumerate(source_data_ids):
                if not _is_graph_memory_ref(ref):
                    continue
                checked_source_ref_count += 1
                if ref not in record_ids:
                    missing_source_refs.append(
                        GraphMemoryIntegrityIssue(
                            record_data_id=record.data_id,
                            record_data_type=record.data_type,
                            field_name=f"source_data_ids[{index}]",
                            missing_ref=ref,
                        )
                    )

        if record.data_type.startswith(GRAPH_MEMORY_EDGE_DATA_TYPE_PREFIX):
            checked_edge_count += 1
            for field_name in ("from_node_id", "to_node_id"):
                ref = payload.get(field_name)
                if not _is_graph_memory_ref(ref):
                    continue
                if ref not in record_ids:
                    missing_edge_endpoints.append(
                        GraphMemoryIntegrityIssue(
                            record_data_id=record.data_id,
                            record_data_type=record.data_type,
                            field_name=field_name,
                            missing_ref=ref,
                        )
                    )

    return GraphMemoryIntegrityReport(
        checked_record_count=checked_record_count,
        checked_source_ref_count=checked_source_ref_count,
        checked_edge_count=checked_edge_count,
        missing_source_refs=missing_source_refs,
        missing_edge_endpoints=missing_edge_endpoints,
    )


def _is_graph_memory_ref(value: object) -> bool:
    return isinstance(value, str) and value.startswith(GRAPH_MEMORY_REFERENCE_PREFIXES)


__all__ = [
    "GRAPH_MEMORY_EDGE_DATA_TYPE_PREFIX",
    "GRAPH_MEMORY_REFERENCE_PREFIXES",
    "GraphMemoryIntegrityIssue",
    "GraphMemoryIntegrityReport",
    "audit_graph_memory_integrity",
]
