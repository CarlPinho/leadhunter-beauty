# 🧠 LeadHunter Beauty - Memória e Contexto do Projeto

## 📌 Objetivo do Sistema
Aplicação local em Python focada em prospecção B2B de salões de beleza, studios de cílios, sobrancelhas e clínicas de estética no Google Maps em São Paulo. 
O sistema extrai estabelecimentos, audita a presença digital, classifica a oportunidade (Tipo A vs Tipo B), gera abordagens personalizadas de vendas com Google Gemini e sincroniza tudo diretamente com um banco de dados no Notion (sem banco SQLite/SQL local).

---

## 🏗️ Stack Tecnológica
- **Backend:** Python 3.10+ (FastAPI + Uvicorn)
- **Scraping:** Playwright (Python) headless navegando no Google Maps Web
- **Armazenamento & CRM:** Notion Database via API oficial (`notion-client`)
- **Inteligência Artificial:** Google Gemini SDK (`google-genai`) para copy de WhatsApp e geração de código de Landing Pages
- **Frontend:** SPA nativo em HTML5, Tailwind CSS via CDN e Vanilla JavaScript (sem React, sem Streamlit)

---

## 🎯 Regras de Negócio e Classificação de Leads
- **Tipo A (Sem Site Próprio):** Estabelecimento com site vazio, nulo ou apontando para redes sociais (`instagram.com`, `linktr.ee`, `wa.me`).
  - *Ângulo de Venda:* Falta de autoridade própria, risco de depender só de rede social e perda de clientes que buscam no Google com alta intenção de agendamento.
- **Tipo B (Site Obsoleto / Sem SEO):** Estabelecimento com domínio próprio, mas com falhas de carregamento, ausência de tags semânticas (`<h1>`, `<title>`) ou layout não responsivo no celular.
  - *Ângulo de Venda:* Fuga de clientes e desperdício de investimento em anúncios porque o site tem atrito e não converte em agendamentos de WhatsApp.

---

## 🗂️ Estrutura do Banco no Notion
O Notion Database possui as propriedades:
- `Nome` (title)
- `Nicho` (select)
- `Bairro` (rich_text / select)
- `Telefone` (phone_number ou rich_text)
- `Link WhatsApp` (url - formato `https://wa.me/55...`)
- `Nota` (number)
- `Qtd Reviews` (number)
- `Website Original` (url)
- `Classificação` (select: "Tipo A (Sem Site)" / "Tipo B (Site Obsoleto)")
- `Status` (select/status: "Novo Lead", "Pitch Gerado", "Mensagem Enviada", "Em Conversa", "Fechado", "Descartado")
- `Pitch WhatsApp` (rich_text)
- `Demo HTML` (rich_text)

---

## 📁 Estrutura de Arquivos
```text
leadhunter/
├── app/
│   ├── __init__.py
│   ├── main.py              # Endpoints FastAPI e rotas estáticas
│   ├── scraper.py           # Automação Playwright para Google Maps
│   ├── auditor.py           # Validador de sites e classificação A/B
│   ├── notion_service.py    # CRUD direto com Notion Database
│   ├── ai_service.py        # Integração Gemini (Pitch + Landing Pages)
│   └── templates/
│       └── index.html       # Painel em HTML/Tailwind/JS
├── .env.example
├── .gitignore
├── requirements.txt
├── AGENT_MEMORY.md          # Este arquivo de contexto
├── AGENT_INSTRUCTIONS.md    # Regras e restrições para agentes de IA
└── README.md
```

---

## ⚙️ Variáveis de Ambiente (`.env`)
```env
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
GEMINI_API_KEY=AIza...
PORT=8000
```
