import json
import os
import re
import requests
from .config import load_config
from .logger import logger
from .database import obter_perfil_aluno, salvar_perfil_aluno, registrar_progresso_aula
from .docs_service import ler_pdf, listar_documentos

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TEACHER_SYSTEM_PROMPT = """Você é o **Professor Alex**, um mentor e professor de Inglês extremamente empático, bem-humorado, humano e especialista em impulsionar carreiras de Profissionais Brasileiros de Tecnologia (TI, RPA, Engenharia de Software, Produto e Negócios).

PERSONALIDADE & ATITUDE HUMANA:
1. Tom de Mentoria Calorosa: Você fala como um colega sênior de TI e mentor de carreira que se importa de verdade com o aluno. Use saudações humanas reais (ex: "Show de bola!", "Fala dev!", "Mandou bem demais!", "Essa é clássica em reuniões com gringo!").
2. Storytelling Prático de Escritório: Sempre contextualize o vocabulário com situações reais do dia a dia (Daily standups, alinhamento com POs, pull requests, prazos, e-mails ou reuniões internacionais).
3. Micro-doses Faladas (Máximo 2 a 3 frases por áudio): Nunca faça o aluno ler um bloco gigante de texto. Explique um conceito por vez de forma leve, fluida e falada ("fala_audio_pt").
4. TRADUÇÃO EM PORTUGUÊS OBRIGATÓRIA: SEMPRE que apresentar qualquer palavra, expressão ou frase em inglês ("termo_en"), você DEVE obrigatoriamente ensinar a sua TRADUÇÃO direta e contextualizada em Português do Brasil no campo ("traducao_pt") e também destacá-la no texto da explicação ("texto_chat"). Afinal, o aluno precisa entender perfeitamente o significado em português!
5. Ponte de Pronúncia Abrasileirada & Dica Física da Língua/Boca: 
   - Apresente o termo em inglês, a tradução em português e SEMPRE ensine o "jeitão brasileiro" de pronunciar ("pronuncia_abrasileirada") em sílabas fonéticas maiúsculas (ex: 'Schedule' -> "SKÉ-djiul", 'Framework' -> "FRÉIM-uôrk", 'Deadline' -> "DÉD-láin").
   - OBRIGATÓRIO: Forneça uma **Dica Prática da Língua/Boca & Macete Mental** ("dica_articulacao") ensinando a posição exata da boca/língua ou um macete mental de associação para facilitar a fala (ex: "👅 Dica da Língua: Posicione a ponta da língua no céu da boca sem encostar, tipo o R caipira...", "👅 Macete: Lembra de falar 'esquece', para no 'ESKÉ' e emenda com 'djiul'...").
6. Feedback Empático e Construtivo: Se o aluno errar ou se enrolar ao falar no microfone, NUNCA seja frio ou puramente corretivo. Acolha com carinho.
7. Checagem de Ritmo: Faça perguntas de checagem humana ("Faz sentido?", "Conseguiu pegar a sacada?", "Quer tentar de novo?") antes de liberar a resposta.

FORMATO DE RESPOSTA (OBRIGATÓRIO):
REGRA CRÍTICA: Comece sua resposta IMEDIATAMENTE com o caractere '{'. NUNCA escreva raciocínio prévio, pensamentos, "We need to output", "We have student's response" ou textos de planejamento em inglês antes ou depois do JSON.

Retorne APENAS um objeto JSON válido (sem marcação de bloco ```json) com a seguinte estrutura:
{
  "fala_audio_pt": "Explicação falada curta, humana, empática e encorajadora em português (2 a 3 frases no máximo, mencionando a tradução em português e a dica da boca).",
  "termo_en": "Palavra ou expressão em inglês foco da lição (ex: What do you do?).",
  "traducao_pt": "Tradução direta e contextualizada em português (ex: O que você faz? / Qual é sua profissão?).",
  "pronuncia_abrasileirada": "Pronúncia fonética abrasileirada em maiúsculas (ex: WÓT du iu DÚ).",
  "dica_articulacao": "Macete físico da língua/boca ou associação mental simples para lembrar na hora de falar.",
  "texto_chat": "Texto bem formatado em Markdown com emojis, destacando o Termo em Inglês, a TRADUÇÃO EM PORTUGUÊS (ex: 🇧🇷 Tradução: O que você faz?), a dica da língua/boca e dicas de escritório.",
  "modo_resposta": "voz",
  "instrucao_aluno": "Instrução calorosa para a vez do aluno (ex: 'Pressione o microfone e diga em voz alta: ...')"
}
"""

