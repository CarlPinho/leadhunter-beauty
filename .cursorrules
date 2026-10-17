# Instruções para o Agente de IA

1. Antes de codificar ou alterar arquivos, leia obrigatoriamente o arquivo `AGENT_MEMORY.md`.
2. Não adicione bancos de dados locais (SQLite, PostgreSQL, etc.). Toda a persistência é feita via `notion_service.py`.
3. Não use bibliotecas frontend pesadas (React, Vue, Streamlit). O frontend deve permanecer em `app/templates/index.html` usando Tailwind via CDN e Vanilla JS com `fetch()`.
4. Garanta que o Playwright rode com flags seguras para ambientes locais (`--no-sandbox`, `--disable-dev-shm-usage`).
5. Ao lidar com o Notion, respeite o limite de 2000 caracteres por bloco de texto ao salvar cópias ou HTML no rich_text.
