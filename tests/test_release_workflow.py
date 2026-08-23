from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"


def test_release_workflow_is_published_release_only_and_checks_tag_version() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "release:\n    types: [published]" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert 'test "v${PACKAGE_VERSION}" = "${RELEASE_TAG}"' in workflow


def test_release_workflow_separates_verified_build_from_tokenless_oidc_publish() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.index("  build:") < workflow.index("  publish:")
    assert "if: github.event.release.prerelease == false" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    assert "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c" in workflow
    assert "python -m twine check dist/*" in workflow
    assert 'tpxlab-release-venv/bin/python" -m pip check' in workflow
    assert 'tpxlab-release-venv/bin/python" -c "import tpxlab' in workflow
    assert 'tpxlab" --help' in workflow
    assert "examples/overlapping_tpr.csv" in workflow
    assert "xvfb-run" in workflow
    publish = workflow.split("  publish:\n", maxsplit=1)[1]
    assert "runs-on: ubuntu-latest" in publish
    assert "name: pypi" in publish
    assert "id-token: write" in publish
    assert "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33" in publish
    assert "secrets." not in workflow
    assert "password:" not in workflow