def extrair_json_resposta(content: str) -> dict:
    """Extrai e purifica dados JSON de respostas de IA, eliminando pensamentos/raciocínio interno do modelo."""
    if not content:
        return {}

    # 1. Elimina blocos de raciocínio/pensamento interno <think>...</think>
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # 2. Se houver texto de planejamento interno prévio (ex: "We need to output JSON..."), remove tudo até o primeiro '{'
    idx_inicio = content.find('{')
    if idx_inicio != -1:
        content_json = content[idx_inicio:]
    else:
        content_json = content

    # 3. Tenta carregar JSON puro
    try:
        dados = json.loads(content_json)
        if "traducao" in dados and "traducao_pt" not in dados:
            dados["traducao_pt"] = dados["traducao"]
        return dados
    except Exception:
        pass

    # 4. Tenta até o último '}'
    idx_fim = content_json.rfind('}')
    if idx_fim != -1:
        try:
            dados = json.loads(content_json[:idx_fim+1])
            if "traducao" in dados and "traducao_pt" not in dados:
                dados["traducao_pt"] = dados["traducao"]
            return dados
        except Exception:
            pass

    # 5. Se o JSON foi cortado/truncado no meio, extrai os campos individualmente via REGEX
    dados_extraidos = {}
    for campo in ["fala_audio_pt", "termo_en", "traducao_pt", "traducao", "pronuncia_abrasileirada", "dica_articulacao", "texto_chat", "modo_resposta", "instrucao_aluno"]:
        m = re.search(rf'\"{campo}\"\s*:\s*\"((?:[^\"]|\\\")*)\"', content_json)
        if m:
            dados_extraidos[campo] = m.group(1).replace("\\n", "\n").replace('\\"', '"')
    
    if "traducao" in dados_extraidos and "traducao_pt" not in dados_extraidos:
        dados_extraidos["traducao_pt"] = dados_extraidos["traducao"]
            
    return dados_extraidos

def sanitizar_texto_chat(texto: str) -> str:
    """Garante que o texto exibido no chat seja 100% humano, orgânico e limpo, sem chaves JSON ou raciocínio de IA."""
    if not texto:
        return ""

    # Se o texto contiver o monólogo de pensamento interno do modelo
    if "We need to output" in texto or "student's response" in texto or "Let's choose" in texto:
        idx_json = texto.find('{')
        if idx_json != -1:
            texto = texto[idx_json:]
        else:
            return "Vamos continuar nossa aula! Como você gostaria de prosseguir?"

    # Se o texto recebido for o payload JSON bruto vazado
    if texto.strip().startswith('{') and ('"texto_chat"' in texto or '"fala_audio_pt"' in texto):
        try:
            m_chat = re.search(r'\"texto_chat\"\s*:\s*\"((?:[^\"]|\\\")*)\"', texto)
            if m_chat:
                texto = m_chat.group(1).replace("\\n", "\n").replace('\\"', '"')
            else:
                m_fala = re.search(r'\"fala_audio_pt\"\s*:\s*\"((?:[^\"]|\\\")*)\"', texto)
                if m_fala:
                    texto = m_fala.group(1).replace("\\n", "\n").replace('\\"', '"')
        except Exception:
            pass

    # Remove chaves de sistema residuais caso tenham vazado no meio do texto
    texto = re.sub(r'\"?(?:fala_audio_pt|texto_chat|termo_en|pronuncia_abrasileirada|instrucao_aluno|modo_resposta)\"?\s*:\s*\"?', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'^\s*\{\s*', '', texto)
    texto = re.sub(r'\s*\}\s*$', '', texto)
    return texto.strip()

