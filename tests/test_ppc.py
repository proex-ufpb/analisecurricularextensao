from pathlib import Path

import pandas as pd
import pytest

from painel.dados import carregar_linhas, cursos_ativos, cursos_unicos, periodo_ppc
from painel.metricas import (
    base_ppc,
    com_meta,
    formatar_variacao,
    linhas_ppc,
    modificacao_por_centro,
    resumo_modificacao,
)

FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"


@pytest.fixture(scope="module")
def ativos():
    return cursos_ativos(com_meta(cursos_unicos(carregar_linhas(FIXTURE))))


@pytest.mark.parametrize("valor,esperado", [
    (240.0, "+240"),
    (1020.0, "+1.020"),
    (-660.0, "-660"),
    (0.0, "0"),
    (float("nan"), "—"),
    (7.2072, "+7,2"),
])
def test_formatar_variacao(valor, esperado):
    assert formatar_variacao(valor) == esperado


def test_formatar_variacao_com_sufixo():
    assert formatar_variacao(7.2, "%") == "+7,2%"
    assert formatar_variacao(0.0, "%") == "0%"
    assert formatar_variacao(float("nan"), "%") == "—"


def test_periodo_do_ppc_antigo_usa_a_mesma_conversao():
    assert periodo_ppc("2015.2") == "2015.2"


def test_base_so_tem_cursos_ativos_com_modificacao_classificada(ativos):
    base = base_ppc(ativos)
    assert len(base) == 36
    assert set(base["M.CURRICULAR"]) <= {"AUMENTO", "MANUTENÇÃO", "REDUÇÃO", "NOVO"}


def test_resumo_da_modificacao_na_base_real(ativos):
    itens = resumo_modificacao(base_ppc(ativos))
    assert {i["rotulo"]: i["total"] for i in itens} == {"Aumento": 17, "Manutenção": 11, "Redução": 4, "Novo": 4}
    assert round(sum(i["percentual"] for i in itens), 6) == 100.0


def test_modificacao_por_centro_preserva_o_total(ativos):
    tabela = modificacao_por_centro(base_ppc(ativos))
    assert tabela["TOTAL"].sum() == 36
    assert tabela["TOTAL"].is_monotonic_decreasing
    assert (tabela.drop(columns="TOTAL").sum(axis=1) == tabela["TOTAL"]).all()


def test_linha_de_um_curso_com_aumento(ativos):
    linhas = linhas_ppc(base_ppc(ativos))
    biotec = next(l for l in linhas if l["curso"] == "Biotecnologia")
    assert biotec["modificacao_rotulo"] == "Aumento"
    assert (biotec["ppc_antigo"], biotec["ppc_novo"]) == ("2015.2", "2024.2")
    assert (biotec["ch_antiga"], biotec["ch_nova"]) == ("3.330", "3.570")
    assert (biotec["variacao"], biotec["variacao_pct"]) == ("+240", "+7,2%")


def test_variacao_bate_com_a_classificacao_da_planilha(ativos):
    for linha in linhas_ppc(base_ppc(ativos)):
        if linha["variacao"] == "—":
            continue
        sinal = linha["variacao"][0]
        if linha["modificacao"] == "AUMENTO":
            assert sinal == "+", linha["curso"]
        elif linha["modificacao"] == "MANUTENÇÃO":
            assert linha["variacao"] == "0", linha["curso"]
        elif linha["modificacao"] == "REDUÇÃO":
            assert sinal == "-", linha["curso"]


def test_curso_sem_carga_horaria_antiga_mostra_traco():
    base = pd.DataFrame([{
        "CENTRO": "CT", "CURSO": "NOVO CURSO", "CÓDIGO E-MEC": "1", "M.CURRICULAR": "NOVO",
        "PPC_ANTIGO_PERIODO": "", "PPC_NOVO_PERIODO": "2026.1",
        "CH_MÍNINA_ANTIGO": float("nan"), "CH_MÍNINA_NOVO": 3000.0,
    }])
    linha = linhas_ppc(base)[0]
    assert (linha["ch_antiga"], linha["ch_nova"]) == ("—", "3.000")
    assert (linha["variacao"], linha["variacao_pct"], linha["ppc_antigo"]) == ("—", "—", "—")
