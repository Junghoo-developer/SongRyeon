"""Materialize every effective prompt and schema before the first model call."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from contracts import build_contract_unit, build_semantic_unit
from schemas import canonical_json, load_strict_json


ROOT = Path(__file__).resolve().parent


def load_json(path):
    return load_strict_json(path)


def add_identity(unit):
    effective = {
        "system_prompt": unit["system_prompt"],
        "user_prompt": unit["user_prompt"],
        "response_schema": unit["response_schema"],
    }
    unit["effective_request_sha256"] = hashlib.sha256(
        canonical_json(effective).encode("utf-8")
    ).hexdigest()
    return unit


def build_plan():
    manifest = load_json(ROOT / "manifest.json")
    contract_cases = load_json(ROOT / "contract_cases.json")["cases"]
    contract_units = [
        add_identity(build_contract_unit(case, ordinal=index))
        for index, case in enumerate(contract_cases, 1)
    ]

    semantic_units = []
    ordinal = 0
    for case_number, original_case in enumerate(manifest["cases"], 1):
        case = dict(original_case)
        source_path = (ROOT / case["source"]).resolve()
        if ROOT.resolve() not in source_path.parents:
            raise ValueError("source escapes calibration root")
        case["source_content"] = source_path.read_text(encoding="utf-8")
        batch = ("batch", case["claims"])
        singles = [("single", [claim]) for claim in case["claims"]]
        ordered = [batch, *singles] if case_number % 2 else [*singles, batch]
        for mode, claims in ordered:
            ordinal += 1
            semantic_units.append(
                add_identity(
                    build_semantic_unit(
                        case,
                        claims,
                        mode=mode,
                        ordinal=ordinal,
                    )
                )
            )

    return {
        "schema_version": 1,
        "contract_units": contract_units,
        "semantic_units": semantic_units,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "control" / "run_plan.json",
    )
    args = parser.parse_args()
    plan = build_plan()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as file:
        file.write(
            json.dumps(plan, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
    print(args.output)


if __name__ == "__main__":
    main()
