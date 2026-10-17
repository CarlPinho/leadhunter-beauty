"""
Módulo de Web Scraping com Playwright para o Google Maps.
LeadHunter Beauty.
"""

import asyncio
import re
import urllib.parse
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

from app.auditor import auditar_url, get_whatsapp_link, format_whatsapp_number

logger = logging.getLogger(__name__)


def _extrair_bairro(endereco: str, fallback_localizacao: str = "") -> str:
    """Tenta isolar o bairro a partir do endereço completo do Google Maps."""
    if not endereco:
        return fallback_localizacao.split(",")[0].strip()

    # Formatos comuns no Brasil:
    # "R. Guaipá, 123 - Vila Leopoldina, São Paulo - SP, 05089-000"
    # "Av. Paulista, 1000 - Bela Vista, São Paulo"
    partes = [p.strip() for p in endereco.split("-")]
    if len(partes) >= 2:
        # Pega a parte logo após o primeiro hífen
        trecho = partes[1].split(",")[0].strip()
        if trecho and not trecho.isdigit() and len(trecho) > 2:
            return trecho

    partes_virgula = [p.strip() for p in endereco.split(",")]
    if len(partes_virgula) >= 3:
        trecho = partes_virgula[1].strip()
        if trecho and not trecho.isdigit() and len(trecho) > 2:
            return trecho

    return fallback_localizacao.split(",")[0].strip() if fallback_localizacao else "Região Central"


def _limpar_url_google(url_bruta: str) -> str:
    """Desembrulha URLs do tipo https://www.google.com/url?q=..."""
    if not url_bruta:
        return ""
    if "google.com/url?" in url_bruta:
        try:
            parsed = urllib.parse.urlparse(url_bruta)
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                return qs["q"][0]
        except Exception:
            pass
    return url_bruta


async def _lidar_com_consentimento(page: Page):
    """Fecha banners ou modais de consentimento do Google se existirem."""
    try:
        botoes = page.locator('button:has-text("Aceitar tudo"), button:has-text("Rejeitar tudo"), button:has-text("Concordo"), form button:has-text("Aceitar")')
        if await botoes.count() > 0:
            await botoes.first.click(timeout=3000)
            await page.wait_for_timeout(1000)
    except Exception:
        pass


class GoogleMapsScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def prospectar(self, nicho: str, localizacao: str, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Navega no Google Maps para o termo de busca '{nicho} em {localizacao}',
        rola os resultados e extrai detalhes de cada estabelecimento.
        """
        termo_busca = f"{nicho} em {localizacao}"
        url_busca = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(termo_busca)}?hl=pt-BR"
        logger.info(f"Iniciando raspagem no Google Maps: {termo_busca} (limite: {limite})")

        resultados: List[Dict[str, Any]] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="pt-BR"
            )
            page = await context.new_page()

            try:
                await page.goto(url_busca, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(2000)
                await _lidar_com_consentimento(page)

                # Localiza o container de lista (feed)
                feed_selector = 'div[role="feed"]'
                try:
                    await page.wait_for_selector(feed_selector, timeout=12000)
                except PlaywrightTimeoutError:
                    # Pode ter aberto diretamente um único resultado ou lista simples
                    logger.warning("Feed div[role='feed'] não encontrado no tempo limite. Tentando extração alternativa...")

                # Rolagem progressiva do feed para carregar o número de itens solicitado
                itens_processados = set()
                tentativas_scroll = 0
                max_scrolls = max(5, limite * 2)

                while tentativas_scroll < max_scrolls:
                    # Links de estabelecimentos (a.hfpxzc é a classe padrão de cards do Maps)
                    place_links = await page.locator('a.hfpxzc').all()
                    
                    if len(place_links) >= limite or await page.locator("text='Você chegou ao final da lista'").count() > 0:
                        break

                    # Rola o feed para baixo
                    feed_element = page.locator(feed_selector)
                    if await feed_element.count() > 0:
                        await feed_element.evaluate("el => el.scrollBy(0, 1500)")
                    else:
                        await page.mouse.wheel(0, 1500)

                    await page.wait_for_timeout(1500)
                    tentativas_scroll += 1

                # Agora itera sobre os cards de estabelecimentos encontrados
                raw_place_links = await page.locator('a.hfpxzc').all()
                place_links = []
                for p_link in raw_place_links:
                    label = (await p_link.get_attribute("aria-label") or "").strip()
                    if label and not label.lower().startswith("resultado"):
                        place_links.append(p_link)

                logger.info(f"Total de estabelecimentos válidos no feed: {len(place_links)}")

                # Se nenhum card foi listado, pode ter aberto diretamente o estabelecimento
                if len(place_links) == 0:
                    h1_el = page.locator('h1.DUwDvf, h1.fontHeadlineLarge, div[role="main"] h1')
                    if await h1_el.count() > 0:
                        logger.info("Google Maps abriu diretamente a página do estabelecimento. Extraindo dados...")
                        detalhes = await self._extrair_detalhes_painel(page)
                        nome = detalhes.get("nome") or "Estabelecimento"
                        endereco = detalhes.get("endereco", "")
                        bairro = _extrair_bairro(endereco, fallback_localizacao=localizacao)
                        telefone = detalhes.get("telefone", "")
                        website = _limpar_url_google(detalhes.get("website", ""))
                        link_wa = get_whatsapp_link(telefone)
                        auditoria = await auditar_url(website)

                        lead = {
                            "nome": nome,
                            "nicho": nicho,
                            "bairro": bairro,
                            "endereco": endereco,
                            "telefone": telefone,
                            "link_whatsapp": link_wa,
                            "nota": detalhes.get("nota"),
                            "qtd_reviews": detalhes.get("qtd_reviews"),
                            "website_original": website,
                            "classificacao": auditoria["classificacao"],
                            "motivo_auditoria": auditoria["motivo"],
                            "status": "Novo Lead",
                            "pitch_whatsapp": "",
                            "demo_html": ""
                        }
                        resultados.append(lead)
                        return resultados

                alvos = place_links[:limite]

                for index, link_locator in enumerate(alvos):
                    try:
                        aria_label = (await link_locator.get_attribute("aria-label") or "").strip()
                        href = await link_locator.get_attribute("href") or ""

                        if not aria_label and not href:
                            continue

                        # Clica no item para abrir o painel lateral de detalhes
                        try:
                            await link_locator.scroll_into_view_if_needed(timeout=2000)
                            await link_locator.click(force=True, timeout=3000)
                        except Exception:
                            try:
                                await link_locator.evaluate("el => el.click()")
                            except Exception:
                                pass
                        await page.wait_for_timeout(1500)

                        # Extrai dados do painel aberto
                        detalhes = await self._extrair_detalhes_painel(page, fallback_nome=aria_label)
                        
                        nome = detalhes.get("nome") or aria_label
                        if not nome or nome.lower().startswith("resultado"):
                            nome = aria_label or f"Espaço {index+1}"

                        if nome in itens_processados:
                            continue
                        itens_processados.add(nome)

                        endereco = detalhes.get("endereco", "")
                        bairro = _extrair_bairro(endereco, fallback_localizacao=localizacao)
                        telefone = detalhes.get("telefone", "")
                        website = _limpar_url_google(detalhes.get("website", ""))
                        link_wa = get_whatsapp_link(telefone)

                        # Executa auditoria da URL
                        auditoria = await auditar_url(website)

                        lead = {
                            "nome": nome,
                            "nicho": nicho,
                            "bairro": bairro,
                            "endereco": endereco,
                            "telefone": telefone,
                            "link_whatsapp": link_wa,
                            "nota": detalhes.get("nota"),
                            "qtd_reviews": detalhes.get("qtd_reviews"),
                            "website_original": website,
                            "classificacao": auditoria["classificacao"],
                            "motivo_auditoria": auditoria["motivo"],
                            "status": "Novo Lead",
                            "pitch_whatsapp": "",
                            "demo_html": ""
                        }

                        logger.info(f"Lead extraído [{index+1}/{len(alvos)}]: {nome} | {auditoria['classificacao']} | Tel: {telefone or 'Sem tel'}")
                        resultados.append(lead)

                    except Exception as ex_item:
                        logger.warning(f"Erro ao extrair item {index+1}: {ex_item}")
                        continue

            except Exception as e:
                logger.error(f"Erro geral no scraper do Google Maps: {e}")
            finally:
                await context.close()
                await browser.close()

        logger.info(f"Raspagem finalizada com sucesso. Total de leads extraídos: {len(resultados)}")
        return resultados

    async def _extrair_detalhes_painel(self, page: Page, fallback_nome: str = "") -> Dict[str, Any]:
        """Extrai os campos de um estabelecimento com o painel lateral aberto."""
        dados: Dict[str, Any] = {
            "nome": fallback_nome,
            "nota": None,
            "qtd_reviews": None,
            "telefone": "",
            "endereco": "",
            "website": ""
        }

        # 1. Nome
        try:
            nome_el = page.locator('h1.DUwDvf, h1.fontHeadlineLarge, div[role="main"] h1')
            if await nome_el.count() > 0:
                texto_nome = (await nome_el.first.inner_text()).strip()
                if texto_nome:
                    dados["nome"] = texto_nome
        except Exception:
            pass

        # 2. Nota (Rating)
        try:
            rating_el = page.locator('span.ceNzKf, div[role="main"] span.MW4etd, span[aria-label*="estrelas"]')
            if await rating_el.count() > 0:
                texto_rating = await rating_el.first.inner_text()
                # Converte '4,8' para 4.8
                num_match = re.search(r"(\d+[\.,]\d+)", texto_rating)
                if num_match:
                    dados["nota"] = float(num_match.group(1).replace(",", "."))
                else:
                    aria = await rating_el.first.get_attribute("aria-label") or ""
                    num_match = re.search(r"(\d+[\.,]\d+)", aria)
                    if num_match:
                        dados["nota"] = float(num_match.group(1).replace(",", "."))
        except Exception:
            pass

        # 3. Quantidade de Reviews
        try:
            reviews_el = page.locator('span.UY7F9, div[role="main"] button span:has-text("avaliações"), div[role="main"] span:has-text("avaliações")')
            if await reviews_el.count() > 0:
                texto_rev = await reviews_el.first.inner_text()
                # Extrai números: "(142)" ou "142 avaliações"
                rev_digits = re.sub(r"\D", "", texto_rev)
                if rev_digits:
                    dados["qtd_reviews"] = int(rev_digits)
        except Exception:
            pass

        # 4. Website
        try:
            site_el = page.locator('a[data-item-id="authority"], a[data-tooltip*="Abrir o site" i], a[aria-label*="Website:" i], a[aria-label*="Site:" i], a[data-value*="Abrir o site" i], a[data-value*="site" i]')
            if await site_el.count() > 0:
                href = await site_el.first.get_attribute("href")
                if href:
                    dados["website"] = href.strip()
        except Exception:
            pass

        # 5. Telefone
        try:
            tel_el = page.locator('button[data-tooltip*="telefone" i], button[data-item-id*="phone:tel:"], button[aria-label*="Telefone:" i], button[aria-label*="Telefone" i], button[data-tooltip*="phone" i]')
            if await tel_el.count() > 0:
                aria = await tel_el.first.get_attribute("aria-label") or ""
                # O aria-label geralmente vem como "Telefone: (11) 98765-4321"
                if "Telefone:" in aria or "Phone:" in aria:
                    dados["telefone"] = aria.split(":")[-1].strip()
                elif "Telefone" in aria:
                    num_match = re.search(r"(\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4})", aria)
                    if num_match:
                        dados["telefone"] = num_match.group(1).strip()
                    else:
                        dados["telefone"] = aria.replace("Telefone", "").strip()
                else:
                    texto = await tel_el.first.inner_text()
                    dados["telefone"] = texto.strip()
        except Exception:
            pass

        # 6. Endereço
        try:
            end_el = page.locator('button[data-item-id="address"], button[data-tooltip*="endereço" i], button[aria-label*="Endereço:" i], button[aria-label*="Endereço" i], button[data-tooltip*="address" i]')
            if await end_el.count() > 0:
                aria = await end_el.first.get_attribute("aria-label") or ""
                if "Endereço:" in aria or "Address:" in aria:
                    dados["endereco"] = aria.split(":")[-1].strip()
                elif "Endereço" in aria:
                    dados["endereco"] = aria.replace("Endereço", "").strip()
                else:
                    dados["endereco"] = (await end_el.first.inner_text()).strip()
        except Exception:
            pass

        return dados
