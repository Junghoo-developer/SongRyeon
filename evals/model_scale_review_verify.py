"""CLI for verifying a derived blinded model-scale review bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .model_scale_review_bundle import verify_model_scale_review_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="파생 blind review bundle의 파일·hash·provenance를 검증합니다."
    )
    parser.add_argument("review_bundle", type=Path)
    parser.add_argument("--expected-artifact-sha256")
    args = parser.parse_args(argv)
    try:
        result = verify_model_scale_review_bundle(
            args.review_bundle,
            expected_artifact_manifest_sha256=(
                args.expected_artifact_sha256
            ),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"review bundle 검증 실패: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
