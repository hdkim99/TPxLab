from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.validate_public_data import PublicDataValidationError, load_manifest, validate_archive

PROJECT_ROOT = Path(__file__).parents[1]
MANIFEST = PROJECT_ROOT / "docs" / "public-data-manifest.json"
SOURCES = PROJECT_ROOT / "docs" / "public-data-sources.md"


def test_public_data_manifest_pins_source_without_vendoring_raw_data() -> None:
    manifest = load_manifest(MANIFEST)
    documentation = SOURCES.read_text(encoding="utf-8")

    assert manifest["dataset_id"] == "TPX-PUB-001"
    assert manifest["record_doi"] == "10.5281/zenodo.21884075"
    assert manifest["dataset_license"] == "CC-BY-4.0"
    assert manifest["article_license"] == "CC-BY-NC-ND-4.0"
    assert manifest["analysis"]["peak_polarity"] == "negative"
    assert manifest["analysis"]["calibration"] is None
    assert manifest["derived_ramp_selection"]["supplement_reported_rate_degC_per_min"] == 10
    assert manifest["archive"]["sha256"] in documentation
    assert "4.97-4.98" in documentation.replace("\u2013", "-")
    assert "must not report H2 consumption in mmol/g" in documentation

    source_suffixes = {".csv", ".xlsx", ".zip", ".rar", ".opj"}
    vendored = [
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in source_suffixes
        and "examples" not in path.parts
        and "dist" not in path.parts
        and ".git" not in path.parts
        and ".venv" not in path.parts
    ]
    assert vendored == []


def test_public_data_validation_rejects_archive_digest_mismatch(tmp_path: Path) -> None:
    member_name = "curve.csv"
    member_data = b"time,temperature,signal\n0,20,0\n"
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(member_name, member_data)
    manifest = {
        "archive": {
            "size_bytes": archive_path.stat().st_size,
            "sha256": "0" * 64,
        },
        "members": [
            {
                "path": member_name,
                "size_bytes": len(member_data),
                "sha256": hashlib.sha256(member_data).hexdigest(),
            }
        ],
    }
    with pytest.raises(PublicDataValidationError, match="archive SHA-256"):
        validate_archive(archive_path, manifest)


def test_public_data_manifest_json_is_canonical_and_all_members_have_sha256() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"].endswith("/0.1-draft")
    assert len(manifest["archive"]["sha256"]) == 64
    assert len(manifest["members"]) == 6
    assert all(len(member["sha256"]) == 64 for member in manifest["members"])
    analysis_members = [
        member for member in manifest["members"] if member["analysis_role"] == "tpr_validation"
    ]
    assert len(analysis_members) == 4
    assert all(member["components"] for member in analysis_members)
