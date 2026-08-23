from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def test_general_ci_uses_only_the_measured_dgx_runner_and_blocks_external_or_bot_prs() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "runs-on: [self-hosted, dgx-spark]" in workflow
    assert "runs-on: ubuntu-latest" not in workflow
    assert workflow.count("github.actor == github.repository_owner") == 1
    assert workflow.count("github.event.pull_request.head.repo.full_name == github.repository") == 1
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow


def test_general_ci_pins_actions_and_runs_the_complete_scientific_package_path() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09" in workflow
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in workflow
    assert 'PIP_NO_CACHE_DIR: "1"' in workflow
    assert "cache: pip" not in workflow
    assert "/opt/catalysttwin-actions/shared-gui-runtime" in workflow
    assert 'echo "${TPXLAB_GUI_RUNTIME}/usr/bin" >> "${GITHUB_PATH}"' in workflow
    assert "LD_LIBRARY_PATH=" in workflow
    assert "TK_LIBRARY=" in workflow
    assert "command -v Xvfb" in workflow
    assert "command -v xvfb-run" in workflow
    assert "python -c 'import tkinter" in workflow
    for command in (
        "ruff format --check .",
        "ruff check .",
        "mypy src",
        "xvfb-run",
        "pytest",
        "tests/gui_widget_smoke.py",
        'python" -m build',
        "twine check",
        "pip check",
        "examples/synthetic_tpr.csv",
        "examples/overlapping_tpr.csv",
        "examples/overlapping_components.json",
        "scripts/ci/verify_arm64_runtime.py",
    ):
        assert command in workflow
