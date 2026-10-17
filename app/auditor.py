"""
Módulo de Auditoria de URLs e Classificação de Leads (Tipo A / Tipo B).
LeadHunter Beauty.
"""

from urllib.parse import urlparse
import re
import httpx
from bs4 import BeautifulSoup


# Domínios e plataformas que não contam como site próprio institucional
SOCIAL_AND_BIO_DOMAINS = {
    "instagram.com",
    "instagr.am",
    "facebook.com",
    "fb.com",
    "wa.me",
    "api.whatsapp.com",
    "whatsapp.com",
    "linktr.ee",
    "linktree.com",
    "bio.site",
    "beacons.ai",
    "beacons.page",
    "carrd.co",
    "taplink.cc",
    "msha.ke",
    "snipfeed.co",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "threads.net",
    "pinterest.com",
    "meusalao.com.br",
    "trinks.com",
    "avec.app",
    "agendae.com.br"
}


def _is_social_or_bio_link(url: str) -> bool:
    """Verifica se a URL é de rede social, agregador de links ou aplicativo de agendamento de terceiros."""
    if not url:
        return True
    try:
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"http://{url}")
        hostname = (parsed.hostname or "").lower()
        # Remove prefixo 'www.'
        if hostname.startswith("www."):
            hostname = hostname[4:]
        
        for domain in SOCIAL_AND_BIO_DOMAINS:
            if hostname == domain or hostname.endswith(f".{domain}"):
                return True
        return False
    except Exception:
        return False


def format_whatsapp_number(raw_phone: str) -> str:
    """Limpa e formata o telefone para o padrão WhatsApp internacional E.164 (55DD9XXXXXXXX)."""
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        return ""
    
    # Se já tem o DDI 55
    if digits.startswith("55") and len(digits) in (12, 13):
        return digits
    
    # Se é número do Brasil com DDD (10 ou 11 dígitos)
    if len(digits) in (10, 11):
        return f"55{digits}"
    
    # Caso seja só 8 ou 9 dígitos sem DDD (incompleto)
    return digits


def get_whatsapp_link(raw_phone: str) -> str:
    """Retorna o link https://wa.me/55... formatado."""
    num = format_whatsapp_number(raw_phone)
    if num:
        return f"https://wa.me/{num}"
    return ""


async def auditar_url(url: str | None) -> dict:
    """
    Analisa a presença e qualidade do website e classifica o Lead:
    - 'Tipo A (Sem Site)': Sem URL, ou aponta para redes sociais / linktr.ee / WhatsApp
    - 'Tipo B (Site Obsoleto)': Possui domínio próprio com falhas (erro HTTP, ausência de <title> ou <h1>,
      falta de viewport mobile, layout estático desatualizado).
    """
    clean_url = (url or "").strip()

    # 1. Checagem inicial: Vazio ou Rede Social
    if not clean_url or _is_social_or_bio_link(clean_url):
        motivo = "Sem website próprio cadastrado" if not clean_url else "Utiliza apenas rede social / agregador de links"
        return {
            "classificacao": "Tipo A (Sem Site)",
            "motivo": motivo,
            "status_code": None,
            "has_title": False,
            "has_h1": False,
            "is_responsive": False,
            "url_auditada": clean_url
        }

    # Garante esquema http/https
    test_url = clean_url if clean_url.startswith(("http://", "https://")) else f"https://{clean_url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
            response = await client.get(test_url, headers=headers)

            if response.status_code >= 400:
                return {
                    "classificacao": "Tipo B (Site Obsoleto)",
                    "motivo": f"Site com erro HTTP {response.status_code}",
                    "status_code": response.status_code,
                    "has_title": False,
                    "has_h1": False,
                    "is_responsive": False,
                    "url_auditada": test_url
                }

            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # Avaliação de elementos de SEO e estrutura
            title_tag = soup.find("title")
            title_text = title_tag.get_text(strip=True) if title_tag else ""
            has_title = bool(title_text and len(title_text) > 3)

            h1_tag = soup.find("h1")
            h1_text = h1_tag.get_text(strip=True) if h1_tag else ""
            has_h1 = bool(h1_text and len(h1_text) > 3)

            viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
            is_responsive = viewport_tag is not None

            # Detecta sinais de obsolescência técnica
            falhas = []
            if not has_title:
                falhas.append("ausência de tag <title> de SEO")
            if not has_h1:
                falhas.append("ausência de cabeçalho principal <h1>")
            if not is_responsive:
                falhas.append("não responsivo para celulares (sem meta viewport)")

            # Se houver qualquer falha clássica de SEO/estrutura ou site com problemas
            if falhas:
                motivo = "Site desatualizado: " + ", ".join(falhas)
            else:
                # Mesmo com title e h1, enquadrado como Tipo B para proposta de modernização visual/conversão
                motivo = "Site existente com potencial de modernização para padrão de luxo e conversão"

            return {
                "classificacao": "Tipo B (Site Obsoleto)",
                "motivo": motivo,
                "status_code": response.status_code,
                "has_title": has_title,
                "has_h1": has_h1,
                "is_responsive": is_responsive,
                "url_auditada": test_url
            }

    except httpx.ConnectTimeout:
        return {
            "classificacao": "Tipo B (Site Obsoleto)",
            "motivo": "Site inacessível (Timeout de conexão)",
            "status_code": 0,
            "has_title": False,
            "has_h1": False,
            "is_responsive": False,
            "url_auditada": test_url
        }
    except Exception as e:
        return {
            "classificacao": "Tipo B (Site Obsoleto)",
            "motivo": f"Falha ao conectar ao site: {str(e)[:80]}",
            "status_code": 0,
            "has_title": False,
            "has_h1": False,
            "is_responsive": False,
            "url_auditada": test_url
        }
