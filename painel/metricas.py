import re

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


def formatar_percentual(valor):
    if pd.isna(valor):
        return "—"
    return f"{valor * 100:.2f}".replace(".", ",") + "%"


PADRAO_PROCESSO = re.compile(r"^\d{5}\.\d{6}/\d{4}-\d{2}$")
PADRAO_RESOLUCAO = re.compile(r"^N\S?\s*(\d{1,3})\s*/\s*(\d{4})")


def _unicos(valores):
    return list(dict.fromkeys(valores))


def formatar_processo(valores):
    """Números de processo SIPAC válidos do curso; sem eles, o motivo registrado na planilha."""
    validos = _unicos(v for v in valores if PADRAO_PROCESSO.match(v))
    if validos:
        return "; ".join(validos)
    if any("EXCE" in v.upper() for v in valores):
        return "Sem processo (exceção)"
    if any(v.upper().startswith("N") and "CONSTA" in v.upper() for v in valores):
        return "Não consta"
    return "—"


def formatar_resolucao(valores):
    """Resolução CONSEPE no formato XX/XXXX; 'Pendente' quando a planilha indica pendência."""
    numeros = []
    for v in valores:
        achado = PADRAO_RESOLUCAO.match(v)
        if achado:
            numeros.append(f"{int(achado.group(1)):02d}/{achado.group(2)}")
    numeros = _unicos(numeros)
    if numeros:
        return "; ".join(numeros)
    if any(v.upper() == "PENDENTE" for v in valores):
        return "Pendente"
    return "—"


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
            "processo": formatar_processo(c.get("PROCESSOS_LINHAS", [])),
            "resolucao": formatar_resolucao(c.get("RESOLUCOES_LINHAS", [])),
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
    return itens, formatar_horas(total)


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


COLUNA_OFERTA = "%CH_EXT_DISPONÍVEL"
COLUNA_HORAS_EXIGIDAS = "CH_INTEGRALIZADA_EXTENSAO"


def _margem_pp(base):
    return (base[COLUNA_OFERTA] - base[COLUNA_PERCENTUAL]) * 100


def formatar_pp(valor):
    if abs(valor) <= 1e-6:
        return "0,00"
    return f"{valor:+.2f}".replace(".", ",")


def resumo_oferta(base):
    """Compara o que o aluno precisa integralizar com o que o curso oferta."""
    margem = _margem_pp(base)
    horas_exigidas = float(base[COLUNA_HORAS_EXIGIDAS].fillna(0).sum())
    horas_ofertadas = float(base[COLUNA_TOTAL_EXT].sum())
    return {
        "total": len(base),
        "iguais": int((margem.abs() <= 1e-6).sum()),
        "maiores": int((margem > 1e-6).sum()),
        "menores": int((margem < -1e-6).sum()),
        "horas_exigidas": formatar_horas(horas_exigidas),
        "horas_ofertadas": formatar_horas(horas_ofertadas),
        "horas_a_mais": formatar_horas(horas_ofertadas - horas_exigidas),
        "pct_horas_a_mais": ((horas_ofertadas / horas_exigidas - 1) * 100) if horas_exigidas else 0.0,
    }


def oferta_por_centro(base):
    """Média, por centro, do % a integralizar e do % ofertado (em pontos percentuais)."""
    tabela = base.groupby("CENTRO").agg(
        EXIGIDO=(COLUNA_PERCENTUAL, "mean"),
        OFERTADO=(COLUNA_OFERTA, "mean"),
        CURSOS=("CURSO", "count"),
    )
    tabela[["EXIGIDO", "OFERTADO"]] = tabela[["EXIGIDO", "OFERTADO"]] * 100
    tabela["_centro"] = tabela.index
    return tabela.sort_values(["OFERTADO", "_centro"], ascending=[False, True]).drop(columns="_centro")


def linhas_oferta(base):
    """Um curso por linha, da maior para a menor margem entre oferta e exigência."""
    base = base.assign(_margem=_margem_pp(base))
    ordenados = base.sort_values(["_margem", "CENTRO", "CURSO"], ascending=[False, True, True], kind="stable")
    return [
        {
            "centro": c["CENTRO"],
            "curso": formatar_nome(c["CURSO"]),
            "emec": c["CÓDIGO E-MEC"] or "Não informado",
            "horas_exigidas": formatar_horas(c[COLUNA_HORAS_EXIGIDAS]),
            "pct_exigido": formatar_percentual(c[COLUNA_PERCENTUAL]),
            "horas_ofertadas": formatar_horas(c[COLUNA_TOTAL_EXT]),
            "pct_ofertado": formatar_percentual(c[COLUNA_OFERTA]),
            "margem": formatar_pp(c["_margem"]),
        }
        for _, c in ordenados.iterrows()
    ]
