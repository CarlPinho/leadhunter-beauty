"""
Módulo de Integração com Notion Database via notion-client.
LeadHunter Beauty.
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from notion_client import Client

# Carrega variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)


def _chunk_rich_text(text: str, max_chunk: int = 1900) -> List[Dict[str, Any]]:
    """
    Divide um texto longo em blocos de até 1900 caracteres (limite do Notion é 2000 por objeto).
    Retorna lista formatada de objetos rich_text para a API do Notion.
    """
    if not text:
        return []
    chunks = [text[i:i + max_chunk] for i in range(0, len(text), max_chunk)]
    # Notion aceita no máximo 100 objetos por rich_text array
    return [{"type": "text", "text": {"content": c}} for c in chunks[:100]]


def _extract_plain_text(rich_text_list: List[Dict[str, Any]]) -> str:
    """Extrai e concatena o texto puro de um array rich_text do Notion."""
    if not rich_text_list or not isinstance(rich_text_list, list):
        return ""
    return "".join(item.get("plain_text", "") for item in rich_text_list)


class NotionService:
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("NOTION_API_KEY", "")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")
        self._client: Optional[Client] = None
        self._db_schema: Optional[Dict[str, Any]] = None

    @property
    def client(self) -> Client:
        if not self.api_key:
            raise ValueError("NOTION_API_KEY não foi configurada no arquivo .env")
        if not self._client:
            self._client = Client(auth=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        """Verifica se as chaves mínimas estão preenchidas."""
        return bool(self.api_key and self.database_id and "xxx" not in self.api_key and "xxx" not in self.database_id)

    def test_connection(self) -> Dict[str, Any]:
        """Testa a conexão com o Notion e retorna metadados do banco."""
        if not self.is_configured():
            return {
                "success": False,
                "message": "Configurações do Notion ausentes ou com placeholders no arquivo .env"
            }
        try:
            db = self.client.databases.retrieve(database_id=self.database_id)
            title = ""
            if db.get("title") and len(db["title"]) > 0:
                title = db["title"][0].get("plain_text", "")
            return {
                "success": True,
                "database_id": self.database_id,
                "database_title": title,
                "properties": list(db.get("properties", {}).keys())
            }
        except Exception as e:
            logger.error(f"Erro ao testar conexão com Notion: {e}")
            return {
                "success": False,
                "message": f"Erro de autenticação ou acesso ao Notion Database: {str(e)}"
            }

    def _get_schema(self) -> Dict[str, Any]:
        """Recupera e armazena em cache o esquema de propriedades do banco do Notion."""
        if not self._db_schema and self.is_configured():
            try:
                db = self.client.databases.retrieve(database_id=self.database_id)
                self._db_schema = db.get("properties", {})
            except Exception as e:
                logger.warning(f"Não foi possível obter o schema do Notion Database: {e}")
                self._db_schema = {}
        return self._db_schema or {}

    def garantir_estrutura_database(self) -> bool:
        """
        Garante que todas as propriedades exigidas existam no Notion Database.
        Se faltar alguma propriedade, adiciona dinamicamente via databases.update.
        """
        if not self.is_configured():
            return False

        try:
            db = self.client.databases.retrieve(database_id=self.database_id)
            existing_props = db.get("properties", {})

            # Propriedades padrão esperadas
            required_properties = {
                "Nicho": {"select": {}},
                "Bairro": {"rich_text": {}},
                "Telefone": {"phone_number": {}},
                "Link WhatsApp": {"url": {}},
                "Nota": {"number": {"format": "number"}},
                "Qtd Reviews": {"number": {"format": "number"}},
                "Website Original": {"url": {}},
                "Classificação": {
                    "select": {
                        "options": [
                            {"name": "Tipo A (Sem Site)", "color": "purple"},
                            {"name": "Tipo B (Site Obsoleto)", "color": "orange"}
                        ]
                    }
                },
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Novo Lead", "color": "blue"},
                            {"name": "Pitch Gerado", "color": "yellow"},
                            {"name": "Mensagem Enviada", "color": "pink"},
                            {"name": "Em Conversa", "color": "purple"},
                            {"name": "Fechado", "color": "green"},
                            {"name": "Descartado", "color": "gray"}
                        ]
                    }
                },
                "Pitch WhatsApp": {"rich_text": {}},
                "Demo HTML": {"rich_text": {}}
            }

            missing_properties = {}
            for prop_name, prop_def in required_properties.items():
                if prop_name not in existing_props:
                    missing_properties[prop_name] = prop_def

            if missing_properties:
                logger.info(f"Adicionando propriedades ausentes ao Notion: {list(missing_properties.keys())}")
                self.client.databases.update(
                    database_id=self.database_id,
                    properties=missing_properties
                )
                self._db_schema = None  # Invalida cache

            return True
        except Exception as e:
            logger.warning(f"Aviso ao verificar/garantir propriedades do Notion: {e}")
            return False

    def salvar_lead(self, lead_data: dict) -> str:
        """
        Insere um novo lead no Notion verificando duplicidade por Nome/Telefone.
        Retorna o page_id.
        """
        nome = (lead_data.get("nome") or "").strip()
        telefone = (lead_data.get("telefone") or "").strip()

        if not nome:
            raise ValueError("O lead precisa ter ao menos um 'Nome'")

        # 1. Checagem de duplicidade no Notion
        try:
            filtro_duplicidade = {"property": "Nome", "title": {"equals": nome}}
            query_res = self.client.databases.query(
                database_id=self.database_id,
                filter=filtro_duplicidade,
                page_size=1
            )
            if query_res.get("results"):
                page_id = query_res["results"][0]["id"]
                logger.info(f"Lead já cadastrado com o nome '{nome}' (ID: {page_id}). Atualizando dados...")
                self.atualizar_lead(page_id, lead_data)
                return page_id
        except Exception as e:
            logger.warning(f"Erro ao verificar duplicidade por nome no Notion: {e}")

        # Se não existe, monta o payload das propriedades respeitando o schema do banco
        schema = self._get_schema()
        status_prop_type = schema.get("Status", {}).get("type", "select")
        bairro_prop_type = schema.get("Bairro", {}).get("type", "rich_text")
        tel_prop_type = schema.get("Telefone", {}).get("type", "phone_number")

        properties: Dict[str, Any] = {
            "Nome": {
                "title": [{"type": "text", "text": {"content": nome[:100]}}]
            }
        }

        if lead_data.get("nicho"):
            properties["Nicho"] = {"select": {"name": str(lead_data["nicho"])[:50]}}

        if lead_data.get("bairro"):
            bairro_val = str(lead_data["bairro"])[:100]
            if bairro_prop_type == "select":
                properties["Bairro"] = {"select": {"name": bairro_val}}
            else:
                properties["Bairro"] = {"rich_text": [{"type": "text", "text": {"content": bairro_val}}]}

        if telefone:
            if tel_prop_type == "phone_number":
                properties["Telefone"] = {"phone_number": telefone[:30]}
            else:
                properties["Telefone"] = {"rich_text": [{"type": "text", "text": {"content": telefone[:30]}}]}

        if lead_data.get("link_whatsapp"):
            properties["Link WhatsApp"] = {"url": lead_data["link_whatsapp"]}

        if lead_data.get("nota") is not None:
            try:
                properties["Nota"] = {"number": float(lead_data["nota"])}
            except (ValueError, TypeError):
                pass

        if lead_data.get("qtd_reviews") is not None:
            try:
                properties["Qtd Reviews"] = {"number": int(lead_data["qtd_reviews"])}
            except (ValueError, TypeError):
                pass

        if lead_data.get("website_original"):
            properties["Website Original"] = {"url": lead_data["website_original"]}

        if lead_data.get("classificacao"):
            properties["Classificação"] = {"select": {"name": lead_data["classificacao"]}}

        # Status inicial
        status_inicial = lead_data.get("status") or "Novo Lead"
        if status_prop_type == "status":
            properties["Status"] = {"status": {"name": status_inicial}}
        else:
            properties["Status"] = {"select": {"name": status_inicial}}

        if lead_data.get("pitch_whatsapp"):
            properties["Pitch WhatsApp"] = {"rich_text": _chunk_rich_text(lead_data["pitch_whatsapp"])}

        if lead_data.get("demo_html"):
            properties["Demo HTML"] = {"rich_text": _chunk_rich_text(lead_data["demo_html"])}

        nova_pagina = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties
        )
        return nova_pagina["id"]

    def listar_leads(self, filtro_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera os registros do Notion para exibir no frontend."""
        if not self.is_configured():
            return []

        filtro = None
        if filtro_status and filtro_status not in ("Todos", "todos", ""):
            schema = self._get_schema()
            status_type = schema.get("Status", {}).get("type", "select")
            if status_type == "status":
                filtro = {"property": "Status", "status": {"equals": filtro_status}}
            else:
                filtro = {"property": "Status", "select": {"equals": filtro_status}}

        query_args: Dict[str, Any] = {"database_id": self.database_id}
        if filtro:
            query_args["filter"] = filtro

        response = self.client.databases.query(**query_args)
        results = response.get("results", [])

        leads = []
        for page in results:
            leads.append(self._parse_page_to_lead(page))
        return leads

    def obter_lead(self, page_id: str) -> Dict[str, Any]:
        """Recupera os dados de uma página específica no Notion."""
        page = self.client.pages.retrieve(page_id=page_id)
        lead = self._parse_page_to_lead(page)

        # Se o Demo HTML não estava completo na propriedade, tenta ler blocos da página
        if not lead.get("demo_html"):
            try:
                blocks = self.client.blocks.children.list(block_id=page_id).get("results", [])
                for b in blocks:
                    if b.get("type") == "code":
                        lead["demo_html"] = _extract_plain_text(b["code"].get("rich_text", []))
                        break
            except Exception as e:
                logger.debug(f"Não foi possível ler blocos adicionais da página {page_id}: {e}")

        return lead

    def atualizar_lead(self, page_id: str, updates: dict) -> Dict[str, Any]:
        """Atualiza status, pitch gerado ou HTML do site no Notion."""
        schema = self._get_schema()
        status_prop_type = schema.get("Status", {}).get("type", "select")

        properties: Dict[str, Any] = {}

        if "status" in updates and updates["status"]:
            if status_prop_type == "status":
                properties["Status"] = {"status": {"name": updates["status"]}}
            else:
                properties["Status"] = {"select": {"name": updates["status"]}}

        if "pitch_whatsapp" in updates:
            properties["Pitch WhatsApp"] = {"rich_text": _chunk_rich_text(updates["pitch_whatsapp"])}

        if "demo_html" in updates:
            properties["Demo HTML"] = {"rich_text": _chunk_rich_text(updates["demo_html"])}

        if "classificacao" in updates:
            properties["Classificação"] = {"select": {"name": updates["classificacao"]}}

        if "link_whatsapp" in updates:
            properties["Link WhatsApp"] = {"url": updates["link_whatsapp"]}

        res = self.client.pages.update(page_id=page_id, properties=properties)
        return self._parse_page_to_lead(res)

    def _parse_page_to_lead(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Converte uma página bruta da API do Notion em um dicionário limpo para a aplicação."""
        page_id = page["id"]
        props = page.get("properties", {})

        # Nome (title)
        nome = ""
        nome_prop = props.get("Nome", {})
        if nome_prop.get("title"):
            nome = _extract_plain_text(nome_prop["title"])

        # Nicho (select)
        nicho = ""
        nicho_prop = props.get("Nicho", {})
        if nicho_prop.get("select"):
            nicho = nicho_prop["select"].get("name", "")

        # Bairro (rich_text ou select)
        bairro = ""
        bairro_prop = props.get("Bairro", {})
        if bairro_prop.get("type") == "select" and bairro_prop.get("select"):
            bairro = bairro_prop["select"].get("name", "")
        elif bairro_prop.get("rich_text"):
            bairro = _extract_plain_text(bairro_prop["rich_text"])

        # Telefone (phone_number ou rich_text)
        telefone = ""
        tel_prop = props.get("Telefone", {})
        if tel_prop.get("phone_number"):
            telefone = tel_prop["phone_number"]
        elif tel_prop.get("rich_text"):
            telefone = _extract_plain_text(tel_prop["rich_text"])

        # Link WhatsApp (url)
        link_whatsapp = props.get("Link WhatsApp", {}).get("url") or ""

        # Nota (number)
        nota = props.get("Nota", {}).get("number")

        # Qtd Reviews (number)
        qtd_reviews = props.get("Qtd Reviews", {}).get("number")

        # Website Original (url)
        website_original = props.get("Website Original", {}).get("url") or ""

        # Classificação (select)
        classificacao = ""
        class_prop = props.get("Classificação", {})
        if class_prop.get("select"):
            classificacao = class_prop["select"].get("name", "")

        # Status (status ou select)
        status = "Novo Lead"
        status_prop = props.get("Status", {})
        if status_prop.get("status"):
            status = status_prop["status"].get("name", "Novo Lead")
        elif status_prop.get("select"):
            status = status_prop["select"].get("name", "Novo Lead")

        # Pitch WhatsApp (rich_text)
        pitch_whatsapp = _extract_plain_text(props.get("Pitch WhatsApp", {}).get("rich_text", []))

        # Demo HTML (rich_text)
        demo_html = _extract_plain_text(props.get("Demo HTML", {}).get("rich_text", []))

        return {
            "id": page_id,
            "nome": nome,
            "nicho": nicho,
            "bairro": bairro,
            "telefone": telefone,
            "link_whatsapp": link_whatsapp,
            "nota": nota,
            "qtd_reviews": qtd_reviews,
            "website_original": website_original,
            "classificacao": classificacao,
            "status": status,
            "pitch_whatsapp": pitch_whatsapp,
            "demo_html": demo_html,
            "has_demo": bool(demo_html),
            "notion_url": page.get("url", f"https://notion.so/{page_id.replace('-', '')}")
        }
