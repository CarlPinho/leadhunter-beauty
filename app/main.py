"""
API Principal FastAPI para o LeadHunter Beauty.
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Body, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.notion_service import NotionService
from app.scraper import GoogleMapsScraper
from app.ai_service import AIService
from app.site_extractor import extrair_conteudo_site

# Carrega variáveis de ambiente
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_HTML = TEMPLATES_DIR / "index.html"

app = FastAPI(
    title="LeadHunter Beauty",
    description="Sistema de prospecção no Google Maps e CRM integrado diretamente ao Notion com IA Generativa Gemini",
    version="1.0.0"
)

# Habilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa serviços
notion_service = NotionService()
ai_service = AIService()
scraper = GoogleMapsScraper(headless=True)

# Cache em memória temporário para sessão de demonstração quando o Notion não estiver configurado
_session_leads_cache: Dict[str, Dict[str, Any]] = {}


def _obter_lead_hibrido(page_id: str) -> Optional[Dict[str, Any]]:
    """Recupera o lead do Notion se configurado e não for ID de buffer temporário, ou do cache em memória."""
    if notion_service.is_configured() and not page_id.startswith("lead_"):
        try:
            return notion_service.obter_lead(page_id)
        except Exception:
            pass
    return _session_leads_cache.get(page_id)


def _atualizar_lead_hibrido(page_id: str, updates: dict):
    """Atualiza o lead no Notion e no cache da sessão."""
    if page_id in _session_leads_cache:
        _session_leads_cache[page_id].update(updates)
    if notion_service.is_configured() and not page_id.startswith("lead_"):
        try:
            return notion_service.atualizar_lead(page_id, updates)
        except Exception:
            pass


# --- Modelos Pydantic ---
class ProspectarRequest(BaseModel):
    nicho: str = Field(default="Extensão de Cílios", description="Nicho de atuação da busca")
    localizacao: str = Field(default="Vila Leopoldina, São Paulo - SP", description="Bairro ou região para busca")
    limite: int = Field(default=8, ge=1, le=30, description="Quantidade máxima de estabelecimentos a extrair")


class EnviarNotionRequest(BaseModel):
    leads: List[Dict[str, Any]] = Field(..., description="Lista de leads selecionados para enviar ao Notion")


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Novo status do lead (ex: 'Pitch Gerado', 'Mensagem Enviada', etc.)")


class PitchUpdateRequest(BaseModel):
    pitch: str = Field(..., description="Novo texto do pitch para salvar no Notion")


# --- Rotas da Aplicação ---

@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve o painel Web SPA do LeadHunter Beauty."""
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=404, detail="Arquivo index.html não encontrado em app/templates/")
    return FileResponse(str(INDEX_HTML))


@app.get("/api/status")
async def check_system_status():
    """Retorna o status de conexão com o Notion e com o Gemini."""
    notion_configured = notion_service.is_configured()
    gemini_configured = ai_service.is_configured()

    notion_test = {"success": False, "message": "Notion não configurado"}
    if notion_configured:
        notion_test = notion_service.test_connection()

    return {
        "status": "online",
        "notion": {
            "configured": notion_configured,
            "connected": notion_test.get("success", False),
            "database_title": notion_test.get("database_title", ""),
            "database_id": notion_service.database_id,
            "message": notion_test.get("message", "Conexão ativa com Notion Database")
        },
        "gemini": {
            "configured": gemini_configured,
            "api_key_present": bool(os.getenv("GEMINI_API_KEY"))
        }
    }


@app.get("/api/leads")
async def listar_leads(filtro_status: Optional[str] = Query(None, alias="status", description="Filtro opcional por status")):
    """Consulta e retorna os leads direto do Notion."""
    if not notion_service.is_configured():
        leads = list(_session_leads_cache.values())
        if filtro_status and filtro_status not in ("Todos", "todos", ""):
            leads = [l for l in leads if l.get("status") == filtro_status]
        return {
            "leads": leads,
            "total": len(leads),
            "filtro": filtro_status or "Todos",
            "warning": "NOTION_API_KEY ou NOTION_DATABASE_ID ainda não configurados no arquivo .env (modo demonstração local ativo)"
        }

    try:
        leads = notion_service.listar_leads(filtro_status=filtro_status)
        return {
            "leads": leads,
            "total": len(leads),
            "filtro": filtro_status or "Todos"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar leads no Notion: {str(e)}"
        )


