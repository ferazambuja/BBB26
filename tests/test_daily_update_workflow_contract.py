from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "daily-update.yml"
)


def test_integrity_audit_runs_before_pytest():
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    tests_idx = content.index("- name: Run tests")
    build_idx = content.index("- name: Build derived data")
    audit_idx = content.index("- name: Run integrity audit")

    assert build_idx < audit_idx < tests_idx
