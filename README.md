# Análise Curricular — Inserção Curricular da Extensão (PROEX/UFPB)

Painel público que acompanha a inserção curricular da extensão nos cursos de graduação da UFPB, com um relatório interno de ações prioritárias enviado por e-mail.

**Painel:** https://proex-ufpb.github.io/analisecurricularextensao/

Este documento é para quem for **manter** o projeto. Não há segredos aqui: os nomes dos segredos aparecem, mas os valores ficam só no GitHub e no Google.

---

## 1. Como funciona

```
Planilha Google (aba "ANÁLISE CURRICULAR")
        │  todos os dias às 06h (Brasília), ou "Run workflow"
        ▼
GitHub Actions  ──►  exporta a planilha  ──►  data/analise_curricular.csv
        │
        ├──►  roda os testes  ──►  gera as 18 páginas (Python)  ──►  GitHub Pages (o painel)
        │
        └──►  botão "Área da equipe" ──► Google Apps Script ──► dispara o workflow do relatório
                                                                   │
                                            gera o relatório e envia por e-mail à equipe
```

- Tudo é recalculado a cada execução: cartões, gráficos, tabelas, menu de Centros e a data "Dados atualizados em". Nada é digitado à mão.
- Se a construção falhar, **o site continua com a última versão boa**. O erro aparece em *Actions* (execução vermelha).
- Nenhum serviço de IA participa do funcionamento. O painel roda em GitHub (repositório, Actions, Pages) e Google (Planilhas, conta de serviço, Apps Script, Gmail).

## 2. Estrutura do repositório

| Caminho | O que é |
|---|---|
| `painel/dados.py` | Lê o CSV, normaliza, agrupa por curso único e resolve o STATUS |
| `painel/metricas.py` | Cálculos de todas as seções (cartões, gráficos, tabelas) |
| `painel/acoes.py` | **Regras do Relatório de Ações Prioritárias** |
| `painel/construir.py` | Gera o site (`site/`): página geral, uma por Centro e a da equipe |
| `painel/relatorio.py` | Gera o relatório em HTML para o e-mail |
| `painel/tema.py` | Cores, contatos, equipe, **nomes dos Centros**, endereço do Apps Script |
| `painel/templates/`, `painel/static/` | Modelos HTML, CSS, JavaScript e a fonte Saira |
| `scripts/exportar_planilha.py` | Baixa a aba da planilha para o CSV (descarta `NOTAS_FASE2`) |
| `data/analise_curricular.csv` | Última exportação (gerada automaticamente, não editar) |
| `assets/` | Logos da UFPB e da PROEX |
| `tests/` | Testes automáticos (usam uma cópia congelada dos dados em `tests/fixtures/`) |
| `.github/workflows/` | `atualizar-dados.yml` (diário) e `enviar-relatorio.yml` (sob demanda) |
| `docs/apps-script/` | Cópia do código do botão de envio (ver seção 6) |

## 3. Regras que não podem ser quebradas

- **Curso único** = mesmo código e-MEC + tipo + Centro + curso + modalidade + sede (após remover espaços extras). Cursos com vários turnos contam **uma vez**.
- **Prioridade de STATUS** quando as linhas do mesmo curso divergem: `IMPLANTADO > AGUARDANDO IMPLANTAÇÃO > EM ANDAMENTO > SEM PROCESSO`.
- Totais e percentuais usam só cursos com `SITUAÇÃO = EM ATIVIDADE`. Cursos em extinção aparecem nas tabelas, fora das contas.
- As análises de oferta, componentes e UCE usam só cursos ativos com **percentual de extensão maior que zero** (`cursos_com_extensao`, em `painel/metricas.py`). A regra é reavaliada a cada execução.
- **"A integralizar"** é o que o aluno precisa cumprir (colunas AD–AF); **"ofertada"** é o que o curso disponibiliza (AG–AN). A faixa de 10% a 15% vale só para o "a integralizar".
- A coluna **`NOTAS_FASE2` nunca** é usada, exibida nem guardada no repositório.
- O painel usa **somente** a aba `ANÁLISE CURRICULAR`.

## 4. Rotina de manutenção

### O que conferir
- **De vez em quando:** a aba *Actions* deve mostrar a execução diária em verde. Se estiver vermelha, abra o passo que falhou.
- **Uso do token do Apps Script:** em *Settings → Developer settings → Personal access tokens* da conta do repositório, o campo *Last used* mostra quando ele foi usado pela última vez.
- **O GitHub pode desativar tarefas agendadas** de repositórios públicos sem atividade por cerca de 60 dias (como o CSV só muda quando a planilha muda, isso é possível). Se o painel parar de atualizar: *Actions → Atualizar dados e publicar painel* → se aparecer o aviso de desativado, clique em **Enable workflow**; depois **Run workflow** para atualizar na hora.

### O que expira ou precisa ser renovado

