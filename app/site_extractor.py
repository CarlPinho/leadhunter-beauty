"""
Módulo de Extração de Conteúdo de Sites para Enriquecimento de Prompts.
LeadHunter Beauty.
"""

import re
import logging
from typing import Dict, Any, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domínios e redes que não devem ser raspados como sites institucionais
SOCIAL_AND_BIO_DOMAINS = {
    "instagram.com", "instagr.am", "facebook.com", "fb.com", "wa.me",
    "api.whatsapp.com", "whatsapp.com", "linktr.ee", "linktree.com",
    "bio.site", "beacons.ai", "beacons.page", "carrd.co", "taplink.cc",
    "msha.ke", "snipfeed.co", "tiktok.com", "youtube.com", "linkedin.com",
    "twitter.com", "x.com", "threads.net", "pinterest.com", "meusalao.com.br",
    "trinks.com", "avec.app", "agendae.com.br", "agendaboa.com", "simplesagenda.com.br",
    "belasis.com.br", "gendo.com.br", "booksy.com", "bit.ly", "tinyurl.com"
}

IGNORABLE_TEXT_PATTERNS = [
    r"cookie", r"política de privacidade", r"termos de uso", r"todos os direitos",
    r"all rights reserved", r"desenvolvido por", r"powered by", r"fale conosco",
    r"clique aqui", r"leia mais", r"login", r"cadastre-se"
]


def _is_social_or_bio(url: str) -> bool:
    if not url:
        return True
    try:
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"http://{url}")
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        for domain in SOCIAL_AND_BIO_DOMAINS:
            if host == domain or host.endswith(f".{domain}"):
                return True
        return False
    except Exception:
        return True


