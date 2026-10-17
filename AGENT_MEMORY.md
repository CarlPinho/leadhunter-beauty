# 🧠 LeadHunter Beauty - Memória e Contexto do Projeto

## 📌 Objetivo do Sistema
Aplicação local em Python focada em prospecção B2B de salões de beleza, studios de cílios, sobrancelhas, clínicas de estética e gastronomia no Google Maps em São Paulo. 
O sistema extrai estabelecimentos, audita a presença digital, classifica a oportunidade (Tipo A vs Tipo B), gera abordagens personalizadas de vendas com Google Gemini, extrai inteligência de websites legados e sincroniza os leads com o Notion CRM (sem banco SQLite/SQL local).

---

## 🏗️ Stack Tecnológica
- **Backend:** Python 3.10+ (FastAPI + Uvicorn)
- **Scraping & Auditoria:** Playwright (Python) headless no Google Maps e HTTP client para raspagem de sites legados
- **Extração de Inteligência:** `app/site_extractor.py` (títulos, cabeçalhos h1/h2, bio/apresentação e serviços reais)
- **Armazenamento & CRM:** Notion Database via API oficial (`notion-client`)
- **Inteligência Artificial:** Google Gemini SDK (`google-genai`) para copy de WhatsApp e Engenharia de Super Prompts para o Google AI Studio
- **Frontend:** SPA nativo em HTML5, Tailwind CSS via CDN e Vanilla JavaScript (sem React, sem Streamlit)

---

## 🎯 Regras de Negócio e Classificação de Leads
- **Tipo A (Sem Site Próprio):** Estabelecimento com site vazio, nulo ou apontando para redes sociais (`instagram.com`, `linktr.ee`, `wa.me`).
  - *Ângulo de Venda:* Falta de autoridade própria, risco de depender só de rede social e perda de clientes que buscam no Google com alta intenção de agendamento.
- **Tipo B (Site Obsoleto / Sem SEO):** Estabelecimento com domínio próprio, mas com falhas de carregamento, ausência de tags semânticas (`<h1>`, `<title>`) ou layout não responsivo no celular.
  - *Ângulo de Venda:* Fuga de clientes e desperdício de investimento em anúncios porque o site tem atrito e não converte em agendamentos de WhatsApp.

---

## 🚀 Engenharia de Super Prompt para Google AI Studio (Build with Gemini)
Ao invés de compilar código HTML diretamente no backend, o LeadHunter atua como um extrator de inteligência que gera Super Prompts hiperpersonalizados para o usuário colar diretamente no **Google AI Studio** (`https://aistudio.google.com/`):

1. **Extração de Inteligência de Sites Legados (`app/site_extractor.py`):**
   - Função: `extrair_conteudo_site(url: str) -> dict`
   - Detecta e ignora redes sociais / agregadores de bio.
   - Realiza requisições com timeout seguro de 6s e User-Agent padrão.
   - Extrai: título da página (`<title>`), cabeçalhos principais (`<h1>`, `<h2>`), parágrafos de apresentação/bio e catálogo de serviços/itens de cardápio (`<li>`, `<h3>`).
   - Remove excessos, scripts e mensagens de cookies.