| Item | Onde fica | Quando renovar |
|---|---|---|
| Token do GitHub usado pelo Apps Script (`GITHUB_TOKEN`) | Propriedades do script no Google | Foi criado **sem data de validade**, então não vence sozinho. A validade pode ser alterada a qualquer momento editando o token na página dos tokens do GitHub, **sem trocar o valor** guardado no Apps Script. Revise uma vez por ano e **gere outro se alguém com acesso ao Apps Script ou à conta sair** (apague o antigo). Se o botão de envio der erro 401, o token foi apagado ou revogado. Permissão mínima: *Actions: Read and write*, só neste repositório. |
| Senha de app do Gmail remetente (`MAIL_PASSWORD`) | Segredo do GitHub | Se for revogada ou se a senha da conta mudar. Exige verificação em duas etapas. |
| Chave da conta de serviço Google (`GOOGLE_SERVICE_ACCOUNT_JSON`) | Segredo do GitHub | Não expira sozinha; refazer se a chave for apagada no Google Cloud. A conta de serviço precisa ter a planilha compartilhada como **Leitor**. |
| Lista de destinatários (`MAIL_TO`) | Segredo do GitHub | Quando a equipe mudar (e-mails separados por vírgula). |

**Segredos do repositório** (*Settings → Secrets and variables → Actions*): `GOOGLE_SERVICE_ACCOUNT_JSON`, `SHEET_ID`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_TO`.

### Tarefas comuns
- **Atualizar na hora:** *Actions → Atualizar dados e publicar painel → Run workflow*.
- **Novo Centro:** aparece sozinho no menu, mas só com a sigla. Para mostrar o nome, acrescente-o em `NOMES_CENTROS` (`painel/tema.py`).
- **Mudar critérios do relatório** (o que é prioridade 1, 2 ou 3, e os alertas): `painel/acoes.py`.
- **Mudar textos, títulos e rótulos:** `painel/templates/index.html.j2` e os gráficos em `painel/construir.py`.
- **Se a planilha mudar de estrutura:** o painel depende dos **nomes das colunas** da linha 2 da aba (por exemplo `CÓDIGO E-MEC`, `STATUS`, `SITUAÇÃO`, `% CH_INTEGRALIZADA_EXTENSAO`, `%CH_EXT_DISPONÍVEL`, `CH_TOTAL_EXT`, `CH_UCE`, `QTDE_UCE`, `M.CURRICULAR`, `PPC_ANO_NOVO`, `PROCESSO`, `RESOLUÇÃO`). Renomear ou apagar uma delas faz a construção falhar (o site antigo continua no ar).

## 5. Rodar no computador

Requer Python 3.12.

```bash
pip install -r requirements-dev.txt
python -m pytest -q                 # testes
python -m painel.construir          # gera o site em site/
cd site && python -m http.server 8765   # abre em http://localhost:8765
python -m painel.relatorio          # gera o relatório em relatorio/ (não é publicado)
```

Para exportar a planilha localmente, defina as variáveis de ambiente `GOOGLE_SERVICE_ACCOUNT_JSON` (conteúdo do JSON) e `SHEET_ID`, e rode `python scripts/exportar_planilha.py`.

## 6. Relatório por e-mail (botão da equipe)

1. No rodapé do painel, o link discreto **"Área da equipe"** leva a `equipe.html`, que abre um aplicativo do Google Apps Script.
2. O aplicativo exige login Google e **só uma conta autorizada** vê o botão de envio (o servidor confere a conta de novo antes de agir). Pede confirmação e mostra o último envio.
3. O Apps Script dispara o workflow `enviar-relatorio.yml`, que exporta a planilha, gera o relatório (`painel/relatorio.py`) e o envia pelo Gmail remetente aos endereços de `MAIL_TO`.

O código do Apps Script **não fica neste repositório em produção**: ele vive no projeto do Google da conta da creditação. Uma cópia sem dados pessoais está em [`docs/apps-script/`](docs/apps-script/) com o passo a passo para recriá-lo. O endereço do aplicativo fica em `URL_ENVIO_RELATORIO` (`painel/tema.py`).

## 7. Mudar para um domínio da UFPB

O painel é **100% estático** (cerca de 26 arquivos, 6,6 MB) e usa só caminhos relativos, então funciona em qualquer servidor web. Do mais simples ao mais trabalhoso:

1. **Domínio da UFPB apontando para o GitHub Pages (recomendado).** A TI cria um endereço (por exemplo `analisecurricular.proex.ufpb.br`) com um registro DNS do tipo CNAME para `proex-ufpb.github.io`; depois, em *Settings → Pages → Custom domain*, informa o endereço. Não move nada e mantém a atualização diária e o HTTPS.
2. **Copiar a pasta `site/`** (gerada a cada execução) para o servidor da UFPB. Cada atualização diária precisaria ser copiada de novo.
3. **Mover o pipeline inteiro** para a infraestrutura da UFPB: levar `painel/`, `scripts/`, `assets/`, `requirements.txt`, os workflows e a chave da conta de serviço. O servidor precisa de Python 3.12 e de uma tarefa agendada (cron) diária. O botão de envio teria de ser refeito para chamar o novo servidor.

O site não carrega nada de fora: a fonte Saira e os gráficos (Plotly) vão junto. O único endereço externo é o do botão de envio do relatório (Apps Script).

## 8. Licenças e marcas

- Fonte **Saira**: SIL Open Font License 1.1 (`painel/static/fonts/LICENCA-Saira-OFL.txt`).
- Gráficos: **Plotly.js** (MIT), incluído no site.
- As logomarcas da UFPB e da PROEX pertencem às instituições e seguem o Manual de Identidade Visual da PROEX.

## 9. Contato

Pró-Reitoria de Extensão (PROEX/UFPB) — creditacaodaextensao@proex.ufpb.br — ramal 3216-7211.
