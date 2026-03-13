"""Contract tests for Cartola points naming consistency."""

from data_utils import POINTS_LABELS


def test_nao_eliminado_label_uses_official_wording():
    assert POINTS_LABELS["nao_eliminado_paredao"] == "Não Eliminado no Paredão"


def test_legacy_survived_label_not_used():
    assert "Sobreviveu ao Paredão" not in POINTS_LABELS.values()
