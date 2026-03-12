from pathlib import Path


def test_paredao_viz_has_no_python311_incompatible_nested_fstrings():
    source = Path("scripts/paredao_viz.py").read_text()
    offenders: list[tuple[int, str]] = []

    for lineno, line in enumerate(source.splitlines(), 1):
        has_nested_fstring = (
            "f'{f\"" in line
            or 'f"{f\'' in line
            or 'f"{f"' in line
            or "f'{f'" in line
        )
        if has_nested_fstring and "\\" in line:
            offenders.append((lineno, line.strip()))

    assert not offenders, (
        "Python 3.11 rejects nested f-strings that rely on backslash-escaped quotes. "
        f"Offending lines: {offenders}"
    )
