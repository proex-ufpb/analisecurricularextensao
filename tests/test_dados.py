from pathlib import Path

import pandas as pd
import pytest

from painel.dados import PRIORIDADE_STATUS, carregar_linhas, cursos_ativos, cursos_unicos, resumo

FIXTURE = Path(__file__).parent / "fixtures" / "analise_curricular_2026-09-24.csv"


def linha(emec="1", curso="PEDAGOGIA", turno="N", status="SEM PROCESSO", situacao="EM ATIVIDADE", **extra):
    base = {
        "CÓDIGO E-MEC": emec, "TIPO": "LICENCIATURA", "CENTRO": "CE", "CURSO": curso,
        "MODALIDADE": "PRESENCIAL", "SEDE": "JOÃO PESSOA", "TURNO": turno,
        "STATUS": status, "SITUAÇÃO": situacao,
    }
    base.update(extra)
    return base


def unicos(*linhas):
    return cursos_unicos(pd.DataFrame(linhas))


def test_turnos_do_mesmo_curso_contam_como_um():
    cursos = unicos(linha(turno="N"), linha(turno="M"), linha(turno="T"))
    assert len(cursos) == 1
    assert cursos.iloc[0]["N_LINHAS"] == 3
    assert cursos.iloc[0]["TURNOS"] == "N, M, T"


def test_emec_diferente_sao_cursos_diferentes():
    assert len(unicos(linha(emec="1"), linha(emec="2"))) == 2


def test_campo_da_chave_diferente_separa_cursos():
    assert len(unicos(linha(), linha(curso="HISTÓRIA"))) == 2


@pytest.mark.parametrize("status", [
    ["SEM PROCESSO", "EM ANDAMENTO", "SEM PROCESSO"],
    ["EM ANDAMENTO", "SEM PROCESSO"],
])
def test_conflito_prevalece_em_andamento(status):
    cursos = unicos(*[linha(status=s) for s in status])
    assert cursos.iloc[0]["STATUS"] == "EM ANDAMENTO"
    assert cursos.iloc[0]["CONFLITO_STATUS"]


def test_ordem_completa_de_prioridade():
    for i, vencedor in enumerate(PRIORIDADE_STATUS):
        perdedores = PRIORIDADE_STATUS[i + 1:]
        cursos = unicos(*[linha(status=s) for s in reversed(perdedores + [vencedor])])
        assert cursos.iloc[0]["STATUS"] == vencedor


def test_sem_conflito_quando_status_iguais():
    cursos = unicos(linha(status="IMPLANTADO"), linha(status="IMPLANTADO", turno="M"))
    assert not cursos.iloc[0]["CONFLITO_STATUS"]


def test_linha_representante_e_a_do_status_vencedor():
    cursos = unicos(
        linha(status="SEM PROCESSO", turno="N", **{"% CH_INTEGRALIZADA_EXTENSAO": float("nan")}),
        linha(status="IMPLANTADO", turno="M", **{"% CH_INTEGRALIZADA_EXTENSAO": 0.1}),
    )
    assert cursos.iloc[0]["% CH_INTEGRALIZADA_EXTENSAO"] == 0.1


def test_espacos_extras_nao_separam_o_mesmo_curso(tmp_path):
    csv = tmp_path / "a.csv"
    pd.DataFrame([linha(), linha(turno="M")]).assign(**{"CENTRO": ["CE ", " CE"]}).to_csv(csv, index=False)
    assert len(cursos_unicos(carregar_linhas(csv))) == 1


def test_emec_com_ponto_zero_e_normalizado(tmp_path):
    csv = tmp_path / "a.csv"
    pd.DataFrame([linha(emec="13418.0"), linha(emec="13418", turno="M")]).to_csv(csv, index=False)
    assert len(cursos_unicos(carregar_linhas(csv))) == 1


def test_curso_sem_emec_e_sinalizado_e_nao_e_agrupado_com_outros():
    cursos = unicos(linha(emec=""), linha(emec="5", curso="OUTRO"))
    assert cursos["SEM_EMEC"].sum() == 1
    assert len(cursos) == 2


def test_erros_da_planilha_viram_sem_dado(tmp_path):
    csv = tmp_path / "a.csv"
    pd.DataFrame([linha(**{"% CH_INTEGRALIZADA_EXTENSAO": "#DIV/0! (Function DIVIDE parameter 2 cannot be zero.)"})]).to_csv(csv, index=False)
    assert pd.isna(carregar_linhas(csv).iloc[0]["% CH_INTEGRALIZADA_EXTENSAO"])


def test_cursos_ativos_exclui_extincao():
    cursos = unicos(linha(emec="1"), linha(emec="2", situacao="EM EXTINÇÃO"))
    assert len(cursos_ativos(cursos)) == 1


def test_base_real_congelada():
    linhas = carregar_linhas(FIXTURE)
    dados = resumo(linhas, cursos_unicos(linhas))
    assert dados["linhas"] == 153
    assert dados["cursos_unicos"] == 131
    assert dados["grupos_duplicados"] == 21
    assert dados["conflitos_status"] == 3
    assert dados["status_desconhecido"] == 0


@pytest.mark.parametrize("emec,esperado", [("107552", "EM ANDAMENTO"), ("13394", "IMPLANTADO"), ("13418", "EM ANDAMENTO")])
def test_conflitos_da_base_real_resolvidos(emec, esperado):
    cursos = cursos_unicos(carregar_linhas(FIXTURE))
    curso = cursos[cursos["CÓDIGO E-MEC"] == emec].iloc[0]
    assert curso["CONFLITO_STATUS"]
    assert curso["STATUS"] == esperado
