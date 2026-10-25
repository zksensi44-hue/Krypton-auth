# Krypton Cloud — primeira versão web

Interface responsiva monocromática com autenticação oficial Discord OAuth2 (identify/email), sessão de backend e endpoint de saúde. O frontend não recebe o client secret.

## Rodar localmente
1. Instale Python 3.11 ou superior.
2. Extraia a pasta e abra o terminal dentro dela.
3. Instale dependências: `pip install -r requirements.txt`.
4. Copie `.env.example` para `.env` e preencha as variáveis.
5. No Discord Developer Portal, abra sua aplicação → OAuth2 e cadastre como Redirect URL o valor exato de `DISCORD_REDIRECT_URI`.
6. Rode `python app.py` e abra `http://127.0.0.1:5000`.

## Hospedagem (Render ou equivalente)
- Crie um Web Service apontando para esta pasta.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Cadastre `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` com a URL pública HTTPS terminando em `/oauth/callback`, `FLASK_SECRET_KEY` forte e `COOKIE_SECURE=true`.
- Cadastre a mesma URL de callback no Discord Developer Portal.
- Nunca comite `.env` nem publique o client secret.

## Integração com a source do bot
A source fornecida tem `modules/cloud/` e arquivos de pagamentos, mas `configs/config_api.json` deixa `services.cloud_enabled` como `false`. Não foi encontrada uma API web autenticada e documentada que permita ao site listar/controlar bots ou consultar pagamentos. Por isso o dashboard não inventa status, planos, pagamentos nem botões de controle. Para ativar essas funções, implemente uma API backend autenticada (token de serviço guardado somente no servidor), autorização por ID Discord, validação de propriedade, auditoria e endpoints documentados; então conecte os adaptadores do dashboard à API. Não exponha o token do bot Discord no site.

## Testes
- `GET /health` retorna JSON com `status: ok`.
- Sem credenciais OAuth, `GET /login/discord` retorna uma página explicando a configuração pendente (HTTP 503).
- O callback valida o parâmetro `state`, troca o código no backend e consulta `/users/@me` no Discord.
- `GET /api/me` exige sessão autenticada.

Esta entrega é a base funcional de frontend e OAuth; não significa que o gerenciamento real de bots ou pagamentos esteja conectado. O acesso a essas funções depende da API descrita acima.
