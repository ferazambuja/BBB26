from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RELACOES_QMD = REPO_ROOT / "relacoes.qmd"


def test_relacoes_qmd_formats_structured_sincerao_contradictions():
    content = RELACOES_QMD.read_text(encoding="utf-8")

    assert "sc.get('text', str(sc))" not in content
    assert "sc.get('ator'" in content or 'sc.get("ator"' in content
    assert "sc.get('alvo'" in content or 'sc.get("alvo"' in content
    assert "sc.get('tema'" in content or 'sc.get("tema"' in content
