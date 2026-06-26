from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class JSONValidationResult:
    """LLM JSON 출력 검증 결과."""

    ok: bool
    payload: dict[str, object] | None = None
    error: str | None = None


def parse_json_object(text: str) -> JSONValidationResult:
    """LLM text가 JSON object인지 확인한다."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return JSONValidationResult(ok=False, error=f"json_decode_error: {exc}")
    if not isinstance(payload, dict):
        return JSONValidationResult(ok=False, error="json_root_is_not_object")
    return JSONValidationResult(ok=True, payload=payload)