@app.post("/api/prospectar")
async def prospectar(req: ProspectarRequest):
    """
    Roda a extração via Playwright no Google Maps e audita URLs (Tipo A / Tipo B).
    NÃO salva automaticamente no Notion; armazena em buffer de sessão e retorna
    para seleção e envio controlado pelo usuário.
    """
    try:
        # Executa Playwright scraper
        leads_extraidos = await scraper.prospectar(
            nicho=req.nicho,
            localizacao=req.localizacao,
            limite=req.limite
        )

        preparados = []
        for item in leads_extraidos:
            lead_id = f"lead_{uuid.uuid4().hex[:10]}"
            item["id"] = lead_id
            item["has_demo"] = bool(item.get("demo_html"))
            item["synced_notion"] = False
            item["notion_url"] = ""
            item["status"] = item.get("status") or "Novo Lead"

            _session_leads_cache[lead_id] = item
            preparados.append(item)

        return {
            "success": True,
            "total_extraidos": len(preparados),
            "leads": preparados,
            "notion_configured": notion_service.is_configured()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na prospecção: {str(e)}")


@app.post("/api/leads/enviar-notion")
async def enviar_leads_para_notion(req: EnviarNotionRequest):
    """
    Recebe a lista de leads selecionados pelo usuário, salva cada um no Notion Database
    e retorna os dados atualizados com os page_id oficiais do Notion.
    """
    if not notion_service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="NOTION_API_KEY ou NOTION_DATABASE_ID não configurados no arquivo .env"
        )

    try:
        notion_service.garantir_estrutura_database()
    except Exception:
        pass

    sincronizados = []
    erros = []

    for lead_input in req.leads:
        temp_id = lead_input.get("id", "")
        # Mescla com dados do cache de sessão (preserva pitch/demo caso gerados em buffer)
        dados_completos = dict(_session_leads_cache.get(temp_id, {}))
        dados_completos.update(lead_input)

        nome = dados_completos.get("nome", "Sem Nome")
        try:
            page_id = notion_service.salvar_lead(dados_completos)

            # Se tiver demo_html gerado, tenta também anexar bloco de código
            if dados_completos.get("demo_html"):
                try:
                    notion_service.salvar_bloco_codigo_html(page_id, dados_completos["demo_html"])
                except Exception:
                    pass

            dados_completos["id"] = page_id
            dados_completos["synced_notion"] = True
            dados_completos["notion_url"] = f"https://notion.so/{page_id.replace('-', '')}"

            # Atualiza cache de sessão
            if temp_id and temp_id in _session_leads_cache:
                del _session_leads_cache[temp_id]
            _session_leads_cache[page_id] = dados_completos

            sincronizados.append(dados_completos)
        except Exception as ex:
            erros.append(f"{nome}: {str(ex)}")

    return {
        "success": True,
        "total_enviados": len(sincronizados),
        "leads": sincronizados,
        "erros": erros
    }


