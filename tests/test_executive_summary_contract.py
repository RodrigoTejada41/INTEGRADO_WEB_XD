from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_executive_summary_captures_project_contract() -> None:
    summary = (ROOT / "cerebro_vivo" / "resumo_executivo.md").read_text(encoding="utf-8")

    assert "Plataforma comercial de sincronizacao de dados multi-tenant" in summary
    assert "agentes locais em MariaDB" in summary
    assert "API central em FastAPI" in summary
    assert "banco central em PostgreSQL" in summary
    assert "Nunca misturar dados entre empresas" in summary
    assert "Nunca armazenar dados com mais de 14 meses" in summary
    assert "runbook de producao unico" in summary


def test_readme_points_to_executive_summary() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "cerebro_vivo/resumo_executivo.md" in readme
    assert "visao curta do que o projeto e e como ele deve ser" in readme
