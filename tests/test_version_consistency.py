from __future__ import annotations

import re
from importlib.metadata import version as installed_version
from pathlib import Path

import pytest

import tpxlab
from tpxlab import cli, gui

PROJECT_ROOT = Path(__file__).parents[1]


def test_version_is_consistent_across_package_and_release_surfaces() -> None:
    runtime_version = tpxlab.__version__
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (PROJECT_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == runtime_version
    assert installed_version("tpxlab") == runtime_version
    assert cli.__version__ == runtime_version
    assert gui.__version__ == runtime_version
    assert f"version: {runtime_version}" in citation
    assert f"## {runtime_version} -" in changelog
    assert f"the tested `{runtime_version}` development line" in readme
    assert f"/v{runtime_version}/tpxlab-{runtime_version}-py3-none-any.whl" not in readme
    assert f"Support status in v{runtime_version}" in readme


def test_pypi_metadata_has_human_author_four_urls_and_absolute_readme_image() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert 'authors = [{ name = "Hyun Dong Kim" }]' in pyproject
    for name in ("Homepage", "Documentation", "Issues", "Source"):
        assert re.search(rf"^{name} = \"https://", pyproject, flags=re.MULTILINE)
    assert (
        "![Actual TPxLab global deconvolution of the bundled overlapping example]"
        "(https://raw.githubusercontent.com/hdkim99/TPxLab/main/"
        "docs/tpxlab-global-deconvolution.png)"
    ) in readme


def test_cli_version_uses_runtime_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--version"])
    assert capsys.readouterr().out.strip() == f"TPxLab {tpxlab.__version__}"