@app.post("/api/leads/{page_id}/gerar-pitch")
async def gerar_pitch_lead(page_id: str):
    """Gera o pitch consultivo com Gemini e salva na propriedade do Notion correspondente."""
    try:
        lead = _obter_lead_hibrido(page_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado no Notion ou sessão")

        # Gera o pitch via Gemini
        pitch_texto = ai_service.gerar_pitch(lead)

        # Atualiza a propriedade "Pitch WhatsApp" e o status para "Pitch Gerado"
        updates = {
            "pitch_whatsapp": pitch_texto,
            "status": "Pitch Gerado"
        }
        _atualizar_lead_hibrido(page_id, updates)

        return {
            "success": True,
            "page_id": page_id,
            "pitch": pitch_texto,
            "novo_status": "Pitch Gerado"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar pitch: {str(e)}")


@app.put("/api/leads/{page_id}/pitch")
async def salvar_pitch_manual(page_id: str, payload: PitchUpdateRequest):
    """Atualiza o texto do pitch editado pelo usuário diretamente no Notion."""
    try:
        _atualizar_lead_hibrido(page_id, {"pitch_whatsapp": payload.pitch})
        return {"success": True, "page_id": page_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar pitch no Notion: {str(e)}")


@app.post("/api/leads/{page_id}/gerar-prompt-studio")
async def gerar_prompt_studio_lead(page_id: str):
    """
    Extrai inteligência do site existente do lead (se houver) e gera um Super Prompt
    hiperpersonalizado para o usuário colar diretamente no Google AI Studio (Build with Gemini).
    """
    try:
        lead = _obter_lead_hibrido(page_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado no Notion ou sessão")

        # Se o lead tiver website original válido, extrai o conteúdo real
        website = lead.get("website_original", "")
        conteudo_site = {}
        if website:
            try:
                conteudo_site = extrair_conteudo_site(website)
            except Exception:
                pass

        # Gera o Super Prompt personalizado
        prompt_texto = ai_service.gerar_prompt_ai_studio(lead, conteudo_extraido=conteudo_site)

        # Atualiza dados no lead (sessão/cache)
        updates = {
            "prompt_studio": prompt_texto,
            "conteudo_extraido": conteudo_site
        }
        _atualizar_lead_hibrido(page_id, updates)

        return {
            "success": True,
            "page_id": page_id,
            "prompt": prompt_texto,
            "conteudo_extraido": conteudo_site,
            "has_site_content": bool(conteudo_site.get("tem_conteudo"))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar prompt para AI Studio: {str(e)}")


@app.post("/api/leads/{page_id}/gerar-site")
async def gerar_site_lead(page_id: str):
    """Gera a Landing Page com Gemini e salva o código HTML no Notion."""
    try:
        lead = _obter_lead_hibrido(page_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado no Notion ou sessão")

        # Gera o código HTML completo da Landing Page
        html_code = ai_service.gerar_landing_page(lead)

        # Salva na propriedade "Demo HTML" do Notion
        updates = {
            "demo_html": html_code,
            "has_demo": True
        }
        _atualizar_lead_hibrido(page_id, updates)

        # Opcionalmente sincroniza bloco de código na página do Notion
        if notion_service.is_configured() and not page_id.startswith("lead_"):
            try:
                notion_service.salvar_bloco_codigo_html(page_id, html_code)
            except Exception:
                pass

        return {
            "success": True,
            "page_id": page_id,
            "preview_url": f"/preview/{page_id}",
            "tamanho_html": len(html_code)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar landing page: {str(e)}")


@app.get("/preview/{page_id}", response_class=HTMLResponse)
async def preview_landing_page(page_id: str):
    """
    Lê o HTML salvo no Notion e renderiza diretamente no navegador como uma página funcional para demonstração.
    """
    try:
        lead = _obter_lead_hibrido(page_id)
        if not lead:
            return HTMLResponse(
                content="<h2 style='font-family:sans-serif;text-align:center;margin-top:50px;'>Lead não encontrado.</h2>",
                status_code=404
            )

        html_content = lead.get("demo_html")
        if not html_content:
            # Se ainda não foi gerado, gera sob demanda
            html_content = ai_service.gerar_landing_page(lead)
            _atualizar_lead_hibrido(page_id, {"demo_html": html_content, "has_demo": True})

        return HTMLResponse(content=html_content, status_code=200)

    except Exception as e:
        return HTMLResponse(
            content=f"<h2 style='font-family:sans-serif;text-align:center;margin-top:50px;'>Erro ao carregar prévia: {str(e)}</h2>",
            status_code=500
        )


@app.get("/api/leads/{page_id}")
async def obter_detalhes_lead(page_id: str):
    """Retorna os dados completos de um lead específico."""
    lead = _obter_lead_hibrido(page_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


@app.patch("/api/leads/{page_id}/status")
async def atualizar_status_lead(page_id: str, payload: StatusUpdateRequest):
    """Altera a propriedade 'Status' no Notion."""
    try:
        _atualizar_lead_hibrido(page_id, {"status": payload.status})
        return {
            "success": True,
            "page_id": page_id,
            "status": payload.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar status: {str(e)}")


@app.delete("/api/leads/{page_id}")
async def arquivar_lead(page_id: str):
    """Remove (arquiva) o lead diretamente no Notion Database e no cache da sessão."""
    try:
        if page_id in _session_leads_cache:
            del _session_leads_cache[page_id]

        if notion_service.is_configured() and not page_id.startswith("lead_"):
            notion_service.arquivar_lead(page_id)

        return {
            "success": True,
            "page_id": page_id,
            "message": "Lead removido com sucesso"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao arquivar lead: {str(e)}")


@app.post("/api/notion/setup")
async def configurar_notion_database():
    """Garante que a estrutura de colunas do Notion Database esteja atualizada com todas as regras de negócio."""
    if not notion_service.is_configured():
        raise HTTPException(status_code=400, detail="Notion não configurado no arquivo .env")
    try:
        ok = notion_service.garantir_estrutura_database()
        return {
            "success": ok,
            "message": "Estrutura do banco de dados no Notion verificada e atualizada com sucesso!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao estruturar banco no Notion: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
