# Botão "Enviar relatório" (Google Apps Script)

Cópia dos dois arquivos do botão de envio (`Codigo.gs` e `Pagina.html`), sem dados pessoais. Para recriar o aplicativo, copie-os para o editor do Apps Script e ajuste `EMAIL_AUTORIZADO` em `Codigo.gs`. Não há segredos neles: o token do GitHub vai nas propriedades do script.

## 1. Segredos do GitHub (repositório → Settings → Secrets and variables → Actions)

| Nome | Valor |
|---|---|
| `MAIL_USERNAME` | Gmail remetente (ex.: a conta da PROEX) |
| `MAIL_PASSWORD` | **Senha de app** desse Gmail (Conta Google → Segurança → Verificação em duas etapas → Senhas de app). Não use a senha normal. |
| `MAIL_TO` | E-mails da equipe separados por vírgula |

(`GOOGLE_SERVICE_ACCOUNT_JSON` e `SHEET_ID` já existem.)

## 2. Token do GitHub para o Apps Script

GitHub → Settings → Developer settings → Fine-grained tokens → **Generate new token**:
- Repositório: apenas `proex-ufpb/analisecurricularextensao`.
- Permissão: **Actions: Read and write** (nenhuma outra).
- Validade: pode ser sem data de validade (evita o botão parar por vencimento). Nesse caso, revise o token uma vez por ano e gere outro se alguém com acesso sair. Se escolher uma data, anote-a para renovar.

## 3. Criar o aplicativo web

1. Acesse https://script.google.com logado com a conta a conta autorizada (a mesma definida em `EMAIL_AUTORIZADO`) → **Novo projeto**.
2. Cole o conteúdo de `Codigo.gs` em `Código.gs` e crie um arquivo HTML chamado `Pagina` com o conteúdo de `Pagina.html`.
3. Em **Configurações do projeto → Propriedades do script**, adicione `GITHUB_TOKEN` = o token do passo 2.
4. **Implantar → Nova implantação → Aplicativo da Web**:
   - Executar como: **Usuário que acessa o aplicativo da Web**
   - Quem tem acesso: **Qualquer pessoa com uma Conta do Google**
5. Autorize quando o Google pedir e copie a **URL do aplicativo da Web**.

## 4. Ligar o botão ao painel

O painel já tem a página **Relatório (Equipe PROEX)** (`equipe.html`), com link no menu do topo. Ela mostra "Envio em configuração" até você informar o endereço: cole a URL do passo 3 em `URL_ENVIO_RELATORIO` (arquivo `painel/tema.py`) ou me passe a URL, e publique. O botão da página passa a levar ao login do Google.

A tela do Apps Script pede confirmação antes de enviar e mostra o último envio (data, hora e quem enviou).

## Como funciona a restrição

O link abre uma página que exige login Google. Só a conta a conta autorizada (a mesma definida em `EMAIL_AUTORIZADO`) vê o botão; qualquer outra vê "Acesso restrito". O servidor confere a conta de novo antes de chamar o GitHub.

## Testar sem o botão

No GitHub: **Actions → Enviar relatório de ações prioritárias → Run workflow**.
