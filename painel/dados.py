import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

CSV_PADRAO = Path(__file__).resolve().parent.parent / "data" / "analise_curricular.csv"

CHAVE_CURSO = ["CÓDIGO E-MEC", "TIPO", "CENTRO", "CURSO", "MODALIDADE", "SEDE"]
PRIORIDADE_STATUS = ["IMPLANTADO", "AGUARDANDO IMPLANTAÇÃO", "EM ANDAMENTO", "SEM PROCESSO"]
SITUACAO_ATIVA = "EM ATIVIDADE"

COLUNAS_TEXTO = CHAVE_CURSO + ["TURNO", "SITUAÇÃO", "STATUS"]
COLUNAS_TEXTO_OPCIONAIS = ["PROCESSO", "RESOLUÇÃO"]
COLUNA_PPC_NOVO = "PPC_ANO_NOVO"
EPOCA_PLANILHA = datetime(1899, 12, 30)
PREFIXOS_NUMERICOS = ("CH_", "CRÉDITO", "CREDITO", "%", "QTDE")


def _limpar_espacos(texto):
    return " ".join(str(texto).split())


def _limpar_emec(texto):
    limpo = _limpar_espacos(texto)
    return limpo[:-2] if limpo.endswith(".0") else limpo


def periodo_ppc(valor):
    """Converte o PPC_ANO_NOVO para 'ano.semestre'. A planilha guarda uma data formatada como yyyy.m (mês = semestre)."""
    texto = _limpar_espacos(valor)
    if not texto or re.fullmatch(r"\d{4}\.\d", texto):
        return texto
    try:
        serial = float(texto)
    except ValueError:
        return texto
    data = EPOCA_PLANILHA + timedelta(days=serial)
    return f"{data.year}.{data.month}"


def _rank_status(status):
    if status in PRIORIDADE_STATUS:
        return PRIORIDADE_STATUS.index(status)
    return len(PRIORIDADE_STATUS)


def carregar_linhas(caminho=CSV_PADRAO):
    linhas = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    for coluna in COLUNAS_TEXTO:
        linhas[coluna] = linhas[coluna].map(_limpar_espacos)
    linhas["CÓDIGO E-MEC"] = linhas["CÓDIGO E-MEC"].map(_limpar_emec)
    for coluna in COLUNAS_TEXTO_OPCIONAIS:
        if coluna in linhas.columns:
            linhas[coluna] = linhas[coluna].map(_limpar_espacos)
    if COLUNA_PPC_NOVO in linhas.columns:
        linhas["PPC_NOVO_PERIODO"] = linhas[COLUNA_PPC_NOVO].map(periodo_ppc)
    for coluna in linhas.columns:
        if coluna.startswith(PREFIXOS_NUMERICOS):
            linhas[coluna] = pd.to_numeric(linhas[coluna], errors="coerce")
    return linhas


def cursos_unicos(linhas):
    """Uma linha por curso: agrupa turnos/ofertas pela chave e resolve o STATUS pela prioridade."""
    linhas = linhas.assign(_rank=linhas["STATUS"].map(_rank_status))
    registros = []
    for chave, grupo in linhas.groupby(CHAVE_CURSO, sort=False):
        grupo = grupo.sort_values("_rank", kind="stable")
        curso = grupo.iloc[0].drop("_rank").to_dict()
        curso["N_LINHAS"] = len(grupo)
        curso["TURNOS"] = ", ".join(t for t in dict.fromkeys(grupo["TURNO"]) if t)
        curso["STATUS_LINHAS"] = list(grupo["STATUS"])
        curso["CONFLITO_STATUS"] = grupo["STATUS"].nunique() > 1
        curso["CONFLITO_SITUACAO"] = grupo["SITUAÇÃO"].nunique() > 1
        curso["SEM_EMEC"] = chave[0] == ""
        curso["PPC_NOVO_PERIODO"] = next((p for p in grupo["PPC_NOVO_PERIODO"] if p), "") if "PPC_NOVO_PERIODO" in grupo.columns else ""
        curso["PROCESSOS_LINHAS"] = list(grupo["PROCESSO"]) if "PROCESSO" in grupo.columns else []
        curso["RESOLUCOES_LINHAS"] = list(grupo["RESOLUÇÃO"]) if "RESOLUÇÃO" in grupo.columns else []
        registros.append(curso)
    return pd.DataFrame(registros)


def cursos_ativos(cursos):
    return cursos[cursos["SITUAÇÃO"] == SITUACAO_ATIVA]


def resumo(linhas, cursos):
    return {
        "linhas": len(linhas),
        "cursos_unicos": len(cursos),
        "grupos_duplicados": int((cursos["N_LINHAS"] > 1).sum()),
        "conflitos_status": int(cursos["CONFLITO_STATUS"].sum()),
        "conflitos_situacao": int(cursos["CONFLITO_SITUACAO"].sum()),
        "sem_emec": int(cursos["SEM_EMEC"].sum()),
        "cursos_ativos": len(cursos_ativos(cursos)),
        "status_desconhecido": int((~cursos["STATUS"].isin(PRIORIDADE_STATUS)).sum()),
    }


if __name__ == "__main__":
    base = carregar_linhas()
    for nome, valor in resumo(base, cursos_unicos(base)).items():
        print(f"{nome}: {valor}")
