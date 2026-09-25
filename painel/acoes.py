"""Regras do Relatório de Ações Prioritárias. Ajuste os critérios aqui; o relatório se adapta."""

from painel.dados import cursos_ativos
from painel.metricas import (
    COLUNA_OFERTA,
    COLUNA_MODIFICACAO,
    COLUNA_PERCENTUAL,
    MODIFICACOES,
    LIMITE_MINIMO,
    TOLERANCIA,
    ROTULOS_STATUS,
    cursos_com_extensao,
    formatar_nome,
    formatar_percentual,
    formatar_processo,
    formatar_resolucao,
)


def _item(curso, detalhe):
    return {
        "centro": curso["CENTRO"],
        "curso": formatar_nome(curso["CURSO"]),
        "emec": curso["CÓDIGO E-MEC"] or "Não informado",
        "detalhe": detalhe,
    }


def _ordenar(itens):
    return sorted(itens, key=lambda i: (i["centro"], i["curso"]))


def _tramitacao(curso):
    processo = formatar_processo(curso["PROCESSOS_LINHAS"])
    resolucao = formatar_resolucao(curso["RESOLUCOES_LINHAS"])
    return f"Processo SIPAC: {processo} · Resolução CONSEPE: {resolucao}"


def acoes_prioritarias(cursos):
    """Prioridades (por proximidade da conclusão) e alertas de dados, só com cursos ativos."""
    ativos = cursos_ativos(cursos)
    por_status = lambda status: ativos[ativos["STATUS"] == status]  # noqa: E731

    aguardando = [_item(c, _tramitacao(c)) for _, c in por_status("AGUARDANDO IMPLANTAÇÃO").iterrows()]

    abaixo = ativos[(ativos["META"] != "NAO_IMPLANTADO") & (ativos[COLUNA_PERCENTUAL] < LIMITE_MINIMO - TOLERANCIA)]
    regularizar = [
        _item(c, f"{formatar_percentual(c[COLUNA_PERCENTUAL])} a integralizar (mínimo de 10%) · "
                 f"{ROTULOS_STATUS.get(c['STATUS'], c['STATUS'])}")
        for _, c in abaixo.iterrows()
    ]

    em_andamento = [_item(c, _tramitacao(c)) for _, c in por_status("EM ANDAMENTO").iterrows()]
    sem_processo = [_item(c, f"Processo SIPAC: {formatar_processo(c['PROCESSOS_LINHAS'])}")
                    for _, c in por_status("SEM PROCESSO").iterrows()]

    prioridades = [
        {"nivel": 1, "titulo": "Concluir a implantação",
         "descricao": "Cursos aguardando implantação: falta implantar o novo PPC.", "itens": _ordenar(aguardando)},
        {"nivel": 1, "titulo": "Regularizar o percentual de extensão a integralizar",
         "descricao": "Cursos com PPC novo e percentual abaixo do mínimo de 10%.", "itens": _ordenar(regularizar)},
        {"nivel": 2, "titulo": "Finalizar a tramitação",
         "descricao": "Cursos com processo em andamento.", "itens": _ordenar(em_andamento)},
        {"nivel": 3, "titulo": "Iniciar o processo",
         "descricao": "Cursos sem processo de inserção curricular da extensão.", "itens": _ordenar(sem_processo)},
    ]

    implantado_sem_processo = [
        _item(c, "Curso implantado sem número de processo SIPAC válido na planilha.")
        for _, c in por_status("IMPLANTADO").iterrows()
        if formatar_processo(c["PROCESSOS_LINHAS"])[:1] not in "0123456789"
    ]
    sem_modificacao = [
        _item(c, "Curso implantado sem classificação em M.CURRICULAR (Aumento, Manutenção, Redução ou Novo): "
                 "não entra na seção de modificação da carga horária mínima do painel.")
        for _, c in por_status("IMPLANTADO").iterrows()
        if c[COLUNA_MODIFICACAO] not in MODIFICACOES
    ]
    sem_emec = [_item(c, "Sem código e-MEC: não é possível agrupar turnos nem cruzar com outras bases.")
                for _, c in ativos[ativos["SEM_EMEC"]].iterrows()]
    divergentes = [
        _item(c, f"Status por turno: {', '.join(ROTULOS_STATUS.get(s, s) for s in c['STATUS_LINHAS'])}. "
                 f"Considerado: {ROTULOS_STATUS.get(c['STATUS'], c['STATUS'])}.")
        for _, c in ativos[ativos["CONFLITO_STATUS"]].iterrows()
    ]
    resolucao_pendente = [
        _item(c, f"Resolução pendente · {ROTULOS_STATUS.get(c['STATUS'], c['STATUS'])}")
        for _, c in ativos.iterrows()
        if formatar_resolucao(c["RESOLUCOES_LINHAS"]) == "Pendente"
    ]
    base = cursos_com_extensao(ativos)
    oferta_menor = [
        _item(c, f"Oferta de {formatar_percentual(c[COLUNA_OFERTA])} menor que a exigência de "
                 f"{formatar_percentual(c[COLUNA_PERCENTUAL])}.")
        for _, c in base[base[COLUNA_OFERTA] < base[COLUNA_PERCENTUAL] - TOLERANCIA].iterrows()
    ]
    alertas = [
        {"titulo": "Implantados sem processo SIPAC válido", "itens": _ordenar(implantado_sem_processo)},
        {"titulo": "Implantados sem modificação curricular classificada", "itens": _ordenar(sem_modificacao)},
        {"titulo": "Resolução CONSEPE pendente", "itens": _ordenar(resolucao_pendente)},
        {"titulo": "Status diferente entre turnos do mesmo curso", "itens": _ordenar(divergentes)},
        {"titulo": "Cursos sem código e-MEC", "itens": _ordenar(sem_emec)},
        {"titulo": "Oferta menor que a exigência", "itens": _ordenar(oferta_menor)},
    ]

    return {
        "prioridades": [p for p in prioridades if p["itens"]],
        "alertas": [a for a in alertas if a["itens"]],
        "por_centro": _por_centro(prioridades),
    }


def _por_centro(prioridades):
    """Quantidade de ações por Centro e por nível de prioridade."""
    contagem = {}
    for grupo in prioridades:
        for item in grupo["itens"]:
            linha = contagem.setdefault(item["centro"], {1: 0, 2: 0, 3: 0})
            linha[grupo["nivel"]] += 1
    return [{"centro": c, "n1": v[1], "n2": v[2], "n3": v[3], "total": sum(v.values())}
            for c, v in sorted(contagem.items(), key=lambda x: (-sum(x[1].values()), x[0]))]