2. **Geração do Super Prompt (`app/ai_service.py`):**
   - Função: `gerar_prompt_ai_studio(lead: dict, conteudo_extraido: dict = None) -> str`
   - **Regra de Ouro Anti-Alucinação:** "Nunca adicione tratamentos médicos invasivos, preços específicos em Real ou dados não fornecidos pelo cliente. Trabalhe com o que foi extraído e posicione o WhatsApp como a ponte de orçamento."
   - **Proibição Estrita de Preços Fictícios:** Se o site legado não informar preços (ex: Studio Haara Beleza), instrui explicitamente: *"NÃO invente valores em R$ ou tabelas de preços fictícias. Utilize botões de CTA como 'Consultar Tabela / Agendar via WhatsApp' ou 'Solicitar Orçamento Personalizado'."*
   - **Fidelidade aos Textos & Números Reais:** Destaca dados reais que a cliente já colocou no site legado (tempo de mercado, clientes atendidos, estacionamento/valet, endereço real).
   - **Categorias Multi-Serviços:** Onde faltar detalhamento de procedimentos, instrui a criação de categorias elegantes de multi-serviços (ex: Cabelo & Penteados, Estética Facial, Manicure & Pedicure) direcionando para consulta de valores no WhatsApp.
   - **Persona:** UI/UX Designer Sênior e Especialista em Front-end de Alta Conversão no nicho específico.
   - **Contexto do Negócio:** Nome, Bairro, Endereço Real, Nota Google Maps, Total de Reviews e link de WhatsApp formatado.
   - **Para Leads Tipo B:** Anexa os dados reais raspados do site antigo com instruções para modernização total de copy e layout.
   - **Para Leads Tipo A:** Instrui a criação do zero com serviços de maior demanda e lucratividade para o nicho.
   - **Diretrizes Técnicas:** HTML5 semântico único, Tailwind CSS via CDN, Google Fonts, paleta por nicho (Clean Luxury para estética; Dark Modern para barbearias; Gastronomia Premium para restaurantes).
   - **Seções Obrigatórias:** Header com botão de WhatsApp, Hero section com selo de reputação Google, Cards de serviços sem preços fictícios, Quebra de objeções com diferenciais reais, Prova social, FAQ orientando para WhatsApp, Rodapé com endereço real e Botão Flutuante de WhatsApp.

3. **Interface e Modal (`app/templates/index.html`):**
   - Botão no card: **"✨ Gerar Prompt AI Studio"** / **"✨ Ver Prompt AI Studio"**.
   - Modal com bloco de código monoespaçado formatado.
   - Botão **"📋 Copiar Prompt"** com feedback instantâneo.
   - Botão **"🚀 Abrir Google AI Studio"** direcionando para `https://aistudio.google.com/`.

---

## 🔄 Fluxo de Prospecção com Stage Buffer (Envio Seletivo)
O sistema opera em duas etapas para garantir controle total sobre os registros salvos no CRM Notion:

1. **Extração & Auditoria (Buffer de Sessão):**
   - Rota: `POST /api/prospectar`
   - O Playwright navega no Google Maps com flags seguras (`--no-sandbox`, `--disable-dev-shm-usage`).
   - O módulo `auditor.py` valida status HTTP e classificação (Tipo A / Tipo B).
   - Os leads recebem IDs temporários (`lead_...`), status `synced_notion: False` e são armazenados em `_session_leads_cache`.
   - **Nenhum lead é salvo automaticamente no Notion** nesta etapa.

2. **Seleção & Envio Controlado ao Notion:**
   - Rota: `POST /api/leads/enviar-notion` (recebe payload `{"leads": [...]}`)
   - O usuário seleciona os estabelecimentos desejados via checkboxes individuais ou pelo botão global na barra de ação ("Enviar Selecionados para o Notion").
   - O backend salva os registros oficiais no Notion via `notion_service.salvar_lead` e retorna os novos `page_id` e `notion_url`.
   - Cards e contadores são atualizados dinamicamente entre "Aguardando envio ao Notion" e "Sincronizado no Notion".
   - Pitch para WhatsApp e Super Prompt para AI Studio podem ser gerados tanto no buffer quanto após a sincronização.

---

## 📍 Localização e Categorias Pré-Definidas
- **Cidade:** Fixo em "São Paulo - SP".
- **Dropdown de Regiões e Bairros de SP:**
  - *"Toda a Cidade (Geral)"* -> envia `São Paulo, SP`.
  - *Zona Oeste:* Vila Leopoldina, Pinheiros, Perdizes, Lapa, Vila Madalena, Butantã -> envia `{Bairro}, São Paulo - SP`.
  - *Zona Sul:* Moema, Itaim Bibi, Vila Mariana, Morumbi, Brooklin, Campo Belo, Santo Amaro -> envia `{Bairro}, São Paulo - SP`.
  - *Zona Leste:* Tatuapé, Mooca, Anália Franco, Penha -> envia `{Bairro}, São Paulo - SP`.
  - *Zona Norte:* Santana, Tucuruvi, Casa Verde -> envia `{Bairro}, São Paulo - SP`.
  - *Centro:* Bela Vista, Consolação, República -> envia `{Bairro}, São Paulo - SP`.
