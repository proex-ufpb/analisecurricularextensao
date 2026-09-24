from pathlib import Path

import pandas as pd

CSV_PADRAO = Path(__file__).resolve().parent.parent / "data" / "analise_curricular.csv"

CHAVE_CURSO = ["CÓDIGO E-MEC", "TIPO", "CENTRO", "CURSO", "MODALIDADE", "SEDE"]
PRIORIDADE_STATUS = ["IMPLANTADO", "AGUARDANDO IMPLANTAÇÃO", "EM ANDAMENTO", "SEM PROCESSO"]
SITUACAO_ATIVA = "EM ATIVIDADE"

COLUNAS_TEXTO = CHAVE_CURSO + ["TURNO", "SITUAÇÃO", "STATUS"]
PREFIXOS_NUMERICOS = ("CH_", "CRÉDITO", "CREDITO", "%", "QTDE")


def _limpar_espacos(texto):
    return " ".join(str(texto).split())


def _limpar_emec(texto):
    limpo = _limpar_espacos(texto)
    return limpo[:-2] if limpo.endswith(".0") else limpo


def _rank_status(status):
    if status in PRIORIDADE_STATUS:
        return PRIORIDADE_STATUS.index(status)
    return len(PRIORIDADE_STATUS)


def carregar_linhas(caminho=CSV_PADRAO):
    linhas = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    for coluna in COLUNAS_TEXTO:
        linhas[coluna] = linhas[coluna].map(_limpar_espacos)
    linhas["CÓDIGO E-MEC"] = linhas["CÓDIGO E-MEC"].map(_limpar_emec)
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
