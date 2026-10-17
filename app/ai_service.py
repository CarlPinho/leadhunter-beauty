"""
Módulo de Inteligência Artificial Generativa com Google Gemini SDK (google-genai).
LeadHunter Beauty.
"""

import os
import re
import logging
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)


def _clean_markdown_code(content: str) -> str:
    """Remove marcações de código markdown (ex: ```html ... ```) se o modelo retornar."""
    if not content:
        return ""
    text = content.strip()
    # Remove ```html ... ``` ou ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


class AIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não foi configurada no arquivo .env")
        if not self._client:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key and "xxx" not in self.api_key)

    def gerar_pitch(self, lead: dict) -> str:
        """
        Cria uma abordagem consultiva de alta conversão para WhatsApp.
        - Tipo A: Foca na perda de tráfego do Google e falta de autoridade/conversão sem site próprio.
        - Tipo B: Aponta a fuga de clientes por causa do site atual obsoleto/não responsivo.
        """
        nome = lead.get("nome", "Espaço de Beleza")
        nicho = lead.get("nicho", "Estética e Beleza")
        bairro = lead.get("bairro", "")
        nota = lead.get("nota", "5.0")
        reviews = lead.get("qtd_reviews", "várias")
        classificacao = lead.get("classificacao", "Tipo A (Sem Site)")
        site = lead.get("website_original", "")

        prompt = f"""
Você é um especialista em prospecção B2B consultiva e vendas de desenvolvimento web para o mercado de alto padrão de beleza e estética (clínicas de estética, micropigmentação, extensão de cílios, salões de beleza).

Crie uma mensagem persuasiva, elegante e consultiva para ser enviada pelo WhatsApp para a proprietária/gerente do seguinte estabelecimento:
- Nome: {nome}
- Nicho de atuação: {nicho}
- Localização/Bairro: {bairro}
- Avaliação no Google Maps: {nota} estrelas ({reviews} avaliações)
- Classificação do Lead: {classificacao}
- Link atual: {site if site else "Sem site próprio (apenas link de redes sociais ou sem link)"}

DIRETRIZES DA MENSAGEM:
1. Tom: Profissional, caloroso, elogioso e consultivo (nada de parecer spam ou vendedor desesperado).
2. Quebra de padrão: Comece elogiando a excelente reputação do espaço no Google Maps ({nota} estrelas e {reviews} avaliações).
3. Diagnóstico pontual:
   - Se for 'Tipo A (Sem Site)': Destaque sutilmente que muitas clientes que encontram o espaço no Google acabam não agendando porque falta uma página institucional rápida com fotos dos procedimentos e botão direto para o WhatsApp, perdendo clientes para concorrentes com presença digital mais estruturada.
   - Se for 'Tipo B (Site Obsoleto)': Pontue de forma construtiva e respeitosa que o site atual não valoriza o nível de sofisticação do atendimento presencial (por não ser totalmente fluido no celular ou visualmente desatualizado para o público A/B), gerando desconfiança em clientes novas.
4. Gancho irresistível: Informe que, como cortesia e demonstração de valor, você já preparou um modelo visual exclusivo (Landing Page moderna de luxo) para o {nome}.
5. Call to Action (CTA): Uma pergunta leve e de baixo atrito, convidando a ver o link da prévia rápida de 1 minuto sem nenhum compromisso.
6. Formatação: Use quebras de parágrafos curtos adequados para leitura no WhatsApp e emojis pontuais com elegância (✨, 🌸, 📲).
7. NÃO use marcadores como '[Seu Nome]' ou '[Empresa]' — termine de forma fluida para assinatura imediata.

Retorne EXCLUSIVAMENTE o texto final da mensagem para WhatsApp.
"""

        if not self.is_configured():
            return self._gerar_pitch_fallback(lead)

        try:
            # Tenta modelos recentes disponíveis no Gemini SDK
            models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            last_error = None
            for model_name in models_to_try:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as ex:
                    last_error = ex
                    continue
            raise last_error or RuntimeError("Não foi possível gerar pitch com nenhum modelo.")
        except Exception as e:
            logger.error(f"Erro ao gerar pitch com Gemini: {e}")
            return self._gerar_pitch_fallback(lead)

    def gerar_landing_page(self, lead: dict) -> str:
        """
        Cria código HTML5 semântico completo com Tailwind CSS e paleta de estética limpa/luxo.
        """
        nome = lead.get("nome", "Studio Beauty & Estética")
        nicho = lead.get("nicho", "Estética Avançada")
        bairro = lead.get("bairro", "São Paulo")
        nota = lead.get("nota", "4.9")
        reviews = lead.get("qtd_reviews", "120")
        whatsapp_link = lead.get("link_whatsapp") or "https://wa.me/5511999999999"

        prompt = f"""
Você é um Designer UI/UX e Desenvolvedor Front-end sênior especializado no mercado de beleza, estética e bem-estar de alto padrão (Luxury Beauty & Wellness).

Desenvolva o código HTML5 completo e funcional de uma Landing Page de altíssima conversão e estética refinada para o seguinte negócio:
- Nome do Espaço: {nome}
- Nicho: {nicho}
- Localização: {bairro}
- Avaliação: {nota} estrelas ({reviews} avaliações no Google)
- Link WhatsApp de Agendamento: {whatsapp_link}

ESPECIFICAÇÕES TÉCNICAS E DE DESIGN OBRIGATÓRIAS:
1. Arquitetura: Arquivo único HTML5 válido, sem dependências de compilação.
2. Framework CSS: Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>).
3. Fontes: Google Fonts elegantes no <head> (ex: 'Playfair Display' ou 'Cormorant Garamond' para títulos e 'Plus Jakarta Sans' ou 'Montserrat' para textos).
4. Paleta de Cores: Estética Clean Luxury / Quiet Luxury (tons neutros quentes como alabastro/areia, champanhe, rosé suave, detalhes em dourado acetinado e preto carvão/marrom nobre para contraste).
5. Estrutura de Seções:
   - Header fixo/sticky com logotipo tipográfico refinado, navegação e botão 'Agendar no WhatsApp'.
   - Hero Section: Headline com proposta de valor única para o nicho ({nicho}), selo visual de reputação (⭐ {nota} com +{reviews} clientes satisfeitas), foto representativa de alta qualidade (use URLs do Unsplash voltadas para estética/beleza/skincare) e CTA principal destacado.
   - Diferenciais Exclusivos: 3 a 4 pilares (Atendimento Personalizado, Produtos Importados de Alta Performance, Biossegurança e Conforto VIP).
   - Menu de Procedimentos / Serviços: Cards elegantes com os principais tratamentos do nicho {nicho}, descrição sedutora e botão de agendamento rápido.
   - Depoimentos / Prova Social: Cards sofisticados com comentários reais de clientes encantadas.
   - Localização & Espaço: Informando o bairro {bairro}, ambiente com estacionamento e horário com hora marcada.
   - Botão Flutuante do WhatsApp: No canto inferior direito, com animação pulsante suave e link direto para {whatsapp_link}.
   - Rodapé completo com direitos autorais e dados do espaço.
6. Acessibilidade e Semântica: Tags header, main, section, footer, nav, botões com aria-label e imagens com alt descritivos.
7. Retorne APENAS o código HTML puro, começando em <!DOCTYPE html> e terminando em </html>, sem explicações ou markdown fences.
"""

        if not self.is_configured():
            return self._gerar_landing_fallback(lead)

        try:
            models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            last_error = None
            for model_name in models_to_try:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text:
                        return _clean_markdown_code(response.text)
                except Exception as ex:
                    last_error = ex
                    continue
            raise last_error or RuntimeError("Não foi possível gerar Landing Page com nenhum modelo.")
        except Exception as e:
            logger.error(f"Erro ao gerar landing page com Gemini: {e}")
            return self._gerar_landing_fallback(lead)

    def _gerar_pitch_fallback(self, lead: dict) -> str:
        """Template de pitch consultivo humanizado caso a API não esteja configurada."""
        nome = lead.get("nome", "Espaço")
        nicho = lead.get("nicho", "estética e beleza")
        bairro = f" em {lead['bairro']}" if lead.get("bairro") else ""
        nota = lead.get("nota", "5.0")
        reviews = lead.get("qtd_reviews", "diversas")
        classificacao = lead.get("classificacao", "Tipo A (Sem Site)")

        if "Tipo A" in classificacao:
            return (
                f"Olá, tudo bem? ✨\n\n"
                f"Estava pesquisando os melhores espaços de {nicho}{bairro} e fiquei muito impressionado com a reputação do *{nome}* no Google — nota {nota} com mais de {reviews} avaliações positivas! Parabéns pelo trabalho impecável.\n\n"
                f"Notei, porém, que ao buscar pelo espaço, muitas clientes novas que vêm pelo Google ou Instagram não encontram um site oficial elegante para conhecer o catálogo de procedimentos e acabam em dúvida antes de chamar no WhatsApp.\n\n"
                f"Para valorizar ainda mais a autoridade do *{nome}*, montei uma demonstração rápida de uma página exclusiva de luxo pensada para converter visitantes diretamente em agendamentos no seu WhatsApp.\n\n"
                f"Posso te mandar o link da prévia de 1 minutinho por aqui para você dar uma olhada, sem nenhum compromisso? 🌸"
            )
        else:
            return (
                f"Olá, tudo bem? ✨\n\n"
                f"Passando para parabenizar pelo trabalho incrível no *{nome}*{bairro}! A nota {nota} com {reviews} avaliações no Google reflete muito o carinho que vocês têm pelas clientes.\n\n"
                f"Dando uma olhada na presença digital de vocês, vi que o site atual não está transmitindo toda a sofisticação e o padrão de luxo que o espaço de vocês oferece hoje (principalmente na navegação pelo celular, onde mais de 90% das clientes buscam).\n\n"
                f"Desenvolvi um conceito moderno e visualmente impecável de Landing Page de alta conversão, focado em atrair clientes de alto valor e facilitar o agendamento direto no seu WhatsApp.\n\n"
                f"Gostaria de ver o link da prévia rápida para conferir como ficou? Sem nenhum compromisso, apenas para compartilhar a ideia! 📲"
            )

    def _gerar_landing_fallback(self, lead: dict) -> str:
        """Gera uma Landing Page HTML5 de luxo completa com Tailwind CSS como fallback ultra-rápido e robusto."""
        nome = lead.get("nome", "Studio Belle & Estética")
        nicho = lead.get("nicho", "Beleza & Bem-Estar")
        bairro = lead.get("bairro", "Região Nobre")
        nota = lead.get("nota") or "4.9"
        reviews = lead.get("qtd_reviews") or "128"
        wa_link = lead.get("link_whatsapp") or "https://wa.me/5511999999999"

        return f"""<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{nome} | {nicho} de Alto Padrão</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        serif: ['"Cormorant Garamond"', 'serif'],
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                    }},
                    colors: {{
                        champagne: '#EADBC8',
                        gold: '#D4AF37',
                        sand: '#FAF8F5',
                        noir: '#1A1816',
                        rosewood: '#C59B8B'
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-sand text-noir font-sans antialiased selection:bg-champagne selection:text-noir">

    <!-- Top Announcement Bar -->
    <div class="bg-noir text-champagne text-xs py-2 px-4 text-center tracking-widest uppercase font-medium">
        Atendimento Exclusivo com Hora Marcada em {bairro}
    </div>

    <!-- Navigation -->
    <header class="sticky top-0 z-40 bg-sand/90 backdrop-blur-md border-b border-champagne/40">
        <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <a href="#" class="font-serif text-2xl md:text-3xl font-semibold tracking-wide text-noir">
                {nome}
            </a>
            <nav class="hidden md:flex items-center space-x-8 text-sm uppercase tracking-wider text-noir/80 font-medium">
                <a href="#procedimentos" class="hover:text-rosewood transition-colors">Procedimentos</a>
                <a href="#diferenciais" class="hover:text-rosewood transition-colors">Diferenciais</a>
                <a href="#depoimentos" class="hover:text-rosewood transition-colors">Avaliações</a>
                <a href="#contato" class="hover:text-rosewood transition-colors">Contato</a>
            </nav>
            <a href="{wa_link}" target="_blank" rel="noopener noreferrer" class="bg-noir hover:bg-noir/90 text-champagne px-5 py-2.5 rounded-full text-xs font-semibold uppercase tracking-wider transition-all duration-300 shadow-sm hover:shadow-md">
                Agendar Horário
            </a>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="relative pt-12 pb-20 md:py-28 overflow-hidden">
        <div class="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center">
            <div class="space-y-6">
                <!-- Google Social Proof Badge -->
                <div class="inline-flex items-center gap-2 bg-white/80 border border-champagne/60 px-4 py-1.5 rounded-full shadow-sm text-xs font-medium">
                    <span class="text-amber-500 font-bold">★ {nota}</span>
                    <span class="text-neutral-400">|</span>
                    <span class="text-neutral-700">Mais de {reviews} avaliações no Google</span>
                </div>
                
                <h1 class="font-serif text-4xl sm:text-5xl lg:text-6xl text-noir leading-[1.1] font-semibold">
                    Realce a sua beleza natural com a sofisticação que você merece.
                </h1>
                
                <p class="text-neutral-600 text-base md:text-lg leading-relaxed max-w-xl font-light">
                    Especialistas em <strong class="font-semibold text-noir">{nicho}</strong> em {bairro}. Procedimentos personalizados, técnicas inovadoras e um ambiente reservado para o seu bem-estar.
                </p>

                <div class="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                    <a href="{wa_link}" target="_blank" rel="noopener noreferrer" class="inline-flex justify-center items-center gap-3 bg-noir text-champagne px-8 py-4 rounded-full font-semibold text-sm tracking-wider uppercase hover:bg-neutral-800 transition shadow-lg hover:shadow-xl">
                        <span>Reservar Minha Experiência</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                    </a>
                    <a href="#procedimentos" class="inline-flex justify-center items-center text-noir/80 hover:text-noir px-6 py-4 text-sm font-medium tracking-wide">
                        Conhecer Serviços ↓
                    </a>
                </div>
            </div>

            <!-- Hero Image -->
            <div class="relative">
                <div class="aspect-[4/5] rounded-3xl overflow-hidden shadow-2xl border-4 border-white bg-neutral-200">
                    <img src="https://images.unsplash.com/photo-1560750588-73207b1ef5b8?auto=format&fit=crop&w=1000&q=80" alt="{nome} {nicho}" class="w-full h-full object-cover object-center transform hover:scale-105 transition-transform duration-700">
                </div>
                <div class="absolute -bottom-6 -left-6 bg-white/95 backdrop-blur-md p-6 rounded-2xl shadow-xl border border-champagne/40 max-w-xs hidden sm:block">
                    <p class="font-serif text-2xl font-bold text-noir">100%</p>
                    <p class="text-xs text-neutral-500 uppercase tracking-wider mt-1">Cuidado personalizado e atendimento VIP individualizado</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Diferenciais -->
    <section id="diferenciais" class="py-20 bg-white border-y border-champagne/30">
        <div class="max-w-7xl mx-auto px-6">
            <div class="text-center max-w-2xl mx-auto mb-16">
                <p class="text-rosewood uppercase text-xs tracking-widest font-bold mb-2">Por que nos escolher</p>
                <h2 class="font-serif text-3xl md:text-4xl font-semibold">O Padrão de Excelência do {nome}</h2>
            </div>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="p-8 rounded-2xl bg-sand/60 border border-champagne/40 space-y-4 hover:shadow-md transition">
                    <div class="w-12 h-12 rounded-full bg-champagne/50 flex items-center justify-center text-noir font-serif text-xl font-bold">01</div>
                    <h3 class="font-serif text-xl font-semibold">Técnicas de Vanguarda</h3>
                    <p class="text-neutral-600 text-sm leading-relaxed">Procedimentos modernos focados na harmonia e preservação da sua saúde e beleza natural.</p>
                </div>
                <div class="p-8 rounded-2xl bg-sand/60 border border-champagne/40 space-y-4 hover:shadow-md transition">
                    <div class="w-12 h-12 rounded-full bg-champagne/50 flex items-center justify-center text-noir font-serif text-xl font-bold">02</div>
                    <h3 class="font-serif text-xl font-semibold">Produtos Premium</h3>
                    <p class="text-neutral-600 text-sm leading-relaxed">Trabalhamos exclusivamente com cosméticos e dermocosméticos certificados internacionalmente.</p>
                </div>
                <div class="p-8 rounded-2xl bg-sand/60 border border-champagne/40 space-y-4 hover:shadow-md transition">
                    <div class="w-12 h-12 rounded-full bg-champagne/50 flex items-center justify-center text-noir font-serif text-xl font-bold">03</div>
                    <h3 class="font-serif text-xl font-semibold">Biossegurança e Conforto</h3>
                    <p class="text-neutral-600 text-sm leading-relaxed">Protocolos rigorosos de esterilização em um espaço calmo, climatizado e pensado para relaxar.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Procedimentos -->
    <section id="procedimentos" class="py-20 bg-sand">
        <div class="max-w-7xl mx-auto px-6">
            <div class="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
                <div>
                    <p class="text-rosewood uppercase text-xs tracking-widest font-bold mb-2">Menu Exclusivo</p>
                    <h2 class="font-serif text-3xl md:text-5xl font-semibold">Nossos Principais Procedimentos</h2>
                </div>
                <a href="{wa_link}" target="_blank" class="text-xs uppercase tracking-widest font-semibold text-noir hover:text-rosewood border-b border-noir pb-1 inline-block">
                    Consultar Tabela Completa →
                </a>
            </div>

            <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
                <!-- Card 1 -->
                <div class="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 border border-champagne/40 flex flex-col">
                    <div class="h-60 overflow-hidden bg-neutral-100">
                        <img src="https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=700&q=80" alt="Procedimento 1" class="w-full h-full object-cover hover:scale-105 transition duration-500">
                    </div>
                    <div class="p-6 flex-1 flex flex-col justify-between space-y-4">
                        <div>
                            <span class="text-[10px] uppercase tracking-widest font-bold text-rosewood bg-champagne/30 px-2.5 py-1 rounded">Destaque</span>
                            <h3 class="font-serif text-2xl font-semibold text-noir mt-2">Design Personalizado</h3>
                            <p class="text-neutral-600 text-sm mt-2 leading-relaxed">Mapeamento anatômico para valorizar os traços únicos do seu rosto com simetria e naturalidade.</p>
                        </div>
                        <a href="{wa_link}" target="_blank" class="w-full text-center py-2.5 px-4 rounded-xl border border-noir text-xs font-semibold uppercase tracking-wider hover:bg-noir hover:text-champagne transition">
                            Agendar Avaliação
                        </a>
                    </div>
                </div>

                <!-- Card 2 -->
                <div class="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 border border-champagne/40 flex flex-col">
                    <div class="h-60 overflow-hidden bg-neutral-100">
                        <img src="https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=700&q=80" alt="Procedimento 2" class="w-full h-full object-cover hover:scale-105 transition duration-500">
                    </div>
                    <div class="p-6 flex-1 flex flex-col justify-between space-y-4">
                        <div>
                            <span class="text-[10px] uppercase tracking-widest font-bold text-rosewood bg-champagne/30 px-2.5 py-1 rounded">Alta Procura</span>
                            <h3 class="font-serif text-2xl font-semibold text-noir mt-2">Harmonização e Volume</h3>
                            <p class="text-neutral-600 text-sm mt-2 leading-relaxed">Aplicação de alta precisão que garante acabamento leve, sofisticado e duradouro.</p>
                        </div>
                        <a href="{wa_link}" target="_blank" class="w-full text-center py-2.5 px-4 rounded-xl border border-noir text-xs font-semibold uppercase tracking-wider hover:bg-noir hover:text-champagne transition">
                            Agendar Avaliação
                        </a>
                    </div>
                </div>

                <!-- Card 3 -->
                <div class="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 border border-champagne/40 flex flex-col">
                    <div class="h-60 overflow-hidden bg-neutral-100">
                        <img src="https://images.unsplash.com/photo-1512290900672-1f023330ff25?auto=format&fit=crop&w=700&q=80" alt="Procedimento 3" class="w-full h-full object-cover hover:scale-105 transition duration-500">
                    </div>
                    <div class="p-6 flex-1 flex flex-col justify-between space-y-4">
                        <div>
                            <span class="text-[10px] uppercase tracking-widest font-bold text-rosewood bg-champagne/30 px-2.5 py-1 rounded">Relax & Glow</span>
                            <h3 class="font-serif text-2xl font-semibold text-noir mt-2">Protocolo Nutritivo VIP</h3>
                            <p class="text-neutral-600 text-sm mt-2 leading-relaxed">Tratamento intensivo que revitaliza, nutre profundamente e devolve o viço radiante.</p>
                        </div>
                        <a href="{wa_link}" target="_blank" class="w-full text-center py-2.5 px-4 rounded-xl border border-noir text-xs font-semibold uppercase tracking-wider hover:bg-noir hover:text-champagne transition">
                            Agendar Avaliação
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Depoimentos -->
    <section id="depoimentos" class="py-20 bg-white">
        <div class="max-w-7xl mx-auto px-6">
            <div class="text-center max-w-xl mx-auto mb-16">
                <div class="text-amber-500 text-xl mb-2">★★★★★</div>
                <h2 class="font-serif text-3xl md:text-4xl font-semibold">O Que Nossas Clientes Dizem</h2>
                <p class="text-neutral-500 text-sm mt-2">Avaliações públicas verificadas no Google Maps</p>
            </div>

            <div class="grid md:grid-cols-3 gap-8">
                <div class="p-6 rounded-2xl bg-sand/40 border border-champagne/30 space-y-4">
                    <div class="text-amber-500 text-sm">★★★★★</div>
                    <p class="text-sm italic text-neutral-700 leading-relaxed">"O atendimento é impecável do início ao fim! Nunca me senti tão bem cuidada. A precisão e dedicação são impressionantes."</p>
                    <p class="text-xs font-bold text-noir uppercase tracking-wider">— Mariana S., {bairro}</p>
                </div>
                <div class="p-6 rounded-2xl bg-sand/40 border border-champagne/30 space-y-4">
                    <div class="text-amber-500 text-sm">★★★★★</div>
                    <p class="text-sm italic text-neutral-700 leading-relaxed">"Ambiente aconchegante, cheiroso e profissionalismo absoluto. Vale cada centavo! Recomendo de olhos fechados."</p>
                    <p class="text-xs font-bold text-noir uppercase tracking-wider">— Beatriz L., Cliente Frequente</p>
                </div>
                <div class="p-6 rounded-2xl bg-sand/40 border border-champagne/30 space-y-4">
                    <div class="text-amber-500 text-sm">★★★★★</div>
                    <p class="text-sm italic text-neutral-700 leading-relaxed">"Resultado natural e elegante, exatamente o que eu buscava. A durabilidade é surpreendente. Não troco por nada!"</p>
                    <p class="text-xs font-bold text-noir uppercase tracking-wider">— Camila F., {bairro}</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Call to Action Banner -->
    <section class="py-20 bg-noir text-white relative overflow-hidden">
        <div class="max-w-4xl mx-auto px-6 text-center space-y-8 relative z-10">
            <span class="text-xs uppercase tracking-widest text-champagne font-semibold">Vagas Limitadas por Semana</span>
            <h2 class="font-serif text-3xl sm:text-4xl md:text-5xl font-semibold leading-tight">
                Pronta para viver sua melhor versão com o {nome}?
            </h2>
            <p class="text-neutral-300 text-base max-w-xl mx-auto font-light">
                Agende sua consulta personalizada diretamente no WhatsApp de forma rápida e sem burocracia.
            </p>
            <div>
                <a href="{wa_link}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-3 bg-champagne text-noir hover:bg-white px-8 py-4 rounded-full font-bold text-sm tracking-widest uppercase transition-all shadow-xl">
                    <span>Falar Conosco no WhatsApp</span>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                </a>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer id="contato" class="bg-sand border-t border-champagne/40 py-12">
        <div class="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-center md:text-left">
            <div>
                <p class="font-serif text-xl font-bold text-noir">{nome}</p>
                <p class="text-xs text-neutral-500 mt-1">Especialistas em {nicho} • {bairro}</p>
            </div>
            <div class="text-xs text-neutral-400">
                &copy; Todos os direitos reservados. Demonstração criada para {nome}.
            </div>
        </div>
    </footer>

    <!-- Floating WhatsApp Button -->
    <a href="{wa_link}" target="_blank" rel="noopener noreferrer" aria-label="Fale no WhatsApp" class="fixed bottom-6 right-6 z-50 bg-[#25D366] text-white p-4 rounded-full shadow-2xl hover:scale-110 transition-transform duration-300 flex items-center justify-center group">
        <span class="absolute -top-10 right-0 bg-noir text-champagne text-[11px] font-semibold py-1 px-3 rounded-full shadow opacity-0 group-hover:opacity-100 transition whitespace-nowrap">
            Agendar no WhatsApp
        </span>
        <svg class="w-7 h-7" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12.031 6.172c-3.181 0-5.767 2.586-5.768 5.766-.001 1.298.38 2.27 1.019 3.287l-.582 2.128 2.182-.573c.978.58 1.911.928 3.145.929 3.178 0 5.767-2.587 5.768-5.766.001-3.187-2.575-5.77-5.764-5.771zm3.392 8.244c-.144.405-.837.774-1.17.824-.299.045-.677.063-1.092-.069-.252-.08-.575-.187-.988-.365-1.739-.751-2.874-2.502-2.961-2.617-.087-.116-.708-.94-.708-1.793s.448-1.273.607-1.446c.159-.173.346-.217.462-.217l.332.006c.106.005.249-.04.39.298.144.347.491 1.2.534 1.287.043.087.072.188.014.304-.058.116-.087.188-.173.289l-.26.304c-.087.086-.177.18-.076.354.101.174.449.741.964 1.201.662.591 1.221.774 1.394.86.173.086.275.072.376-.044.101-.116.433-.506.549-.68.116-.173.231-.145.39-.086.159.058 1.011.477 1.184.564.173.087.289.13.332.202.043.072.043.419-.101.824zM12 2C6.477 2 2 6.477 2 12c0 1.891.524 3.66 1.434 5.176L2 22l4.957-1.398C8.423 21.493 10.154 22 12 22c5.523 0 10-4.477 10-10S17.523 2 12 2z"/>
        </svg>
    </a>

</body>
</html>
"""