- **Categorias de Nichos:**
  - *Beleza & Estética:* Extensão de Cílios, Salão de Beleza, Studio de Sobrancelhas / Brow Lamination, Clínica de Estética, Unhas de Gel / Manicure, Barbearia.
  - *Gastronomia & Food:* Hamburgueria, Pizzaria, Restaurante Japonês / Sushi, Doceria / Confeitaria, Cafeteria.
  - *Outro:* Campo dinâmico para digitação livre.

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
- `Link Maps` (url - link canônico da ficha do estabelecimento no Google Maps)

---

## 🎨 Design System: Dark Mode Premium (Estilo Linear / Vercel)
A interface SPA (`app/templates/index.html`) adota um design sóbrio, minimalista e altamente profissional:
- **Paleta de Superfícies:** Fundo principal `zinc-950` (`#09090b`), cards e modais em `zinc-900` com bordas sutis `border-zinc-800` e cantos arredondados `rounded-xl`.
- **Tipografia:** Texto primário `zinc-100`, textos de apoio `zinc-400`, placeholders `zinc-500`.
- **Destaques:** Acentos de conversão e WhatsApp em esmeralda (`emerald-500`/`emerald-600`) e alertas compactos em âmbar. Sem gradientes roxos ou visual clichê de IA.
- **Card do Lead:** Inclui botão direto **"📍 Ver no Maps"** para abrir a ficha oficial no Google Maps em nova aba, badges minimalistas de classificação (Tipo A / Tipo B) e status de sincronização (Buffer vs Notion).

---

## 💬 Motor de Cópias de WhatsApp (Alta Conversão em vez de "Textão")
Implementado em `app/ai_service.py` (`gerar_copy_whatsapp` e `gerar_pitch`):
- **Formato:** Máximo de 3 a 4 linhas no WhatsApp, tom humano e consultivo sem jargões corporativos.
- **Estrutura Obrigatória em 3 Passos:**
  1. *Quebra de padrão:* Elogio sincero à reputação e avaliações no Google Maps.
  2. *Apontamento cirúrgico da dor:*
     - **Tipo A:** Perda de agendamentos por depender exclusivamente de Instagram/WhatsApp sem página própria.
     - **Tipo B:** Desistência de clientes devido à lentidão ou falta de adaptação móvel do site atual.
  3. *CTA de baixo atrito:* Pergunta leve de permissão ("Montei uma prévia moderna de 1 minuto mostrando como ficaria o atendimento de vocês em alta conversão. Posso te mandar o link aqui?").
- **Follow-up Automático (24h):** Mensagem rápida de reconexão incluída no retorno para acompanhamento do prospect.
- **Abertura Inteligente:** No modal do WhatsApp, o link `wa.me` codifica apenas a mensagem principal, deixando o follow-up visível para consulta.

---

## 📁 Estrutura de Arquivos
```text
leadhunter/
├── app/
│   ├── __init__.py
│   ├── main.py              # Endpoints FastAPI, rotas de buffer, AI Studio e sincronização
│   ├── scraper.py           # Automação Playwright para Google Maps
│   ├── auditor.py           # Validador de sites e classificação A/B
│   ├── site_extractor.py    # Extrator de títulos, textos e serviços de sites legados
│   ├── notion_service.py    # CRUD direto com Notion Database
│   ├── ai_service.py        # Integração Gemini (Pitch + Super Prompt para AI Studio)
│   └── templates/
│       └── index.html       # Painel SPA em HTML/Tailwind/JS nativo
├── .env.example
├── .gitignore
├── requirements.txt
├── AGENT_MEMORY.md          # Memória e documentação do projeto
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