class TeacherService:
    def __init__(self):
        self.historico_chat = []
        self.conteudo_pdf_contexto = ""
        self.topico_atual = "Boas-Vindas e Apresentação"
        self._carregar_materiais_estudo()

    def _carregar_materiais_estudo(self):
        """Carrega e resume os conteúdos dos PDFs disponíveis para servir de guia pedagógico."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mapa_path = os.path.join(base_dir, "docs", "Mapa_de_Estudos_Ingles.pdf")
        if os.path.exists(mapa_path):
            res = ler_pdf(mapa_path)
            if res.get("sucesso"):
                self.conteudo_pdf_contexto = res.get("texto_completo", "")[:4000]
        else:
            docs = listar_documentos()
            if docs:
                res = ler_pdf(docs[0]["filepath"])
                if res.get("sucesso"):
                    self.conteudo_pdf_contexto = res.get("texto_completo", "")[:4000]

    @staticmethod
    def iniciar_aula() -> dict:
        """Verifica se há um perfil de aluno cadastrado. Se não houver, inicia o onboarding de boas-vindas."""
        perfil = obter_perfil_aluno()

        if not perfil:
            return {
                "fala_audio_pt": "Fala dev! Que prazer ter você por aqui! Eu sou o Professor Alex, seu mentor de inglês para a área de tecnologia. Para começarmos nossa parceria, como eu posso te chamar?",
                "termo_en": "Welcome aboard!",
                "traducao_pt": "Bem-vindo a bordo!",
                "pronuncia_abrasileirada": "UÉL-kâm a-BÔRD",
                "texto_chat": "### 🎓 Fala Dev! Bem-vindo à sua Mentoria de Inglês!\n\nEu sou o **Professor Alex**, seu mentor digital focado em destravar seu inglês para reuniões, e-mails e oportunidades internacionais.\n\nAntes de abrirmos nosso **Mapa de Estudos em PDF**, me conta: **como eu posso te chamar?**",
                "modo_resposta": "texto",
                "instrucao_aluno": "Digite ou fale seu nome abaixo para salvar seu perfil de aluno.",
                "onboarding": True
            }

        nome = perfil["nome"]
        return {
            "fala_audio_pt": f"Fala {nome}! Que bom te ver de volta! Tô com seu Mapa de Estudos aberto aqui. Bora continuar nossa aula de onde paramos?",
            "termo_en": f"Let's crush it today, {nome}!",
            "traducao_pt": f"Vamos arrebentar hoje, {nome}!",
            "pronuncia_abrasileirada": "LÉTS CRÂCH ÍT tu-DÉI",
            "texto_chat": f"### 🎓 Fala, {nome}! Tudo certo por aí?\n\nQue bom ter você de volta! Tô com o seu **Mapa de Estudos em PDF** aberto aqui no ponto.\n\nBora pra mais uma sessão? Me diga se quer continuar o fluxo ou escolher um tema!",
            "modo_resposta": "voz",
            "instrucao_aluno": "Clique no microfone e fale: 'Bora começar' ou peça um tópico (ex: 'Quero praticar reuniões').",
            "onboarding": False
        }


    def processar_interacao(self, mensagem_aluno: str) -> dict:
        """Recebe a mensagem/fala do aluno, consulta a IA no OpenRouter e retorna a resposta pedagógica em JSON."""
        config = load_config()
        api_key = config.get("api_key", "").strip()

        perfil = obter_perfil_aluno()
        
        # Fluxo de Onboarding (Definição de Nome)
        if not perfil:
            nome_aluno = mensagem_aluno.strip().replace("Meu nome é", "").replace("Me chamo", "").strip()
            if nome_aluno:
                salvar_perfil_aluno(nome_aluno, "Módulo 1: Fundamentos de Inglês para TI")
                return {
                    "fala_audio_pt": f"Prazer em te conhecer, {nome_aluno}! Já salvei seu perfil. Agora vamos iniciar nossa primeira lição do Mapa de Estudos de Inglês!",
                    "termo_en": f"Nice to meet you, {nome_aluno}!",
                    "pronuncia_abrasileirada": "NAIS tu MÍT iu",
                    "texto_chat": f"### 🌟 Perfil criado com sucesso!\n\nPrazer em te conhecer, **{nome_aluno}**! 👋\n\nAgora vou analisar seu **Mapa de Estudos em PDF** e guiar você passo a passo por voz.",
                    "modo_resposta": "voz",
                    "instrucao_aluno": "Fale no microfone ou digite 'Começar lição 1' para iniciar!",
                    "onboarding": False
                }

        if not api_key:
            return {
                "fala_audio_pt": "Atenção: A sua chave de API do OpenRouter não está configurada.",
                "termo_en": "",
                "pronuncia_abrasileirada": "",
                "texto_chat": "❌ **Erro de Configuração:** Chave de API do OpenRouter não configurada. Por favor, vá na aba **⚙️ Configurações** e insira sua chave.",
                "modo_resposta": "texto",
                "instrucao_aluno": "Cadastre sua API Key na aba Configurações.",
                "onboarding": False
            }

        nome = perfil.get("nome", "Aluno") if perfil else "Aluno"
        nivel = perfil.get("nivel", "Básico") if perfil else "Básico"

        prompt_usuario = f"""
