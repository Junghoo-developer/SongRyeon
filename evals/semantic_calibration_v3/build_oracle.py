"""Execute each fixture function in a fresh isolated CPython process."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from schemas import canonical_json, load_strict_json, strict_json_loads, validate_observation


ROOT = Path(__file__).resolve().parent
RUNNER = r'''import json, runpy, sys
namespace = runpy.run_path(sys.argv[1], run_name="__calibration_oracle__")
try:
    value = namespace[sys.argv[2]]()
    json.dumps(value, ensure_ascii=False, allow_nan=False)
    observation = {"kind": "return", "value": value, "exception": None}
except BaseException as failure:
    observation = {
        "kind": "raise",
        "value": None,
        "exception": type(failure).__name__,
    }
print(json.dumps(observation, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
'''


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(source, function):
    completed = subprocess.run(
        [sys.executable, "-B", "-I", "-c", RUNNER, str(source), function],
        cwd=source.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=True,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError(f"oracle emitted unexpected stdout for {source}:{function}")
    observation = strict_json_loads(lines[0])
    error = validate_observation(observation, allow_unknown=False)
    if error:
        raise ValueError(f"invalid oracle observation: {error}")
    return observation


def build_oracle():
    manifest_path = ROOT / "manifest.json"
    manifest = load_strict_json(manifest_path)
    calibration_root = ROOT.resolve()
    results = []
    seen_ids = set()
    for case in manifest["cases"]:
        source = (ROOT / case["source"]).resolve()
        if calibration_root not in source.parents:
            raise ValueError("manifest source escapes calibration root")
        claims = []
        for claim in case["claims"]:
            if claim["id"] in seen_ids:
                raise ValueError(f"duplicate claim id: {claim['id']}")
            seen_ids.add(claim["id"])
            actual = execute(source, claim["function"])
            verdict = (
                "SUPPORTED"
                if canonical_json(actual) == canonical_json(claim["proposition"])
                else "UNSUPPORTED"
            )
            claims.append(
                {
                    "id": claim["id"],
                    "verdict": verdict,
                    "observation": actual,
                }
            )
        results.append(
            {
                "case_id": case["case_id"],
                "difficulty": case["difficulty"],
                "source": case["source"],
                "source_sha256": sha256(source),
                "claims": claims,
            }
        )
    return {
        "schema_version": 1,
        "python_version": sys.version,
        "manifest_sha256": sha256(manifest_path),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "control" / "oracle_results.json",
    )
    args = parser.parse_args()
    oracle = build_oracle()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as file:
        file.write(
            json.dumps(oracle, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
    print(args.output)


if __name__ == "__main__":
    main()
