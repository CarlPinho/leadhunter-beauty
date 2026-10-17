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
                "Demo HTML": {"rich_text": {}},
                "Link Maps": {"url": {}}
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

    def _build_properties_payload(self, data: dict, schema: dict, is_create: bool = False) -> Dict[str, Any]:
        """
        Monta o dicionário de propriedades formatado para a API do Notion,
        respeitando os tipos do schema e os limites de caracteres (máx 2000 por bloco).
        """
        status_prop_type = schema.get("Status", {}).get("type", "select")
        bairro_prop_type = schema.get("Bairro", {}).get("type", "rich_text")
        tel_prop_type = schema.get("Telefone", {}).get("type", "phone_number")

        properties: Dict[str, Any] = {}

        # 1. Nome (title)
        if "nome" in data and data["nome"]:
            properties["Nome"] = {
                "title": [{"type": "text", "text": {"content": str(data["nome"]).strip()[:100]}}]
            }
        elif is_create:
            properties["Nome"] = {
                "title": [{"type": "text", "text": {"content": "Lead Sem Nome"}}]
            }

        # 2. Nicho (select)
        if "nicho" in data and data["nicho"]:
            properties["Nicho"] = {"select": {"name": str(data["nicho"]).strip()[:50]}}

        # 3. Bairro (rich_text ou select)
        if "bairro" in data and data["bairro"]:
            bairro_val = str(data["bairro"]).strip()[:100]
            if bairro_prop_type == "select":
                properties["Bairro"] = {"select": {"name": bairro_val}}
            else:
                properties["Bairro"] = {"rich_text": [{"type": "text", "text": {"content": bairro_val}}]}

        # 4. Telefone (phone_number ou rich_text)
        if "telefone" in data and data["telefone"]:
            tel_val = str(data["telefone"]).strip()[:30]
            if tel_prop_type == "phone_number":
                properties["Telefone"] = {"phone_number": tel_val}
            else:
                properties["Telefone"] = {"rich_text": [{"type": "text", "text": {"content": tel_val}}]}

        # 5. Link WhatsApp (url)
        if "link_whatsapp" in data and data["link_whatsapp"]:
            properties["Link WhatsApp"] = {"url": str(data["link_whatsapp"]).strip()}

        # 6. Nota (number)
        if "nota" in data and data["nota"] is not None:
            try:
                properties["Nota"] = {"number": float(data["nota"])}
            except (ValueError, TypeError):
                pass

        # 7. Qtd Reviews (number)
        if "qtd_reviews" in data and data["qtd_reviews"] is not None:
            try:
                properties["Qtd Reviews"] = {"number": int(data["qtd_reviews"])}
            except (ValueError, TypeError):
                pass

        # 8. Website Original (url)
        if "website_original" in data and data["website_original"]:
            properties["Website Original"] = {"url": str(data["website_original"]).strip()}

        # 9. Classificação (select)
        if "classificacao" in data and data["classificacao"]:
            properties["Classificação"] = {"select": {"name": str(data["classificacao"]).strip()}}

        # 10. Status (status ou select)
        if "status" in data and data["status"]:
            status_val = str(data["status"]).strip()
            if status_prop_type == "status":
                properties["Status"] = {"status": {"name": status_val}}
            else:
                properties["Status"] = {"select": {"name": status_val}}
        elif is_create:
            status_default = "Novo Lead"
            if status_prop_type == "status":
                properties["Status"] = {"status": {"name": status_default}}
            else:
                properties["Status"] = {"select": {"name": status_default}}

        # 11. Pitch WhatsApp (rich_text)
        if "pitch_whatsapp" in data and data["pitch_whatsapp"]:
            properties["Pitch WhatsApp"] = {"rich_text": _chunk_rich_text(str(data["pitch_whatsapp"]))}

        # 12. Demo HTML (rich_text)
        if "demo_html" in data and data["demo_html"]:
            properties["Demo HTML"] = {"rich_text": _chunk_rich_text(str(data["demo_html"]))}

        # 13. Link Maps (url)
        maps_link = data.get("maps_url") or data.get("link_maps")
        if maps_link:
            properties["Link Maps"] = {"url": str(maps_link).strip()}

        return properties

    def salvar_lead(self, lead_data: dict) -> str:
        """
        Insere um novo lead no Notion verificando duplicidade por Nome ou Telefone.
        Se já existir, atualiza os dados completos. Retorna o page_id.
        """
        nome = (lead_data.get("nome") or "").strip()
        telefone = (lead_data.get("telefone") or "").strip()

        if not nome:
            raise ValueError("O lead precisa ter ao menos um 'Nome'")

        schema = self._get_schema()

        # 1. Checagem de duplicidade por Nome
        try:
            filtro_nome = {"property": "Nome", "title": {"equals": nome}}
            query_res = self.client.databases.query(
                database_id=self.database_id,
                filter=filtro_nome,
                page_size=1
            )
            if query_res.get("results"):
                page_id = query_res["results"][0]["id"]
                logger.info(f"Lead já cadastrado com o nome '{nome}' (ID: {page_id}). Atualizando dados...")
                self.atualizar_lead(page_id, lead_data)
                return page_id
        except Exception as e:
            logger.warning(f"Erro ao verificar duplicidade por nome no Notion: {e}")

        # 2. Checagem opcional de duplicidade por Telefone se fornecido
        if telefone and "Telefone" in schema:
            try:
                tel_type = schema["Telefone"].get("type", "phone_number")
                filtro_tel = (
                    {"property": "Telefone", "phone_number": {"equals": telefone}}
                    if tel_type == "phone_number"
                    else {"property": "Telefone", "rich_text": {"equals": telefone}}
                )
                query_tel = self.client.databases.query(
                    database_id=self.database_id,
                    filter=filtro_tel,
                    page_size=1
                )
                if query_tel.get("results"):
                    page_id = query_tel["results"][0]["id"]
                    logger.info(f"Lead já cadastrado com o telefone '{telefone}' (ID: {page_id}). Atualizando dados...")
                    self.atualizar_lead(page_id, lead_data)
                    return page_id
            except Exception as e:
                logger.debug(f"Verificação de duplicidade por telefone ignorada: {e}")

        # 3. Criação de nova página
        properties = self._build_properties_payload(lead_data, schema, is_create=True)
        nova_pagina = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties
        )
        return nova_pagina["id"]

    def listar_leads(self, filtro_status: Optional[str] = None, max_results: int = 300) -> List[Dict[str, Any]]:
        """
        Recupera os registros do Notion para exibir no frontend com suporte a paginação
        e ordenação por data de criação decrescente.
        """
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

        query_args: Dict[str, Any] = {
            "database_id": self.database_id,
            "page_size": 100,
            "sorts": [{"timestamp": "created_time", "direction": "descending"}]
        }
        if filtro:
            query_args["filter"] = filtro

        leads = []
        has_more = True
        start_cursor = None

        while has_more and len(leads) < max_results:
            if start_cursor:
                query_args["start_cursor"] = start_cursor

            try:
                response = self.client.databases.query(**query_args)
            except Exception as e:
                # Se falhar pelo parâmetro 'sorts', tenta novamente sem sorts
                if "sorts" in query_args:
                    del query_args["sorts"]
                    response = self.client.databases.query(**query_args)
                else:
                    logger.error(f"Erro ao consultar leads no Notion: {e}")
                    raise e

            results = response.get("results", [])
            for page in results:
                leads.append(self._parse_page_to_lead(page))

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
            if not start_cursor:
                break

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
        """Atualiza quaisquer propriedades do lead no Notion (status, pitch, demo, dados de contato, etc.)."""
        schema = self._get_schema()
        properties = self._build_properties_payload(updates, schema, is_create=False)

        if not properties:
            return self.obter_lead(page_id)

        res = self.client.pages.update(page_id=page_id, properties=properties)
        return self._parse_page_to_lead(res)

    def arquivar_lead(self, page_id: str) -> bool:
        """Arquiva (remove) um lead do Notion Database."""
        try:
            self.client.pages.update(page_id=page_id, archived=True)
            logger.info(f"Lead arquivado com sucesso no Notion (ID: {page_id})")
            return True
        except Exception as e:
            logger.error(f"Erro ao arquivar lead no Notion (ID: {page_id}): {e}")
            raise

    def salvar_bloco_codigo_html(self, page_id: str, html_code: str) -> bool:
        """
        Opcionalmente adiciona o código HTML da landing page como um bloco de código
        dentro do corpo da página do Notion.
        """
        try:
            self.client.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "caption": [{"type": "text", "text": {"content": "Landing Page Preview HTML (Tailwind CSS)"}}],
                            "rich_text": _chunk_rich_text(html_code),
                            "language": "html"
                        }
                    }
                ]
            )
            return True
        except Exception as e:
            logger.warning(f"Não foi possível salvar bloco de código HTML na página {page_id}: {e}")
            return False

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

        # Link Maps (url)
        maps_url = props.get("Link Maps", {}).get("url") or ""

        return {
            "id": page_id,
            "nome": nome,
            "nicho": nicho,
            "bairro": bairro,
            "telefone": telefone,
            "link_whatsapp": link_whatsapp,
            "maps_url": maps_url,
            "nota": nota,
            "qtd_reviews": qtd_reviews,
            "website_original": website_original,
            "classificacao": classificacao,
            "status": status,
            "pitch_whatsapp": pitch_whatsapp,
            "demo_html": demo_html,
            "has_demo": bool(demo_html),
            "synced_notion": True,
            "notion_url": page.get("url", f"https://notion.so/{page_id.replace('-', '')}")
        }