NOME DO ALUNO: {nome}
NÍVEL DE PROFICIÊNCIA DO ALUNO: {nivel}
TÓPICO ATUAL: {self.topico_atual}
MATERIAL DE REFERÊNCIA DOS PDFS:
{self.conteudo_pdf_contexto[:1500]}

RESPOSTA / FALA DO ALUNO:
"{mensagem_aluno}"

Como Professor Alex, adapte a complexidade do vocabulário e dos desafios ao NÍVEL DE PROFICIÊNCIA DO ALUNO ({nivel}):
- 🌱 Básico: Explicações acolhedoras em português, frases curtas, termos chave de TI, pronúncia fonética detalhada.
- 🌿 Intermediário: Mistura equilibrada de inglês e português, frases completas corporativas, refinamento de ritmo e articulação.
- 🚀 Avançado: Inglês fluente corporativo (expressões, phrasal verbs de reunião), feedback fino de pronúncia e desafios complexos.

Elabore a próxima micro-lição curta com explicação falada em português, pronúncia abrasileirada e desafio.
"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/language-buddy-app",
            "X-Title": "Language Buddy Teacher"
        }

        modelos_para_testar = [config.get("model")] + [m for m in config.get("fallback_models", []) if m != config.get("model")]
        ultimo_erro = ""

        messages = [
            {"role": "system", "content": TEACHER_SYSTEM_PROMPT}
        ] + self.historico_chat[-6:] + [
            {"role": "user", "content": prompt_usuario}
        ]

        for model in modelos_para_testar:
            if not model:
                continue
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1200
                }
                response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=25)
                if response.status_code == 200:
                    res_data = response.json()
                    content = res_data["choices"][0]["message"]["content"].strip()

                    parsed = extrair_json_resposta(content)
                    if not parsed:
                        parsed = {
                            "fala_audio_pt": "Vamos continuar nossa aula!",
                            "termo_en": "",
                            "pronuncia_abrasileirada": "",
                            "texto_chat": "Vamos continuar nossa lição! Como você gostaria de prosseguir?",
                            "modo_resposta": "voz",
                            "instrucao_aluno": "Fale no microfone ou digite como prefere prosseguir."
                        }

                    texto_chat_limpo = sanitizar_texto_chat(parsed.get("texto_chat", ""))
                    fala_audio_limpa = sanitizar_texto_chat(parsed.get("fala_audio_pt", ""))

                    if not texto_chat_limpo:
                        texto_chat_limpo = fala_audio_limpa

                    self.historico_chat.append({"role": "user", "content": mensagem_aluno})
                    self.historico_chat.append({"role": "assistant", "content": texto_chat_limpo})

                    registrar_progresso_aula(self.topico_atual, "em_andamento")

                    return {
                        "fala_audio_pt": fala_audio_limpa,
                        "termo_en": parsed.get("termo_en", ""),
                        "traducao_pt": parsed.get("traducao_pt", parsed.get("traducao", "")),
                        "pronuncia_abrasileirada": parsed.get("pronuncia_abrasileirada", ""),
                        "texto_chat": texto_chat_limpo,
                        "modo_resposta": parsed.get("modo_resposta", "voz"),
                        "instrucao_aluno": parsed.get("instrucao_aluno", ""),
                        "onboarding": False
                    }
                elif response.status_code == 401:
                    return {
                        "fala_audio_pt": "A sua chave de API do OpenRouter é inválida.",
                        "termo_en": "",
                        "pronuncia_abrasileirada": "",
                        "texto_chat": "❌ **Chave de API Inválida (401)**: Verifique sua chave no openrouter.ai e atualize na aba ⚙️ Configurações.",
                        "modo_resposta": "texto",
                        "instrucao_aluno": "Atualize sua chave de API.",
                        "onboarding": False
                    }
                else:
                    ultimo_erro = f"Modelo {model} retornou HTTP {response.status_code}"
                    logger.warning(ultimo_erro)
            except Exception as e:
                ultimo_erro = str(e)
                logger.warning(f"Erro ao consultar modelo {model}: {e}")

        return {
            "fala_audio_pt": "Tive um problema ao me conectar com a inteligência artificial.",
            "termo_en": "",
            "pronuncia_abrasileirada": "",
            "texto_chat": f"⚠️ Erro ao consultar a API OpenRouter ({ultimo_erro}). Verifique sua conexão e a chave na aba ⚙️ Configurações.",
            "modo_resposta": "texto",
            "instrucao_aluno": "Tente enviar novamente sua mensagem.",
            "onboarding": False
        }

teacher_engine = TeacherService()
