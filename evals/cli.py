"""모델 호출 없이 fixture 또는 정규화된 live run을 재평가하는 CLI."""

import argparse
import sys
from pathlib import Path

from .runner import (
    DEFAULT_FIXTURE_RUNS_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REPORT_PATH,
    run_evaluation,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "고정 manifest와 RecordedRun JSON을 모델 호출 없이 검증하고 "
            "결정론적으로 평가합니다."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=f"case manifest (기본값: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--runs",
        type=Path,
        default=DEFAULT_FIXTURE_RUNS_PATH,
        help=f"RecordedRun bundle (기본값: {DEFAULT_FIXTURE_RUNS_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"평가 보고서 출력 경로 (기본값: {DEFAULT_REPORT_PATH})",
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        report = run_evaluation(
            manifest_path=args.manifest,
            runs_path=args.runs,
            output_path=args.output,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"평가 중단: {error}", file=sys.stderr)
        return 1

    print(
        f"{report['benchmark_status']} 평가 완료: "
        f"{report['coverage']['case_count']} cases × "
        f"{report['coverage']['system_count']} systems"
    )
    print(report["warning"])
    print(f"보고서: {args.output}")
    return 0
