import pandas as pd

from painel.dados import PRIORIDADE_STATUS

ROTULOS_STATUS = {
    "IMPLANTADO": "Implantado",
    "AGUARDANDO IMPLANTAÇÃO": "Aguardando implantação",
    "EM ANDAMENTO": "Em andamento",
    "SEM PROCESSO": "Sem processo",
}

MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em", "para", "a", "o"}
MANTER_MAIUSCULAS = {"EAD"}


def formatar_nome(texto):
    palavras = []
    for i, palavra in enumerate(str(texto).split()):
        baixa = palavra.lower()
        if palavra in MANTER_MAIUSCULAS:
            palavras.append(palavra)
        elif i > 0 and baixa in MINUSCULAS:
            palavras.append(baixa)
        else:
            palavras.append(baixa[:1].upper() + baixa[1:])
    return " ".join(palavras)


def resumo_status(ativos):
    contagem = ativos["STATUS"].value_counts()
    total = len(ativos)
    return [
        {
            "status": status,
            "rotulo": ROTULOS_STATUS[status],
            "total": int(contagem.get(status, 0)),
            "percentual": (contagem.get(status, 0) / total * 100) if total else 0.0,
        }
        for status in PRIORIDADE_STATUS
    ]


def status_por_centro(ativos):
    tabela = pd.crosstab(ativos["CENTRO"], ativos["STATUS"])
    tabela = tabela.reindex(columns=PRIORIDADE_STATUS, fill_value=0)
    tabela["TOTAL"] = tabela.sum(axis=1)
    tabela["_centro"] = tabela.index
    return tabela.sort_values(["TOTAL", "_centro"], ascending=[False, True]).drop(columns="_centro")


def linhas_tabela(cursos):
    ordenados = cursos.sort_values(["CENTRO", "CURSO", "SEDE"])
    return [
        {
            "centro": c["CENTRO"],
            "curso": formatar_nome(c["CURSO"]),
            "tipo": formatar_nome(c["TIPO"]),
            "sede": formatar_nome(c["SEDE"]),
            "modalidade": formatar_nome(c["MODALIDADE"]),
            "turnos": c["TURNOS"] or "—",
            "emec": c["CÓDIGO E-MEC"] or "Não informado",
            "status": c["STATUS"],
            "status_rotulo": ROTULOS_STATUS.get(c["STATUS"], formatar_nome(c["STATUS"])),
            "situacao": formatar_nome(c["SITUAÇÃO"]),
            "ativo": c["SITUAÇÃO"] == "EM ATIVIDADE",
        }
        for _, c in ordenados.iterrows()
    ]
