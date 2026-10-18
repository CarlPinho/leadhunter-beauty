"""
Módulo de Inteligência Artificial Generativa com Google Gemini SDK (google-genai).
LeadHunter Beauty.
"""

import os
import re
import json
import logging
from typing import Optional, Any, Dict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ANTI_ALUCINACAO = (
    "Regra de Ouro Anti-Alucinação: Nunca adicione tratamentos médicos invasivos, "
    "preços específicos em Real ou dados não fornecidos pelo cliente. "
    "Trabalhe com o que foi extraído e posicione o WhatsApp como a ponte de orçamento."
)


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


def _extrair_json(texto: str) -> dict:
    """Extrai e faz parsing de um dicionário JSON retornado pelo modelo."""
    if not texto:
        return {}
    t = texto.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        match = re.search(r"\{.*\}", t, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}


class AIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._client: Optional[Any] = None
        self.system_prompt: str = SYSTEM_PROMPT_ANTI_ALUCINACAO

    @property
    def client(self) -> Any:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não foi configurada no arquivo .env")
        if not self._client:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key and "xxx" not in self.api_key)

    def gerar_copies_whatsapp(self, lead: dict, conteudo_extraido: Optional[dict] = None) -> dict:
        """
        Gera uma Central de Copies multivariada para WhatsApp com 4 ângulos persuasivos
        retornando um dicionário estruturado com:
        - curiosidade: Demonstração Pronta (Alta Curiosidade)
        - concorrencia_perda: Fuga de Clientes (Alerta de Vendas)
        - autoridade_luxo: Posicionamento & Tradição
        - follow_up: Follow-up (Retomada em 24h)
        """
        nome = lead.get("nome", "Espaço")
        palavras = (nome or "").split()
        if len(palavras) > 1 and palavras[0].lower() in ["studio", "salão", "salao", "clínica", "clinica", "espaço", "espaco", "instituto", "ateliê", "atelie", "barbearia"]:
            primeiro_nome = palavras[1]
        elif palavras:
            primeiro_nome = palavras[0]
        else:
            primeiro_nome = "pessoal"
        nicho = lead.get("nicho", "Estética e Beleza")
        bairro = lead.get("bairro", "")
        nota = lead.get("nota", "5.0")
        reviews = lead.get("qtd_reviews", "várias")
        classificacao = lead.get("classificacao", "Tipo A (Sem Site)")
        site = lead.get("website_original", "")
        conteudo = conteudo_extraido or lead.get("conteudo_extraido") or {}
        is_tipo_b = "Tipo B" in str(classificacao) or bool(site and conteudo.get("tem_conteudo"))

        diferenciais_reais = conteudo.get("diferenciais_detectados") or []
        info_diferenciais = f"- Diferenciais Reais Declarados: {'; '.join(diferenciais_reais[:3])}" if diferenciais_reais else ""

        if not is_tipo_b:
            dor_contexto = (
                "LEAD TIPO A (SEM SITE PRÓPRIO):\n"
                "- Dor central: Dependência exclusiva do Instagram/WhatsApp, falta de autoridade própria no Google e fuga de clientes que buscam no Maps com intenção imediata de agendamento."
            )
        else:
            dor_contexto = (
                f"LEAD TIPO B (SITE LEGADO/OBSOLETO: {site}):\n"
                "- Dor central: O site atual tem carregamento lento, atrito no celular e não converte visitantes em chamadas no WhatsApp, fazendo o cliente perder agendamentos para concorrentes locais."
            )

        prompt = f"""Você é um copywriter sênior e estrategista de vendas consultivas via WhatsApp para negócios locais.
{self.system_prompt}

Crie 4 abordagens distintas de prospecção via WhatsApp (Central de Copies) para o seguinte estabelecimento:
- Nome do Estabelecimento: {nome}
- Primeiro Nome / Tratamento: {primeiro_nome}
- Nicho de Atuação: {nicho}
- Localização / Bairro: {bairro if bairro else 'São Paulo - SP'}
- Avaliação Google Maps: {nota} estrelas ({reviews} avaliações)
- Classificação: {classificacao}
- Website Atual: {site if site else "Nenhum (usa apenas rede social)"}
{info_diferenciais}

DIRETRIZES DE NEGÓCIO E DOR:
{dor_contexto}

REGRAS CRUCIAIS PARA AS COPIES (SEM 'TEXTÃO', MÁXIMA CONVERSÃO):
1. Cada mensagem principal DEVE ser curta, humana e direta (máximo de 3 a 4 linhas no WhatsApp).
2. Sem formalismos antiquados (evite 'Prezados', 'Venho por meio deste', 'Espero que este e-mail/mensagem o encontre bem').
3. Regra Anti-Alucinação: NUNCA invente preços em R$ ou tratamentos médicos que não foram informados.
4. Use o nome do estabelecimento (ou primeiro nome) e o bairro real ({bairro if bairro else 'São Paulo'}).
5. As 3 primeiras mensagens (curiosidade, concorrencia_perda, autoridade_luxo) DEVEM finalizar com a chamada para ação de permissão e baixo atrito:
   "Posso te mandar o link de 1 min aqui?"
6. A 4ª mensagem (follow_up) deve ser um lembrete rápido, educado e simpático de 1 a 2 linhas para 24h após o primeiro contato sem resposta.

ESTRUTURA DAS 4 VARIAÇÕES:
- "curiosidade": Quebra de padrão rápida + elogio genuíno à reputação no Maps + gancho de que você desenhou um protótipo exclusivo para o espaço deles.
- "concorrencia_perda": Alerta consultivo mostrando que clientes do bairro buscam no Google todos os dias e acabam agendando em outros salões pela falta de agendamento ágil no WhatsApp.
- "autoridade_luxo": Valorização da autoridade e do padrão de atendimento deles, apontando que o posicionamento digital atual precisa estar à altura da reputação do espaço.
- "follow_up": Mensagem leve para 24h depois caso não respondam ("Opa {primeiro_nome}, tudo bem? Imagino a correria aí...").

FORMATO OBRIGATÓRIO DE RETORNO:
Retorne EXCLUSIVAMENTE um objeto JSON válido (sem texto ou markdown fences fora dele) no formato exato:
{{
  "curiosidade": {{
    "titulo": "🔥 Demonstração Pronta (Alta Curiosidade)",
    "mensagem": "..."
  }},
  "concorrencia_perda": {{
    "titulo": "📉 Fuga de Clientes (Alerta de Vendas)",
    "mensagem": "..."
  }},
  "autoridade_luxo": {{
    "titulo": "💎 Posicionamento & Tradição",
    "mensagem": "..."
  }},
  "follow_up": {{
    "titulo": "⏳ Follow-up (Retomada)",
    "mensagem": "..."
  }}
}}"""

        if not self.is_configured():
            return self._gerar_copies_fallback(lead, conteudo_extraido)

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
                        parsed = _extrair_json(response.text)
                        if (
                            isinstance(parsed, dict)
                            and "curiosidade" in parsed
                            and "concorrencia_perda" in parsed
                            and "autoridade_luxo" in parsed
                            and "follow_up" in parsed
                        ):
                            valido = True
                            for k in ["curiosidade", "concorrencia_perda", "autoridade_luxo", "follow_up"]:
                                if not isinstance(parsed[k], dict) or not parsed[k].get("mensagem"):
                                    valido = False
                                    break
                            if valido:
                                return parsed
                except Exception as ex:
                    last_error = ex
                    continue
            logger.warning(f"Fallback acionado para Central de Copies: {last_error}")
            return self._gerar_copies_fallback(lead, conteudo_extraido)
        except Exception as e:
            logger.error(f"Erro ao gerar Central de Copies com Gemini: {e}")
            return self._gerar_copies_fallback(lead, conteudo_extraido)

    def gerar_copy_whatsapp(self, lead: dict) -> str:
        """Retorna a copy principal com follow-up para manter compatibilidade com chamadas de texto único."""
        copies = self.gerar_copies_whatsapp(lead)
        msg_principal = copies.get("curiosidade", {}).get("mensagem", "")
        follow_up = copies.get("follow_up", {}).get("mensagem", "")
        if follow_up:
            return f"{msg_principal}\n\n---\n⏰ *Follow-up (24h se não responder):*\n{follow_up}"
        return msg_principal

    def gerar_pitch(self, lead: dict) -> str:
        """Alias para manter compatibilidade com rotas de API existentes."""
        return self.gerar_copy_whatsapp(lead)


    def gerar_prompt_ai_studio(self, lead: dict, conteudo_extraido: Optional[dict] = None) -> str:
        """
        Gera um Super Prompt hiperpersonalizado pronto em formato Markdown para o usuário
        colar diretamente no Google AI Studio (Build with Gemini) e obter uma Landing Page de alta conversão,
        respeitando estrita fidelidade aos dados reais e proibindo preços/valores fictícios.
        """
        nome = lead.get("nome", "Espaço de Atendimento")
        nicho = lead.get("nicho", "Estética e Beleza")
        bairro = lead.get("bairro") or "São Paulo"
        endereco = lead.get("endereco") or ""
        nota = lead.get("nota") or "5.0"
        reviews = lead.get("qtd_reviews") or "diversas"
        classificacao = lead.get("classificacao", "Tipo A (Sem Site)")
        tel_limpo = re.sub(r"\D", "", lead.get("telefone") or "")
        whatsapp_link = lead.get("link_whatsapp") or (f"https://wa.me/55{tel_limpo}" if tel_limpo else "https://wa.me/5511999999999")
        website = lead.get("website_original", "")

        conteudo = conteudo_extraido or lead.get("conteudo_extraido") or {}
        is_tipo_b = "Tipo B" in str(classificacao) or bool(website and conteudo.get("tem_conteudo"))

        # Checagem rigorosa de preços nos dados extraídos e no site
        textos_totais = " ".join([
            str(conteudo.get("titulo") or ""),
            " ".join(conteudo.get("cabecalhos") or []),
            " ".join(conteudo.get("resumo_apresentacao") or []),
            " ".join(conteudo.get("servicos_detectados") or []),
            " ".join(conteudo.get("diferenciais_detectados") or [])
        ])
        tem_precos_reais = bool(conteudo.get("tem_precos")) or bool(re.search(r"R\$\s*\d+|\b\d+[,.]\d{2}\b", textos_totais))

        # 1. Diretriz estrita de preços: PROIBIDO inventar preços fictícios se não houver dados comprovados
        if not tem_precos_reais:
            diretriz_precos = (
                "⚠️ PROIBIDO INVENTAR PREÇOS OU VALORES FICTÍCIOS:\n"
                "O site legado NÃO informa preços (como no caso do Studio Haara Beleza e salões renomados).\n"
                "- NÃO invente valores em R$ ou tabelas de preços fictícias. Utilize botões de CTA como 'Consultar Tabela / Agendar via WhatsApp' ou 'Solicitar Orçamento Personalizado'.\n"
                "- Posicione o WhatsApp como a ponte de orçamento para todos os procedimentos."
            )
        else:
            diretriz_precos = (
                "⚠️ DIRETRIZ DE PREÇOS REAIS:\n"
                "- Utilize apenas os valores expressamente encontrados nos dados extraídos.\n"
                "- Caso algum serviço não tenha preço divulgado: NÃO invente valores em R$ ou tabelas de preços fictícias. Utilize botões de CTA como 'Consultar Tabela / Agendar via WhatsApp' ou 'Solicitar Orçamento Personalizado'."
            )

        # 2. Diretriz de fidelidade aos textos e multi-serviços
        diretriz_servicos_fidelidade = (
            "🎯 FIDELIDADE AOS TEXTOS E NÚMEROS REAIS EXTRAÍDOS:\n"
            "- Destaque os dados reais que a cliente já colocou no site legado (ex: tempo de mercado, quantidade de clientes atendidos, diferenciais de estacionamento, endereço real).\n"
            "- Onde faltar informação detalhada de serviços, instrua a interface a criar categorias genéricas e elegantes de multi-serviços (ex: Cabelo & Penteados, Estética Facial, Manicure & Pedicure) convidando o cliente a consultar os valores no WhatsApp.\n"
            "- Nunca adicione tratamentos médicos invasivos não informados pelo cliente."
        )

        # Seleção de paleta visual recomendada por nicho
        nicho_lower = (nicho or "").lower()
        if any(w in nicho_lower for w in ["cilios", "cílios", "sobrancelha", "estética", "estetica", "beleza", "salao", "salão", "manicure", "unhas", "spa", "clinica", "clínica"]):
            paleta_descricao = "Clean Luxury / Quiet Luxury (tons neutros quentes como alabastro/areia, champanhe, rosé suave, detalhes em dourado acetinado e preto carvão/marrom nobre para contraste)"
            exemplo_servicos = "Cabelo & Penteados, Estética Facial, Manicure & Pedicure, Extensão de Cílios e Sobrancelhas"
        elif any(w in nicho_lower for w in ["barbearia", "barber", "barba"]):
            paleta_descricao = "Dark Modern / Vintage Industrial de Alto Padrão (tons de preto fosco, grafite, acabamento couro e detalhes em âmbar/dourado escovado)"
            exemplo_servicos = "Corte & Barboterapia, Alinhamento de Fios, Cuidados com a Barba e Acabamento Clássico"
        elif any(w in nicho_lower for w in ["hamburguer", "burger", "pizza", "sushi", "restaurante", "doceria", "confeitaria", "cafeteria", "cafe", "café", "gastronomia"]):
            paleta_descricao = "Gastronomia Premium & Apelo Visual Imersivo (tons apetitosos contemporâneos como terracota, vermelho rubi, âmbar tostado ou minimalismo elegante com alto contraste)"
            exemplo_servicos = "Combos Especiais da Casa, Pratos Principais, Entradas Artesanais e Bebidas Selecionadas"
        else:
            paleta_descricao = "Moderna, Premium e de Alta Autoridade (tons neutros contemporâneos com acento refinado e vibrante para os botões de ação e conversão)"
            exemplo_servicos = "Serviços Principais Especializados, Consultoria Individualizada e Atendimento com Hora Marcada"

        if is_tipo_b:
            linhas_conteudo = []
            if conteudo.get("titulo"):
                linhas_conteudo.append(f"  - Título oficial detectado: \"{conteudo['titulo']}\"")
            if conteudo.get("cabecalhos"):
                linhas_conteudo.append(f"  - Cabeçalhos e slogans reais: {', '.join(conteudo['cabecalhos'][:6])}")
            if conteudo.get("resumo_apresentacao"):
                apresentacao_str = ' | '.join(conteudo['resumo_apresentacao'][:3])
                linhas_conteudo.append(f"  - Apresentação / História da marca: \"{apresentacao_str}\"")
            
            # Diferenciais reais declarados (tempo de mercado, clientes, estacionamento, etc.)
            diferenciais = conteudo.get("diferenciais_detectados") or []
            if diferenciais:
                linhas_conteudo.append(f"  - Diferenciais reais declarados pelo estabelecimento: {'; '.join(diferenciais[:3])}")
            if endereco:
                linhas_conteudo.append(f"  - Endereço físico real: {endereco}")
            
            if conteudo.get("servicos_detectados"):
                linhas_conteudo.append(f"  - Serviços e procedimentos detectados: {', '.join(conteudo['servicos_detectados'][:10])}")

            detalhes_site = "\n".join(linhas_conteudo) if linhas_conteudo else f"  - Website original: {website} (site com carregamento lento, layout desatualizado ou não responsivo)"

            secao_contexto_site = f"""3. DIAGNÓSTICO E CONTEÚDO REAL EXTRAÍDO (LEAD TIPO B - SITE LEGADO):
O cliente possui um site legado em ({website}) com os seguintes dados e diferenciais reais extraídos pelo nosso auditor:
{detalhes_site}

👉 INSTRUÇÃO DE MODERNIZAÇÃO & FIDELIDADE AOS DADOS:
O cliente possui um site legado com os dados reais acima. Modernize completamente esta estrutura:
- Destaque com fidelidade os dados reais que a cliente já colocou no site legado (ex: tempo de mercado, quantidade de clientes atendidos, diferenciais de estacionamento, endereço real).
- Reescreva os textos com copy magnética e estética moderna de alto padrão, preservando a identidade construída pela proprietária.
{diretriz_precos}
{diretriz_servicos_fidelidade}"""
        else:
            secao_contexto_site = f"""3. DIAGNÓSTICO E OPORTUNIDADE (LEAD TIPO A - SEM SITE PRÓPRIO):
O cliente ainda não tem site e depende apenas de redes sociais (Instagram/WhatsApp).
- Crie a estrutura ideal de alta conversão para o nicho de {nicho} com serviços padrão de alta demanda ({exemplo_servicos}).
{diretriz_precos}
{diretriz_servicos_fidelidade}"""

        prompt = f"""Atue como UI/UX Designer Sênior e Especialista em Front-end voltado para Alta Conversão no nicho de {nicho}.

Desenvolva o código HTML5 completo e funcional de uma Landing Page de altíssimo impacto, estética refinada e foco em conversão para o seguinte negócio:

🔒 {SYSTEM_PROMPT_ANTI_ALUCINACAO}

1. CONTEXTO DO NEGÓCIO:
- Nome do Estabelecimento: {nome}
- Nicho / Especialidade: {nicho}
- Localização: {bairro}, São Paulo - SP{f' (Endereço Real: {endereco})' if endereco else ''}
- Reputação Google Maps: {nota} estrelas com {reviews} avaliações reais
- Link WhatsApp Oficial para Agendamentos e Orçamentos: {whatsapp_link}

2. DIRETRIZES DE PREÇOS E SERVIÇOS (ANTI-ALUCINAÇÃO):
{diretriz_precos}

{diretriz_servicos_fidelidade}

{secao_contexto_site}

4. DIRETRIZES DE DESIGN DO PROMPT:
- Arquitetura: HTML5 em arquivo único semântico (começando em <!DOCTYPE html> e finalizando em </html>).
- Framework CSS: Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>).
- Tipografia: Adicione Google Fonts refinadas no <head> (ex: 'Playfair Display' ou 'Cormorant Garamond' para títulos e 'Plus Jakarta Sans' ou 'Inter' para textos de leitura).
- Paleta de Cores: {paleta_descricao}.
- Responsividade: Layout 100% Mobile-First (impecável em smartphones, tablets e desktop).
- Ícones: Utilize SVGs inline modernos e elegantes.
- Imagens: Utilize URLs diretas e funcionais do Unsplash com fotos profissionais de alta qualidade adequadas para {nicho}.

5. SEÇÕES OBRIGATÓRIAS (ESTRUTURA DE ALTA CONVERSÃO):
a) Header com botão de WhatsApp: Logotipo elegante com o nome "{nome}", navegação com rolagem suave e botão de CTA destacado para agendamento rápido via WhatsApp.
b) Hero section de alto impacto: Proposta de valor irresistível para o nicho ({nicho}), selo de prova social (⭐ {nota} estrelas com {reviews} avaliações no Google), foto expressiva do Unsplash e botão principal de conversão ("Agendar Horário / Consultar Valores").
c) Cards de serviços / cardápio:
   - Vitrine moderna destacando os procedimentos/categorias principais.
   - ⚠️ SEM PREÇOS FICTÍCIOS: Como o estabelecimento não divulgou tabela aberta, utilize botões de CTA como "Consultar Tabela / Agendar via WhatsApp" ou "Solicitar Orçamento Personalizado".
   - Botão de agendamento por serviço direcionando para {whatsapp_link}.
d) Quebra de objeções / Diferenciais Reais: Destaque os dados reais que a cliente já colocou no site legado (ex: tempo de mercado, quantidade de clientes atendidos, diferenciais de estacionamento/valet, biossegurança rigorosa e pontualidade com hora marcada em {bairro}).
e) Prova social: Avaliações com 5 estrelas e depoimentos sinceros de clientes fiéis baseados na reputação do Google Maps ({nota} estrelas).
f) FAQ: 4 a 5 perguntas frequentes respondidas de forma concisa, orientando dúvidas de valores e agendamentos diretamente para o WhatsApp.
g) Rodapé com localização: Endereço real ({endereco if endereco else f'{bairro}, São Paulo - SP'}), horário de atendimento com hora marcada e créditos.
h) Botão flutuante de WhatsApp: Fixo no canto inferior direito, com animação pulsante suave direcionando para: {whatsapp_link}.

ENTREGA ESPERADA:
Retorne EXCLUSIVAMENTE o código HTML5 completo e pronto para publicação em um único arquivo, sem explicações em texto fora do bloco de código."""

        return prompt

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

