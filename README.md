# 🌸 LeadHunter Beauty

**LeadHunter Beauty** é um sistema completo e automatizado para prospecção de estabelecimentos de beleza no Google Maps com auditoria técnica de sites, CRM integrado diretamente à API oficial do Notion (sem bancos de dados locais/SQLite) e inteligência artificial generativa com Google Gemini SDK para criação de abordagens consultivas de WhatsApp e Landing Pages de luxo.

---

## 🏛️ Arquitetura do Sistema

```
leadhunter/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI e rotas REST / SPA
│   ├── scraper.py           # Automação Playwright headless no Google Maps
│   ├── auditor.py           # Auditoria de URL e classificação Tipo A / Tipo B
│   ├── notion_service.py    # CRUD completo com a API oficial do Notion (notion-client)
│   ├── ai_service.py        # Geração de pitches e Landing Pages via Google Gemini
│   └── templates/
│       └── index.html       # Painel Web SPA (HTML5 semântico, Tailwind CSS, JS)
├── .env.example
├── .env
├── requirements.txt
└── README.md
```

- **Backend:** Python 3.10+ com FastAPI e Uvicorn.
- **Web Scraping:** Playwright (Python) headless navegando no Google Maps para extração de estabelecimentos reais (Nome, Avaliação, Reviews, Telefone, Endereço e Website).
- **Auditoria de Presença Digital:**
  - **Tipo A (Sem Site):** Estabelecimentos sem website ou que utilizam apenas redes sociais/link de bio (`instagram.com`, `linktr.ee`, `wa.me`).
  - **Tipo B (Site Obsoleto):** Estabelecimentos com domínio próprio com falhas técnicas (erro HTTP, ausência de `<title>` ou `<h1>`, falta de responsividade mobile ou design ultrapassado).
- **CRM & Armazenamento:** Notion Database oficial via biblioteca `notion-client`. Todos os leads, status do pipeline, links de WhatsApp, pitches gerados e códigos de demonstração são persistidos diretamente no Notion.
- **IA Generativa:** Google Gemini via SDK oficial `google-genai` para redação de abordagens persuasivas e geração de Landing Pages completas com Tailwind CSS.
- **Frontend SPA:** Interface web moderna em HTML5 e Tailwind CSS via CDN, com atualização de status em tempo real, visualização de prévias e disparo direto para o WhatsApp.

---

## 📊 Estrutura do Banco de Dados no Notion

O sistema gerencia automaticamente ou conecta-se a um Notion Database com as seguintes propriedades:

| Propriedade | Tipo no Notion | Descrição |
| :--- | :--- | :--- |
| **Nome** | `title` | Nome do estabelecimento |
| **Nicho** | `select` | Ex: "Extensão de Cílios", "Salão de Beleza", "Estética" |
| **Bairro** | `rich_text` ou `select` | Ex: "Vila Leopoldina", "Moema" |
| **Telefone** | `phone_number` ou `rich_text` | Telefone limpo para contato |
| **Link WhatsApp** | `url` | Link formatado: `https://wa.me/55...` |
| **Nota** | `number` | Avaliação no Google (ex: 4.8) |
| **Qtd Reviews** | `number` | Total de avaliações |
| **Website Original** | `url` | Link cadastrado no Google Maps |
| **Classificação** | `select` | `Tipo A (Sem Site)` ou `Tipo B (Site Obsoleto)` |
| **Status** | `status` ou `select` | `Novo Lead`, `Pitch Gerado`, `Mensagem Enviada`, `Em Conversa`, `Fechado`, `Descartado` |
| **Pitch WhatsApp** | `rich_text` | Mensagem consultiva gerada pela IA |
| **Demo HTML** | `rich_text` | Código HTML5 da Landing Page |

> **Nota:** Caso o seu Notion Database não tenha todas as propriedades acima, o método `notion_service.garantir_estrutura_database()` cria as colunas ausentes automaticamente através da API.

---

## 🚀 Instalação e Execução

### 1. Pré-requisitos
- Python 3.10 ou superior instalado.
- Chave de integração da API do Notion.
- Chave de API do Google Gemini.

### 2. Instalação das Dependências

No diretório do projeto `leadhunter`:

```bash
# Instalação das bibliotecas Python
pip install -r requirements.txt

# Instalação dos navegadores do Playwright
python3 -m playwright install chromium
```

### 3. Configuração das Variáveis de Ambiente (`.env`)

Crie ou edite o arquivo `.env` na raiz do projeto com base no `.env.example`:

```env
# Obtenha em https://www.notion.so/my-integrations
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ID de 32 caracteres do seu Notion Database
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Obtenha em https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

PORT=8000
```

#### Como obter o `NOTION_DATABASE_ID` e configurar permissões:
1. Acesse o seu banco de dados no Notion via navegador.
2. A URL terá o formato: `https://www.notion.so/{workspace_name}/{DATABASE_ID}?v={view_id}`. Copie a sequência de 32 caracteres do `{DATABASE_ID}`.
3. No Notion, clique no menu de três pontos `(...)` no canto superior direito do seu Database, clique em **Conectar a** (ou **Add connections**) e adicione a integração criada em `notion.so/my-integrations`.

### 4. Inicialização do Servidor

Execute o comando:

```bash
python3 -m uvicorn app.main:app --reload --port 8000
```

Abra seu navegador em: **`http://localhost:8000`**

---

## 🛠️ Endpoints da API REST

- `GET /`: Painel web SPA interativo.
- `GET /api/status`: Diagnóstico de conexão com Notion e status do Gemini.
- `GET /api/leads?status={filtro}`: Lista os registros direto do Notion Database.
- `POST /api/prospectar`: Dispara o Playwright para raspar estabelecimentos no Google Maps, audita as URLs e salva novos leads no Notion.
- `POST /api/leads/{page_id}/gerar-pitch`: Gera a abordagem consultiva com o Google Gemini e salva no Notion.
- `PUT /api/leads/{page_id}/pitch`: Salva edições manuais feitas no texto do pitch diretamente no Notion.
- `POST /api/leads/{page_id}/gerar-site`: Gera a Landing Page completa em HTML5/Tailwind e salva no Notion.
- `GET /preview/{page_id}`: Renderiza a Landing Page gerada no navegador para demonstração ao cliente.
- `PATCH /api/leads/{page_id}/status`: Atualiza o status do funil do CRM no Notion.

---

## ✨ Funcionalidades Principais

1. **Scraping Realista no Google Maps:** Navegação sem bloqueios com emulação de usuário real, rolagem dinâmica de feed e extração de dados ricos.
2. **Auditoria Tipo A e Tipo B:**
   - Detecta ausência de site ou uso exclusivo de links de redes sociais.
   - Analisa sites existentes quanto a falhas de carregamento, ausência de meta tags e responsividade mobile.
3. **Pitches de Alta Conversão:** Mensagens com tom humanizado, elogio à reputação real no Google e oferta consultiva de prévia sem compromisso.
4. **Demonstração em Tempo Real:** Gera sites funcionais com paleta Quiet Luxury (Cormorant Garamond, tons areia/nude e champanhe), botões de agendamento no WhatsApp e prova social.
5. **Zero Banco Local:** Total aderência ao Notion como banco primário e central da operação.
