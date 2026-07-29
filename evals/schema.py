"""비교 평가 입력과 결과의 모델 독립적인 데이터 형식.

이 형식은 자연어 답변에서 사실을 추출하지 않는다. 평가 fixture를 만드는
코드나 사람이 실행 사실과 코드 주장을 정규화해서 전달해야 한다. 따라서
평가 자체는 Ollama나 다른 LLM 없이 항상 같은 결과를 만든다.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType


MetricScalar = bool | int | float | str


def _validate_identifier(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}는 비어 있지 않은 문자열이어야 합니다.")


def _validate_unique_strings(values, field_name):
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name}는 tuple이어야 합니다.")

    for value in values:
        _validate_identifier(value, field_name)

    if len(set(values)) != len(values):
        raise ValueError(f"{field_name}에는 중복 값을 넣을 수 없습니다.")


def _validate_fact_tuple(values, field_name):
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name}는 tuple이어야 합니다.")

    if not all(isinstance(value, ExecutionFact) for value in values):
        raise TypeError(
            f"{field_name}에는 ExecutionFact만 넣을 수 있습니다."
        )

    if len(set(values)) != len(values):
        raise ValueError(f"{field_name}에는 중복 사실을 넣을 수 없습니다.")


def _freeze_extra_metrics(values):
    if not isinstance(values, Mapping):
        raise TypeError("extra_metrics는 mapping이어야 합니다.")

    frozen = {}

    for name, value in values.items():
        _validate_identifier(name, "extra_metrics key")

        if not isinstance(value, (bool, int, float, str)):
            raise TypeError(
                "extra_metrics 값은 bool, int, float, str 중 하나여야 합니다."
            )

        if isinstance(value, float) and not isfinite(value):
            raise ValueError("extra_metrics의 실수 값은 유한해야 합니다.")

        frozen[name] = value

    return MappingProxyType(frozen)


@dataclass(frozen=True, order=True)
class ExecutionFact:
    """코드가 확인한 실행 사실 하나의 정규화된 key-value 표현."""

    name: str
    value: str

    def __post_init__(self):
        _validate_identifier(self.name, "name")
        _validate_identifier(self.value, "value")

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value,
        }


@dataclass(frozen=True)
class EvaluationCase:
    """한 질문에서 기대하는 A 사실과 허용되는 코드 주장 fixture."""

    case_id: str
    expected_a_facts: tuple[ExecutionFact, ...] = ()
    supported_code_claims: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self):
        _validate_identifier(self.case_id, "case_id")
        _validate_fact_tuple(self.expected_a_facts, "expected_a_facts")
        _validate_unique_strings(
            self.supported_code_claims,
            "supported_code_claims",
        )
        _validate_unique_strings(self.tags, "tags")


@dataclass(frozen=True)
class RecordedRun:
    """모델 호출과 무관하게 저장할 수 있는 한 시스템의 고정 실행 결과."""

    case_id: str
    system_name: str
    reported_a_facts: tuple[ExecutionFact, ...] = ()
    code_claims: tuple[str, ...] = ()
    completed: bool = False
    tool_call_count: int = 0
    latency_ms: float = 0.0
    extra_metrics: Mapping[str, MetricScalar] = field(default_factory=dict)

    def __post_init__(self):
        _validate_identifier(self.case_id, "case_id")
        _validate_identifier(self.system_name, "system_name")
        _validate_fact_tuple(self.reported_a_facts, "reported_a_facts")
        _validate_unique_strings(self.code_claims, "code_claims")

        if not isinstance(self.completed, bool):
            raise TypeError("completed는 bool이어야 합니다.")

        if (
            type(self.tool_call_count) is not int
            or self.tool_call_count < 0
        ):
            raise ValueError("tool_call_count는 0 이상의 정수여야 합니다.")

        if (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, (int, float))
            or not isfinite(self.latency_ms)
            or self.latency_ms < 0
        ):
            raise ValueError("latency_ms는 0 이상의 유한한 수여야 합니다.")

        object.__setattr__(self, "latency_ms", float(self.latency_ms))
        object.__setattr__(
            self,
            "extra_metrics",
            _freeze_extra_metrics(self.extra_metrics),
        )


@dataclass(frozen=True)
class FactMatchMetrics:
    """기대 A 사실과 시스템이 보고한 A 사실의 비교 결과."""

    expected_count: int
    reported_count: int
    matched_count: int
    exact_match: bool
    precision: float
    recall: float
    missing_facts: tuple[ExecutionFact, ...]
    unexpected_facts: tuple[ExecutionFact, ...]

    def to_dict(self):
        return {
            "expected_count": self.expected_count,
            "reported_count": self.reported_count,
            "matched_count": self.matched_count,
            "exact_match": self.exact_match,
            "precision": self.precision,
            "recall": self.recall,
            "missing_facts": [
                fact.to_dict()
                for fact in self.missing_facts
            ],
            "unexpected_facts": [
                fact.to_dict()
                for fact in self.unexpected_facts
            ],
        }


@dataclass(frozen=True)
class EvaluationResult:
    """한 case의 핵심 지표와 향후 추가 지표를 함께 보존하는 결과."""

    case_id: str
    system_name: str
    a_execution_facts: FactMatchMetrics
    code_claim_count: int
    unsupported_code_claims: tuple[str, ...]
    completed: bool
    tool_call_count: int
    latency_ms: float
    extra_metrics: Mapping[str, MetricScalar] = field(default_factory=dict)

    def __post_init__(self):
        _validate_identifier(self.case_id, "case_id")
        _validate_identifier(self.system_name, "system_name")

        if not isinstance(self.a_execution_facts, FactMatchMetrics):
            raise TypeError(
                "a_execution_facts는 FactMatchMetrics여야 합니다."
            )

        if type(self.code_claim_count) is not int or self.code_claim_count < 0:
            raise ValueError("code_claim_count는 0 이상의 정수여야 합니다.")

        _validate_unique_strings(
            self.unsupported_code_claims,
            "unsupported_code_claims",
        )

        if len(self.unsupported_code_claims) > self.code_claim_count:
            raise ValueError(
                "근거 없는 주장 수는 전체 코드 주장 수를 넘을 수 없습니다."
            )

        if not isinstance(self.completed, bool):
            raise TypeError("completed는 bool이어야 합니다.")

        if (
            type(self.tool_call_count) is not int
            or self.tool_call_count < 0
        ):
            raise ValueError("tool_call_count는 0 이상의 정수여야 합니다.")

        if (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, (int, float))
            or not isfinite(self.latency_ms)
            or self.latency_ms < 0
        ):
            raise ValueError("latency_ms는 0 이상의 유한한 수여야 합니다.")

        object.__setattr__(self, "latency_ms", float(self.latency_ms))
        object.__setattr__(
            self,
            "extra_metrics",
            _freeze_extra_metrics(self.extra_metrics),
        )

    @property
    def unsupported_code_claim_count(self):
        return len(self.unsupported_code_claims)

    def to_dict(self):
        """JSON으로 바로 직렬화할 수 있는 기본형만 반환한다."""

        return {
            "case_id": self.case_id,
            "system_name": self.system_name,
            "metrics": {
                "a_execution_facts": self.a_execution_facts.to_dict(),
                "code_claims": {
                    "total_count": self.code_claim_count,
                    "unsupported_count": (
                        self.unsupported_code_claim_count
                    ),
                    "unsupported": list(
                        self.unsupported_code_claims
                    ),
                },
                "completed": self.completed,
                "tool_call_count": self.tool_call_count,
                "latency_ms": self.latency_ms,
                "extra": dict(self.extra_metrics),
            },
        }
