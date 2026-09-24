from pathlib import Path

from painel.dados import carregar_linhas, cursos_ativos, cursos_unicos
from painel.metricas import formatar_nome, resumo_status, status_por_centro

FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"


def base_real():
    cursos = cursos_unicos(carregar_linhas(FIXTURE))
    return cursos, cursos_ativos(cursos)


def test_formatar_nome_mantem_conectivos_em_minuscula():
    assert formatar_nome("TECNOLOGIA EM GESTÃO PÚBLICA") == "Tecnologia em Gestão Pública"
    assert formatar_nome("EAD") == "EAD"
    assert formatar_nome("JOÃO PESSOA") == "João Pessoa"


def test_totais_e_percentuais_usam_so_cursos_ativos():
    _, ativos = base_real()
    resumo = resumo_status(ativos)
    assert sum(item["total"] for item in resumo) == len(ativos) == 118
    assert round(sum(item["percentual"] for item in resumo), 6) == 100.0
    assert [item["status"] for item in resumo][0] == "IMPLANTADO"


def test_status_por_centro_soma_igual_ao_total_de_ativos():
    _, ativos = base_real()
    tabela = status_por_centro(ativos)
    assert tabela["TOTAL"].sum() == len(ativos)
    assert (tabela.drop(columns="TOTAL").sum(axis=1) == tabela["TOTAL"]).all()
    assert tabela["TOTAL"].is_monotonic_decreasing
