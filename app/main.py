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
    """Recupera o lead do Notion se configurado, ou do cache em memória."""
    if notion_service.is_configured():
        try:
            return notion_service.obter_lead(page_id)
        except Exception:
            pass
    return _session_leads_cache.get(page_id)


def _atualizar_lead_hibrido(page_id: str, updates: dict):
    """Atualiza o lead no Notion e no cache da sessão."""
    if page_id in _session_leads_cache:
        _session_leads_cache[page_id].update(updates)
    if notion_service.is_configured():
        try:
            return notion_service.atualizar_lead(page_id, updates)
        except Exception:
            pass


# --- Modelos Pydantic ---
class ProspectarRequest(BaseModel):
    nicho: str = Field(default="Extensão de Cílios", description="Nicho de atuação da beleza")
    localizacao: str = Field(default="Vila Leopoldina, São Paulo", description="Bairro ou região para busca")
    limite: int = Field(default=8, ge=1, le=30, description="Quantidade máxima de estabelecimentos a extrair")


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
async def prospectar_e_salvar(req: ProspectarRequest):
    """
    Roda a extração via Playwright no Google Maps,
    audita URLs (Tipo A / Tipo B) e salva os novos registros diretamente no Notion.
    """
    try:
        # Garante as propriedades no Notion antes de salvar se estiver configurado
        if notion_service.is_configured():
            notion_service.garantir_estrutura_database()

        # Executa Playwright scraper
        leads_extraidos = await scraper.prospectar(
            nicho=req.nicho,
            localizacao=req.localizacao,
            limite=req.limite
        )

        salvos = []
        erros_salvamento = []

        for item in leads_extraidos:
            lead_id = f"lead_{uuid.uuid4().hex[:10]}"
            item["id"] = lead_id
            item["has_demo"] = bool(item.get("demo_html"))
            item["notion_url"] = f"https://notion.so/{lead_id}"

            if notion_service.is_configured():
                try:
                    page_id = notion_service.salvar_lead(item)
                    item["id"] = page_id
                    item["notion_url"] = f"https://notion.so/{page_id.replace('-', '')}"
                except Exception as ex_save:
                    erros_salvamento.append(f"{item.get('nome')}: {str(ex_save)}")

            _session_leads_cache[item["id"]] = item
            salvos.append(item)

        return {
            "success": True,
            "total_extraidos": len(leads_extraidos),
            "salvos_notion": len([s for s in salvos if not s["id"].startswith("lead_")]),
            "leads": salvos,
            "erros": erros_salvamento,
            "notion_configured": notion_service.is_configured()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na prospecção: {str(e)}")


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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