def _clean_text(text: str) -> str:
    """Limpa quebras de linha e múltiplos espaços de um texto."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_ignorable(text: str) -> bool:
    """Detecta se o texto é apenas aviso de cookies, rodapé ou navegação genérica."""
    t = text.lower()
    for pat in IGNORABLE_TEXT_PATTERNS:
        if re.search(pat, t):
            return True
    return False


def extrair_conteudo_site(url: str) -> Dict[str, Any]:
    """
    Extrai informações estruturadas e textos reais de um website (Tipo B):
    - Título da página (<title>)
    - Cabeçalhos (<h1>, <h2>)
    - Parágrafos de destaque (resumo de serviços, bio ou apresentação da clínica/restaurante)
    - Serviços ou itens de cardápio detectados (listas <li> ou blocos de texto)
    
    Retorna {} se não houver URL, for rede social ou falhar no carregamento.
    """
    if not url or _is_social_or_bio(url):
        return {}

    url_alvo = url if url.startswith(("http://", "https://")) else f"https://{url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    html_text = ""
    # 1. Requisição com timeout seguro de 6 segundos
    try:
        import httpx
        with httpx.Client(timeout=6.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url_alvo, headers=headers)
            if resp.status_code < 400:
                html_text = resp.text
    except Exception:
        # Fallback usando urllib se httpx falhar ou não estiver disponível
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url_alvo, headers=headers)
            with urllib.request.urlopen(req, timeout=6.0, context=ctx) as r:
                html_text = r.read().decode("utf-8", errors="ignore")
        except Exception as ex:
            logger.warning(f"Falha ao requisitar site {url_alvo}: {ex}")
            return {}

    if not html_text:
        return {}

    # 2. Parsing e Extração com BeautifulSoup (ou regex como fallback)
    titulo = ""
    cabecalhos: List[str] = []
    paragrafos: List[str] = []
    servicos: List[str] = []

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        # Remove elementos irrelevantes (scripts, estilos, iframes, svgs)
        for tag in soup(["script", "style", "noscript", "iframe", "svg", "nav", "footer"]):
            tag.decompose()

        # Título
        if soup.title and soup.title.string:
            titulo = _clean_text(soup.title.string)[:120]

        # Cabeçalhos h1 e h2
        for h in soup.find_all(["h1", "h2"]):
            txt = _clean_text(h.get_text())
            if txt and len(txt) >= 4 and len(txt) <= 120 and not _is_ignorable(txt):
                if txt not in cabecalhos:
                    cabecalhos.append(txt)
            if len(cabecalhos) >= 8:
                break

        # Parágrafos de destaque (Apresentação / Sobre / Bio)
        for p in soup.find_all("p"):
            txt = _clean_text(p.get_text())
            if 35 <= len(txt) <= 350 and not _is_ignorable(txt):
                if txt not in paragrafos:
                    paragrafos.append(txt)
            if len(paragrafos) >= 4:
                break

        # Serviços ou Itens de Cardápio (listas <li> ou tags com classes de serviço)
        itens_detectados = []
        for li in soup.find_all("li"):
            txt = _clean_text(li.get_text())
            if 4 <= len(txt) <= 70 and not _is_ignorable(txt):
                # Evita itens de navegação clássicos
                if txt.lower() not in {"home", "início", "inicio", "sobre", "contato", "serviços", "servicos", "cardápio", "cardapio"}:
                    if txt not in itens_detectados:
                        itens_detectados.append(txt)
            if len(itens_detectados) >= 12:
                break

        # Se não achou em <li>, tenta <h3> ou <h4>
        if not itens_detectados:
            for h in soup.find_all(["h3", "h4"]):
                txt = _clean_text(h.get_text())
                if 4 <= len(txt) <= 70 and not _is_ignorable(txt):
                    if txt not in itens_detectados:
                        itens_detectados.append(txt)
                if len(itens_detectados) >= 8:
                    break

        servicos = itens_detectados[:10]

        # Diferenciais, números e destaques reais (tempo de mercado, clientes, estacionamento, etc.)
        diferenciais: List[str] = []
        diferenciais_keywords = [
            "ano", "anos", "desde", "cliente", "clientes", "atendimento", "atendimentos",
            "estacionamento", "valet", "manobrista", "vaga", "espaço", "equipe", "especialista",
            "profissionais", "certifica", "exclusivo", "personalizado", "endereço", "localiza"
        ]
        textos_candidatos = cabecalhos + paragrafos
        for t in textos_candidatos:
            t_low = t.lower()
            if any(kw in t_low for kw in diferenciais_keywords):
                if t not in diferenciais and len(t) <= 260:
                    diferenciais.append(t)
            if len(diferenciais) >= 4:
                break

    except ImportError:
        # Fallback básico com regex caso BeautifulSoup não esteja disponível
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        if title_match:
            titulo = _clean_text(title_match.group(1))[:120]

        h_matches = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html_text, re.IGNORECASE | re.DOTALL)
        for h in h_matches:
            limpo = _clean_text(re.sub(r"<[^>]+>", "", h))
            if 4 <= len(limpo) <= 120 and limpo not in cabecalhos and not _is_ignorable(limpo):
                cabecalhos.append(limpo)
            if len(cabecalhos) >= 6:
                break

        p_matches = re.findall(r"<p[^>]*>(.*?)</p>", html_text, re.IGNORECASE | re.DOTALL)
        for p in p_matches:
            limpo = _clean_text(re.sub(r"<[^>]+>", "", p))
            if 35 <= len(limpo) <= 300 and limpo not in paragrafos and not _is_ignorable(limpo):
                paragrafos.append(limpo)
            if len(paragrafos) >= 3:
                break

        diferenciais = []

    tem_precos = bool(re.search(r"R\$\s*\d+|\b\d+[,.]\d{2}\b", html_text))
    tem_conteudo = bool(titulo or cabecalhos or paragrafos or servicos or diferenciais)
    if not tem_conteudo:
        return {}

    return {
        "url": url_alvo,
        "titulo": titulo,
        "cabecalhos": cabecalhos,
        "resumo_apresentacao": paragrafos,
        "servicos_detectados": servicos,
        "diferenciais_detectados": diferenciais,
        "tem_precos": tem_precos,
        "tem_conteudo": True
    }
