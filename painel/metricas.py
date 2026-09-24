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
COLUNA_HORAS_CURSO = "CH_MÍNINA_NOVO"


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
            "horas_curso": formatar_horas(c[COLUNA_HORAS_CURSO]),
            "horas_exigidas": formatar_horas(c[COLUNA_HORAS_EXIGIDAS]),
            "pct_exigido": formatar_percentual(c[COLUNA_PERCENTUAL]),
            "horas_ofertadas": formatar_horas(c[COLUNA_TOTAL_EXT]),
            "pct_ofertado": formatar_percentual(c[COLUNA_OFERTA]),
            "margem": formatar_pp(c["_margem"]),
        }
        for _, c in ordenados.iterrows()
    ]


COLUNA_UCE_QTDE = "QTDE_UCE"
COLUNA_UCE_HORAS = "CH_UCE"
COLUNA_UCE_CREDITOS = "CREDITO_UCE"
ROTULOS_UCE = {"COM_UCE": "Com UCE", "SEM_UCE": "Sem UCE"}


def _classe_uce(qtde, horas):
    """Campo vazio na planilha conta como sem UCE."""
    if _numero(qtde) > 0 or _numero(horas) > 0:
        return "COM_UCE"
    return "SEM_UCE"


def com_uce(base):
    """Classifica cada curso em com UCE ou sem UCE (inclui os campos vazios da planilha)."""
    classes = [_classe_uce(q, h) for q, h in zip(base[COLUNA_UCE_QTDE], base[COLUNA_UCE_HORAS])]
    return base.assign(UCE_CLASSE=classes)


def _numero(valor):
    return 0 if pd.isna(valor) else valor


def _total(serie):
    soma = serie.fillna(0).sum()
    return "0" if soma == 0 else formatar_horas(soma)


def resumo_uce(base):
    base = com_uce(base)
    return {
        "total": len(base),
        "com_uce": int((base["UCE_CLASSE"] == "COM_UCE").sum()),
        "qtde": _total(base[COLUNA_UCE_QTDE]),
    }


def uce_por_centro(base):
    base = com_uce(base)
    tabela = base.groupby("CENTRO").agg(
        UCES=(COLUNA_UCE_QTDE, lambda s: s.fillna(0).sum()),
        HORAS=(COLUNA_UCE_HORAS, lambda s: s.fillna(0).sum()),
        CREDITOS=(COLUNA_UCE_CREDITOS, lambda s: s.fillna(0).sum()),
        CURSOS=("CURSO", "count"),
    )
    tabela["COM_UCE"] = base[base["UCE_CLASSE"] == "COM_UCE"].groupby("CENTRO")["CURSO"].count().reindex(tabela.index).fillna(0).astype(int)
    tabela["_centro"] = tabela.index
    return tabela.sort_values(["UCES", "_centro"], ascending=[False, True]).drop(columns="_centro")


def _formatar_uce(valor):
    numero = _numero(valor)
    return "0" if numero == 0 else formatar_horas(numero)


def linhas_uce(base):
    """Um curso por linha, do que tem mais UCE para o que tem menos."""
    base = com_uce(base)
    base = base.assign(_qtde=base[COLUNA_UCE_QTDE].fillna(0))
    ordenados = base.sort_values(["_qtde", "CENTRO", "CURSO"], ascending=[False, True, True], kind="stable")
    linhas = []
    for _, c in ordenados.iterrows():
        linhas.append({
            "centro": c["CENTRO"],
            "curso": formatar_nome(c["CURSO"]),
            "emec": c["CÓDIGO E-MEC"] or "Não informado",
            "qtde": _formatar_uce(c[COLUNA_UCE_QTDE]),
            "horas": _formatar_uce(c[COLUNA_UCE_HORAS]),
            "creditos": _formatar_uce(c[COLUNA_UCE_CREDITOS]),
            "classe": c["UCE_CLASSE"],
            "situacao": ROTULOS_UCE[c["UCE_CLASSE"]],
        })
    return linhas


PADRAO_PERIODO = re.compile(r"^(\d{4})\.([12])$")


def _semestres_entre(primeiro, ultimo):
    (ano_i, sem_i), (ano_f, sem_f) = primeiro, ultimo
    periodos = []
    for ano in range(ano_i, ano_f + 1):
        for sem in (1, 2):
            if (ano, sem) >= (ano_i, sem_i) and (ano, sem) <= (ano_f, sem_f):
                periodos.append(f"{ano}.{sem}")
    return periodos


def implantados_por_periodo(ativos):
    """Cursos ativos com STATUS Implantado por período (ano.semestre) do PPC novo, sem pular semestres."""
    implantados = ativos[ativos["STATUS"] == "IMPLANTADO"]
    validos = implantados[implantados["PPC_NOVO_PERIODO"].map(lambda p: bool(PADRAO_PERIODO.match(p))).astype(bool)]
    contagem = validos["PPC_NOVO_PERIODO"].value_counts()
    if contagem.empty:
        return [], len(implantados)
    chaves = sorted((int(a), int(b)) for a, b in (PADRAO_PERIODO.match(p).groups() for p in contagem.index))
    periodos = _semestres_entre(chaves[0], chaves[-1])
    return [{"periodo": p, "total": int(contagem.get(p, 0))} for p in periodos], len(implantados) - len(validos)


def linhas_periodo(ativos):
    """Cursos implantados com o período do PPC novo, do mais antigo para o mais recente."""
    implantados = ativos[ativos["STATUS"] == "IMPLANTADO"]
    ordenados = implantados.assign(_periodo=implantados["PPC_NOVO_PERIODO"].replace("", "9999.9")).sort_values(
        ["_periodo", "CENTRO", "CURSO"], kind="stable")
    return [
        {
            "centro": c["CENTRO"],
            "curso": formatar_nome(c["CURSO"]),
            "emec": c["CÓDIGO E-MEC"] or "Não informado",
            "periodo": c["PPC_NOVO_PERIODO"] or "—",
        }
        for _, c in ordenados.iterrows()
    ]
