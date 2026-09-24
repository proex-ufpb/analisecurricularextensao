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


COLUNA_PERCENTUAL = "% CH_INTEGRALIZADA_EXTENSAO"
LIMITE_MINIMO = 0.10
LIMITE_MAXIMO = 0.15
TOLERANCIA = 1e-9

CLASSES_META = ["ABAIXO", "DENTRO", "ACIMA", "NAO_IMPLANTADO"]
ROTULOS_META = {
    "ABAIXO": "Abaixo de 10%",
    "DENTRO": "Entre 10% e 15%",
    "ACIMA": "Acima de 15%",
    "NAO_IMPLANTADO": "Não implantado",
}


def classificar_meta(percentual):
    if pd.isna(percentual) or percentual <= TOLERANCIA:
        return "NAO_IMPLANTADO"
    if percentual < LIMITE_MINIMO - TOLERANCIA:
        return "ABAIXO"
    if percentual > LIMITE_MAXIMO + TOLERANCIA:
        return "ACIMA"
    return "DENTRO"


def com_meta(cursos):
    return cursos.assign(META=cursos[COLUNA_PERCENTUAL].map(classificar_meta))


def resumo_meta(ativos):
    """Classes de conformidade; o percentual das três primeiras é sobre os cursos com percentual maior que zero."""
    contagem = ativos["META"].value_counts()
    com_dado = len(ativos) - int(contagem.get("NAO_IMPLANTADO", 0))
    itens = []
    for classe in CLASSES_META:
        total = int(contagem.get(classe, 0))
        base = len(ativos) if classe == "NAO_IMPLANTADO" else com_dado
        itens.append({
            "classe": classe,
            "rotulo": ROTULOS_META[classe],
            "total": total,
            "percentual": (total / base * 100) if base else 0.0,
            "base": "dos cursos ativos" if classe == "NAO_IMPLANTADO" else "dos cursos implantados",
        })
    return itens, com_dado


def meta_por_centro(ativos):
    tabela = pd.crosstab(ativos["CENTRO"], ativos["META"]).reindex(columns=CLASSES_META, fill_value=0)
    tabela["TOTAL"] = tabela.sum(axis=1)
    tabela["_centro"] = tabela.index
    return tabela.sort_values(["TOTAL", "_centro"], ascending=[False, True]).drop(columns="_centro")


def formatar_percentual(valor):
    if pd.isna(valor):
        return "—"
    return f"{valor * 100:.2f}".replace(".", ",") + "%"


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
            "percentual": formatar_percentual(c[COLUNA_PERCENTUAL]),
            "meta": c["META"] if c["SITUAÇÃO"] == "EM ATIVIDADE" else "",
            "meta_rotulo": ROTULOS_META[c["META"]] if c["SITUAÇÃO"] == "EM ATIVIDADE" else "—",
        }
        for _, c in ordenados.iterrows()
    ]


def linhas_percentuais(ativos):
    """Cursos ativos com percentual de extensão (não implantados ficam de fora), do menor para o maior."""
    implantados = ativos[ativos["META"] != "NAO_IMPLANTADO"]
    ordenados = implantados.sort_values([COLUNA_PERCENTUAL, "CENTRO", "CURSO"], kind="stable")
    return [
        {
            "centro": c["CENTRO"],
            "curso": formatar_nome(c["CURSO"]),
            "emec": c["CÓDIGO E-MEC"] or "Não informado",
            "percentual": formatar_percentual(c[COLUNA_PERCENTUAL]),
        }
        for _, c in ordenados.iterrows()
    ]


COMPONENTES = ["BASICA", "COMPLEMENTAR", "OPTATIVA", "FLEXIVEL"]
COLUNAS_COMPONENTES = {
    "BASICA": "CH_BASICA_PROFISSIONAL_EXT",
    "COMPLEMENTAR": "CH_COMPL_OBRIG_EXT",
    "OPTATIVA": "CH_OPTATIVA_EXT",
    "FLEXIVEL": "CH_FLEXÍVEL_EXT",
}
ROTULOS_COMPONENTES = {
    "BASICA": "Básica e profissional",
    "COMPLEMENTAR": "Complementar obrigatória",
    "OPTATIVA": "Optativa",
    "FLEXIVEL": "Flexível",
}
COLUNA_TOTAL_EXT = "CH_TOTAL_EXT"


def formatar_horas(valor):
    if pd.isna(valor) or valor == 0:
        return "—"
    if float(valor).is_integer():
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")


def cursos_com_extensao(ativos):
    """Cursos ativos com carga horária de extensão; célula vazia de componente conta como zero hora."""
    base = ativos[ativos["META"] != "NAO_IMPLANTADO"].copy()
    for coluna in COLUNAS_COMPONENTES.values():
        base[coluna] = base[coluna].fillna(0)
    base[COLUNA_TOTAL_EXT] = base[COLUNA_TOTAL_EXT].fillna(0)
    return base


def resumo_componentes(base):
    total = base[COLUNA_TOTAL_EXT].sum()
    itens = []
    for chave in COMPONENTES:
        coluna = COLUNAS_COMPONENTES[chave]
        horas = float(base[coluna].sum())
        itens.append({
            "chave": chave,
            "rotulo": ROTULOS_COMPONENTES[chave],
            "horas": formatar_horas(horas),
            "percentual": (horas / total * 100) if total else 0.0,
            "cursos": int((base[coluna] > 0).sum()),
        })
    obrigatorias = base["CH_BASICA_PROFISSIONAL_EXT"] + base["CH_COMPL_OBRIG_EXT"]
    livres = base["CH_OPTATIVA_EXT"] + base["CH_FLEXÍVEL_EXT"]
    destaques = {
        "so_obrigatorias": int(((livres == 0) & (base[COLUNA_TOTAL_EXT] > 0)).sum()),
        "maioria_livre": int((livres > obrigatorias).sum()),
        "total_horas": formatar_horas(total),
    }
    return itens, destaques


def componentes_por_centro(base):
    colunas = list(COLUNAS_COMPONENTES.values())
    tabela = base.groupby("CENTRO")[colunas].sum()
    tabela.columns = COMPONENTES
    tabela["TOTAL"] = tabela.sum(axis=1)
    tabela["_centro"] = tabela.index
    return tabela.sort_values(["TOTAL", "_centro"], ascending=[False, True]).drop(columns="_centro")


def linhas_componentes(base):
    ordenados = base.sort_values(["CENTRO", "CURSO"])
    linhas = []
    for _, c in ordenados.iterrows():
        total = c[COLUNA_TOTAL_EXT]
        obrigatorias = c["CH_BASICA_PROFISSIONAL_EXT"] + c["CH_COMPL_OBRIG_EXT"]
        linha = {
            "centro": c["CENTRO"],
            "curso": formatar_nome(c["CURSO"]),
            "emec": c["CÓDIGO E-MEC"] or "Não informado",
            "total": formatar_horas(total),
            "obrigatorias": (f"{obrigatorias / total * 100:.0f}%" if total else "—"),
            "integralizado": formatar_percentual(c[COLUNA_PERCENTUAL]),
        }
        for chave, coluna in COLUNAS_COMPONENTES.items():
            linha[chave] = formatar_horas(c[coluna])
        linhas.append(linha)
    return linhas
