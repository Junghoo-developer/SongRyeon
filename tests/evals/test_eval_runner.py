"""고정 case와 RecordedRun bundle runner의 재현성·출처 경계를 검사한다."""

import hashlib
import json
import shutil

import pytest

from evals.cli import main
from evals.runner import (
    DEFAULT_FIXTURE_RUNS_PATH,
    DEFAULT_MANIFEST_PATH,
    build_report,
    load_manifest,
    load_run_bundle,
    run_evaluation,
    write_report,
)


def _fixture_document():
    return json.loads(
        DEFAULT_FIXTURE_RUNS_PATH.read_text(encoding="utf-8")
    )


def _write_json(path, value):
    path.write_text(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_committed_manifest_has_ten_frozen_cases_and_verified_sources():
    manifest = load_manifest()

    assert manifest.manifest_id == "songryeon-p0-v1"
    assert manifest.case_set_status == "frozen-v1"
    assert len(manifest.cases) == 10
    assert len(manifest.questions) == 10
    assert len(manifest.source_fixtures) == 4
    assert len(manifest.boundary_fixtures) == 1
    assert manifest.project_fixture_root.is_dir()
    assert {
        tag
        for case in manifest.cases
        for tag in case.tags
    } >= {
        "execution_facts",
        "conflicting_memory",
        "missing_evidence",
        "long_files",
        "follow_up_turns",
        "subjective_requests",
        "prompt_injection",
        "path_safety",
        "answer_audit",
    }


def test_offline_fixture_report_is_deterministic_and_not_publishable(tmp_path):
    first_report = run_evaluation()
    second_report = run_evaluation()

    assert first_report == second_report
    assert first_report["benchmark_status"] == "fixture"
    assert first_report["review_status"] == "fixture"
    assert first_report["publishable"] is False
    assert first_report["coverage"] == {
        "case_count": 10,
        "system_count": 1,
        "recorded_run_count": 10,
        "complete_case_system_matrix": True,
    }
    assert first_report["provenance"]["uses_external_api"] is False
    assert first_report["provenance"]["raw_artifacts"] == []
    assert first_report["systems"]["fixture-contract"]["model_name"] == (
        "no-model"
    )
    # 1.0은 평가기 계약용 합성 입력의 결과일 뿐, 출력 경고가 실측으로
    # 오해되지 않도록 항상 함께 보존되어야 한다.
    assert first_report["summaries"]["fixture-contract"][
        "a_fact_exact_match_rate"
    ] == 1.0
    assert "FIXTURE ONLY" in first_report["warning"]

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    write_report(first_report, first_path)
    write_report(second_report, second_path)
    assert first_path.read_bytes() == second_path.read_bytes()


def test_runner_rejects_manifest_drift_in_recorded_runs(tmp_path):
    document = _fixture_document()
    document["manifest_sha256"] = "0" * 64
    runs_path = tmp_path / "runs.json"
    _write_json(runs_path, document)

    manifest = load_manifest()
    with pytest.raises(ValueError, match="manifest_sha256"):
        load_run_bundle(runs_path, manifest)


def test_runner_requires_one_run_per_case_for_every_system(tmp_path):
    document = _fixture_document()
    document["runs"].pop()
    runs_path = tmp_path / "incomplete.json"
    _write_json(runs_path, document)

    manifest = load_manifest()
    bundle = load_run_bundle(runs_path, manifest)
    with pytest.raises(ValueError, match="누락된 실행 조합"):
        build_report(manifest, bundle)


def test_runner_rejects_external_api_and_secret_metadata(tmp_path):
    manifest = load_manifest()
    external = _fixture_document()
    external["uses_external_api"] = True
    external_path = tmp_path / "external.json"
    _write_json(external_path, external)

    with pytest.raises(ValueError, match="외부 API"):
        load_run_bundle(external_path, manifest)

    secret = _fixture_document()
    secret["systems"]["fixture-contract"]["configuration"]["api_key"] = (
        "must-not-be-stored"
    )
    secret_path = tmp_path / "secret.json"
    _write_json(secret_path, secret)

    with pytest.raises(ValueError, match="비밀정보"):
        load_run_bundle(secret_path, manifest)


def test_live_replay_requires_and_verifies_raw_artifacts(tmp_path):
    manifest = load_manifest()
    raw_path = tmp_path / "raw.jsonl"
    raw_path.write_text(
        '{"event":"synthetic live-log stand-in"}\n',
        encoding="utf-8",
        newline="\n",
    )
    raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    document = _fixture_document()
    document["benchmark_status"] = "live"
    document["review_status"] = "draft"
    document["normalization_method"] = "manual-normalizer-v1"
    document["disclosure"] = "Local-model raw runs normalized for review."
    document["systems"]["fixture-contract"] = {
        "execution_profile": "contest-local",
        "model_provider": "ollama",
        "model_name": "fixture-local-model",
        "model_id": "sha256:test-model-id",
        "configuration": {
            "num_ctx": 16384,
            "seed": 42,
            "temperature": 0
        }
    }
    for run in document["runs"]:
        run["raw_artifact"] = {
            "path": "raw.jsonl",
            "sha256": raw_sha256
        }
    runs_path = tmp_path / "live_runs.json"
    _write_json(runs_path, document)

    bundle = load_run_bundle(runs_path, manifest)
    report = build_report(manifest, bundle)

    assert report["benchmark_status"] == "live"
    assert report["review_status"] == "draft"
    assert report["publishable"] is False
    assert len(report["provenance"]["raw_artifacts"]) == 10
    assert "LIVE DRAFT" in report["warning"]

    with pytest.raises(ValueError, match="덮어쓸 수 없습니다"):
        run_evaluation(
            runs_path=runs_path,
            output_path=raw_path,
        )

    reviewed_document = json.loads(
        runs_path.read_text(encoding="utf-8")
    )
    reviewed_document["review_status"] = "reviewed"
    reviewed_path = tmp_path / "reviewed_runs.json"
    _write_json(reviewed_path, reviewed_document)
    reviewed_bundle = load_run_bundle(reviewed_path, manifest)
    reviewed_report = build_report(manifest, reviewed_bundle)
    assert reviewed_report["publishable"] is False
    assert "NON-PUBLISHABLE" in reviewed_report["warning"]
    assert reviewed_report["publication_validation"] == {
        "raw_case_system_linkage_verified": True,
        "reviewer_identity_and_version_verified": False,
        "normalization_coverage_verified": False,
        "claim_spans_verified": False,
    }

    raw_path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        load_run_bundle(runs_path, manifest)


def test_source_fixture_tampering_is_detected(tmp_path):
    copied_cases = tmp_path / "cases"
    shutil.copytree(DEFAULT_MANIFEST_PATH.parent, copied_cases)
    source_path = copied_cases / "project" / "review_contract.py"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + "\nTAMPERED = True\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="source fixture SHA-256"):
        load_manifest(copied_cases / "manifest.json")


def test_unlisted_python_file_changes_the_frozen_project_identity(tmp_path):
    copied_cases = tmp_path / "cases"
    shutil.copytree(DEFAULT_MANIFEST_PATH.parent, copied_cases)
    (copied_cases / "project" / "extra.py").write_text(
        "EXTRA = True\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="Python 파일 집합"):
        load_manifest(copied_cases / "manifest.json")


def test_cli_writes_only_the_requested_report(tmp_path, capsys):
    output_path = tmp_path / "report.json"

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["publishable"] is False
    assert report["coverage"]["case_count"] == 10
    captured = capsys.readouterr()
    assert "fixture 평가 완료" in captured.out