{self.system_prompt}

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
   - Menu de Procedimentos / Serviços: Cards elegantes com os principais tratamentos do nicho {nicho}, descrição sedutora e botão de agendamento rápido. NÃO invente valores em R$ ou tabelas de preços fictícias. Utilize botões de CTA como 'Consultar Tabela / Agendar via WhatsApp' ou 'Solicitar Orçamento Personalizado'.
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

    def _gerar_copies_fallback(self, lead: dict, conteudo_extraido: Optional[dict] = None) -> dict:
        """Gera as 4 variações da Central de Copies de WhatsApp como fallback de alta conversão."""
        nome = lead.get("nome", "Espaço")
        palavras = (nome or "").split()
        if len(palavras) > 1 and palavras[0].lower() in ["studio", "salão", "salao", "clínica", "clinica", "espaço", "espaco", "instituto", "ateliê", "atelie", "barbearia"]:
            primeiro_nome = palavras[1]
        elif palavras:
            primeiro_nome = palavras[0]
        else:
            primeiro_nome = "pessoal"
        nicho = lead.get("nicho", "estética")
        bairro = lead.get("bairro") or "São Paulo"
        bairro_str = f" em {bairro}" if lead.get("bairro") else " em São Paulo"
        nota = lead.get("nota", "5.0")
        reviews = lead.get("qtd_reviews", "várias")
        classificacao = lead.get("classificacao", "Tipo A (Sem Site)")
        site = lead.get("website_original", "")
        conteudo = conteudo_extraido or lead.get("conteudo_extraido") or {}
        is_tipo_b = "Tipo B" in str(classificacao) or bool(site and conteudo.get("tem_conteudo"))

        if not is_tipo_b:
            # Tipo A: Sem site próprio
            msg_curiosidade = (
                f"Oi, tudo bem? Vi o trabalho impecável de vocês no *{nome}*{bairro_str} no Google — nota {nota} com {reviews} avaliações, parabéns!\n\n"
                f"Vi que vocês têm excelentes avaliações no Google, mas ainda não têm uma página própria para receber os agendamentos direto no WhatsApp, dependendo só do Insta.\n\n"
                f"Montei uma prévia moderna de 1 minuto mostrando como ficaria o atendimento de vocês em alta conversão. Posso te mandar o link aqui?"
            )
            msg_concorrencia = (
                f"Oi, tudo bem? Estava pesquisando serviços de {nicho} em {bairro} e o *{nome}* se destaca muito pela reputação no Maps ({nota} ⭐).\n\n"
                f"Mas notei que sem uma página rápida com botão direto de Zap, muita gente que busca no Google acaba caindo em outros espaços do bairro por falta de agendamento ágil.\n\n"
                f"Desenhei uma solução simples de 1 minuto para reter esses agendamentos direto no seu WhatsApp. Posso te mandar o link aqui?"
            )
            msg_autoridade = (
                f"Oi, tudo bem? Acompanho a excelência do *{nome}*{bairro_str} e o padrão de atendimento de vocês no Google é referência ({reviews} avaliações reais).\n\n"
                f"Vocês já têm a autoridade, mas ainda falta um espaço digital oficial à altura da marca para transformar essas buscas no Maps em agendamentos qualificados no Zap.\n\n"
                f"Criei uma prévia visual exclusiva com design de alto padrão para o {nome}. Posso te mandar o link de 1 min aqui?"
            )
        else:
            # Tipo B: Site legado / lento
            msg_curiosidade = (
                f"Oi, tudo bem? Vi o trabalho impecável de vocês no *{nome}*{bairro_str} no Google — nota {nota} com {reviews} avaliações, parabéns!\n\n"
                f"Vi que vocês recebem clientes pelo Google, mas o site atual tem lentidão e atrito no celular, o que faz muita gente desistir antes de chamar no Zap.\n\n"
                f"Montei uma prévia moderna de 1 minuto mostrando como ficaria o atendimento de vocês em alta conversão. Posso te mandar o link aqui?"
            )
            msg_concorrencia = (
                f"Oi, tudo bem? Estava analisando a presença no Google do *{nome}* em {bairro} e a reputação de vocês é fantástica ({nota} ⭐).\n\n"
                f"Porém, notei que o site atual demora para carregar no celular e dificulta o agendamento rápido, fazendo potenciais clientes migrarem para outros estabelecimentos da região.\n\n"
                f"Desenhei uma versão leve e otimizada de 1 minuto focada em cliques diretos para o WhatsApp. Posso te mandar o link aqui?"
            )
            msg_autoridade = (
                f"Oi, tudo bem? Acompanho a excelência do *{nome}*{bairro_str} e o padrão do espaço de vocês é referência em {bairro}.\n\n"
                f"Para uma clínica com a história e qualidade de vocês, ter um site moderno e fluido no celular transmite muito mais sofisticação e valor percebido na hora de agendar.\n\n"
                f"Preparei uma proposta visual elegante pensada para o público exigente de {bairro}. Posso te mandar o link de 1 min aqui?"
            )

        msg_follow_up = (
            f"Opa {primeiro_nome}, tudo bem? Imagino que a rotina aí no {nome} esteja super corrida!\n\n"
            f"Conseguiu dar uma olhada na mensagem anterior sobre a prévia de 1 min para os agendamentos de vocês? Um abraço!"
        )

        return {
            "curiosidade": {
                "titulo": "🔥 Demonstração Pronta (Alta Curiosidade)",
                "mensagem": msg_curiosidade
            },
            "concorrencia_perda": {
                "titulo": "📉 Fuga de Clientes (Alerta de Vendas)",
                "mensagem": msg_concorrencia
            },
            "autoridade_luxo": {
                "titulo": "💎 Posicionamento & Tradição",
                "mensagem": msg_autoridade
            },
            "follow_up": {
                "titulo": "⏳ Follow-up (Retomada)",
                "mensagem": msg_follow_up
            }
        }

    def _gerar_pitch_fallback(self, lead: dict) -> str:
        """Script de vendas curto e conversacional para WhatsApp (fallback sem IA)."""
        copies = self._gerar_copies_fallback(lead)
        msg_principal = copies.get("curiosidade", {}).get("mensagem", "")
        follow_up = copies.get("follow_up", {}).get("mensagem", "")
        if follow_up:
            return f"{msg_principal}\n\n---\n⏰ *Follow-up (24h se não responder):*\n{follow_up}"
        return msg_principal

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
