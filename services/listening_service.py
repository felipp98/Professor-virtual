import json
import difflib
import requests
from typing import Dict, List, Any
from .config import load_config
from .logger import logger
from .ai_service import OPENROUTER_URL

# Lições de demonstração pré-carregadas para TI/RPA/Devs
PRESET_LESSONS: List[Dict[str, Any]] = [
    {
        "id": "daily_standup",
        "titulo": "🎙️ Daily Standup: Update & Impedimentos",
        "categoria": "Rotina Dev / Agile",
        "texto_en": "Good morning team! Yesterday I finished writing unit tests for the authentication API. Today I am going to refactor the database query to improve performance. I have no blockers right now.",
        "texto_pt": "Bom dia equipe! Ontem eu terminei de escrever os testes unitários para a API de autenticação. Hoje vou refatorar a consulta do banco de dados para melhorar a performance. Não tenho nenhum impedimento agora.",
        "frases": [
            {
                "id": 1,
                "texto_en": "Good morning team!",
                "texto_pt": "Bom dia equipe!",
                "pronuncia_abrasileirada": "GÚD MÓR-nin TÍM!",
                "dica": "Mantenha o 'g' final de 'morning' suave, sem forçar um som de 'guede'."
            },
            {
                "id": 2,
                "texto_en": "Yesterday I finished writing unit tests for the authentication API.",
                "texto_pt": "Ontem eu terminei de escrever os testes unitários para a API de autenticação.",
                "pronuncia_abrasileirada": "IÊS-ter-dei AI FÍ-nisht RUÁI-tin IÚ-nit TÉSTS fór dhi ó-then-ti-KÉI-shun EI-PI-AI.",
                "dica": "O final em '-ed' de 'finished' soa como um 'T' seco (FÍ-nisht)."
            },
            {
                "id": 3,
                "texto_en": "Today I am going to refactor the database query to improve performance.",
                "texto_pt": "Hoje vou refatorar a consulta do banco de dados para melhorar a performance.",
                "pronuncia_abrasileirada": "tu-DÉI AI ÉM GÔ-in tu ri-FÉK-tor dhi DÉI-ta-beis KWÍ-ri tu im-PRÚV per-FÓR-manss.",
                "dica": "'Query' fala-se 'KWÍ-ri' e 'Performance' com o 'R' bem aberto do interior (per-FÓR-manss)."
            },
            {
                "id": 4,
                "texto_en": "I have no blockers right now.",
                "texto_pt": "Não tenho nenhum impedimento agora.",
                "pronuncia_abrasileirada": "AI HÉV NÔ BLÓ-kers RUÁIT NÁU.",
                "dica": "'Blockers' é o termo ágil padrão para impedimentos ou gargalos."
            }
        ]
    },
    {
        "id": "code_review",
        "titulo": "💻 Code Review & Pull Request",
        "categoria": "Engenharia de Software",
        "texto_en": "I just reviewed your pull request. The overall architecture looks solid, but please add proper error handling and update the documentation before we merge it into main.",
        "texto_pt": "Acabei de revisar o seu pull request. A arquitetura geral parece sólida, mas por favor adicione tratamento de erros adequado e atualize a documentação antes de juntarmos na branch principal.",
        "frases": [
            {
                "id": 1,
                "texto_en": "I just reviewed your pull request.",
                "texto_pt": "Acabei de revisar o seu pull request.",
                "pronuncia_abrasileirada": "AI DJÂST ri-VIÚD iór PÚL ri-KWÉST.",
                "dica": "'Pull Request' pronuncia-se 'PÚL ri-KWÉST' com ênfase no 'PÚL'."
            },
            {
                "id": 2,
                "texto_en": "The overall architecture looks solid,",
                "texto_pt": "A arquitetura geral parece sólida,",
                "pronuncia_abrasileirada": "dhi ô-ver-ÓL ár-ki-TÉK-tcher LÚKS SÓ-lid,",
                "dica": "'Architecture' soa como 'ár-ki-TÉK-tcher' (com som de K no começo)."
            },
            {
                "id": 3,
                "texto_en": "but please add proper error handling",
                "texto_pt": "mas por favor adicione tratamento de erros adequado",
                "pronuncia_abrasileirada": "bât PLÍZ ÉD PRÓ-per É-ror HÉND-ling",
                "dica": "'Error handling' é o termo técnico para capturar e tratar exceções no código."
            },
            {
                "id": 4,
                "texto_en": "and update the documentation before we merge it into main.",
                "texto_pt": "e atualize a documentação antes de juntarmos na main.",
                "pronuncia_abrasileirada": "end âp-DÉIT dhi do-kiu-men-TÉI-shun bi-FÓR uí MÉRDJ it ÍN-tu MÉIN.",
                "dica": "'Merge' tem som de 'G' suave como em 'MÉRDJ'."
            }
        ]
    },
    {
        "id": "rpa_bot_demo",
        "titulo": "🤖 Demonstração de Automação RPA",
        "categoria": "Automação & Processos",
        "texto_en": "In this demo, I will show you how our bot handles invoice extraction. It automatically downloads PDFs from the server, parses line items, and inserts them directly into SAP.",
        "texto_pt": "Nesta demonstração, vou mostrar como nosso robô faz a extração de faturas. Ele baixa PDFs do servidor automaticamente, analisa os itens e os insere diretamente no SAP.",
        "frases": [
            {
                "id": 1,
                "texto_en": "In this demo, I will show you how our bot handles invoice extraction.",
                "texto_pt": "Nesta demonstração, vou mostrar como nosso robô faz a extração de faturas.",
                "pronuncia_abrasileirada": "in DHIS DÉ-mô, AI WI-ul SHÔ uÍ HÁU áu-er BÓT HÉND-uls ÍN-voiss eks-TRÉK-shun.",
                "dica": "'Invoice' pronuncia-se 'ÍN-voiss' (nota fiscal ou fatura)."
            },
            {
                "id": 2,
                "texto_en": "It automatically downloads PDFs from the server,",
                "texto_pt": "Ele baixa PDFs do servidor automaticamente,",
                "pronuncia_abrasileirada": "it ó-to-MÉ-ti-kli DAUN-lôuds pi-di-ÉFS fróm dhi SÉR-ver,",
                "dica": "'Automatically' reduz a sílaba central: 'ó-to-MÉ-ti-kli'."
            },
            {
                "id": 3,
                "texto_en": "parses line items, and inserts them directly into SAP.",
                "texto_pt": "analisa os itens e os insere diretamente no SAP.",
                "pronuncia_abrasileirada": "PÁR-sez LÁIN ÁI-tems, end in-SÉRTS dhem di-RÉK-tli ÍN-tu S-A-P.",
                "dica": "'Parses' em TI significa ler/extrair dados estruturados ('PÁR-sez')."
            }
        ]
    }
]

PROMPT_GERAR_LICAO = """Você é um professor de inglês técnico corporativo para brasileiros de TI/RPA.
Gere um texto de treino de escuta e pronúncia em inglês focado no tema solicitado pelo usuário.

Você DEVE retornar EXCLUSIVAMENTE um objeto JSON válido (sem marcação ```json, apenas a string pura).

Estrutura do JSON:
{
  "id": "slug_do_tema",
  "titulo": "Título com emoji curto em PT-BR",
  "categoria": "Área de atuação",
  "texto_en": "Texto completo em inglês (de 3 a 5 frases fluidas)",
  "texto_pt": "Tradução completa em português",
  "frases": [
    {
      "id": 1,
      "texto_en": "Primeira frase em inglês",
      "texto_pt": "Tradução da primeira frase",
      "pronuncia_abrasileirada": "PRO-nún-sia fô-NÉ-ti-ka a-bra-si-lei-RA-da",
      "dica": "Dica prática de pronúncia ou vocabulário corporativo"
    }
  ]
}

REGRAS:
1. Responda APENAS com o JSON válido.
2. A pronúncia abrasileirada deve ser hiper clara e dividida por sílabas em maiúsculas na sílaba tônica.
3. O texto deve ter vocabulário natural do ambiente corporativo global de TI/Engenharia.
"""

class ListeningService:
    """Serviço responsável por gerenciar as lições de escuta e avaliação de pronúncia."""

    def __init__(self):
        self.lessons = PRESET_LESSONS

    def listar_licoes(self) -> List[Dict[str, Any]]:
        """Retorna todas as lições disponíveis (predefinidas + geradas)."""
        return self.lessons

    def obter_licao_por_id(self, licao_id: str) -> Dict[str, Any]:
        """Busca uma lição pelo ID."""
        for l in self.lessons:
            if l["id"] == licao_id:
                return l
        return self.lessons[0]

    def gerar_licao_com_ia(self, topico: str) -> Dict[str, Any]:
        """Solicita à IA a geração de um novo treino de escuta e pronúncia focado em um tópico."""
        config = load_config()
        api_key = config.get("api_key", "").strip()

        if not api_key:
            return {
                "sucesso": False,
                "erro": "Chave do OpenRouter não configurada. Por favor, adicione sua chave nas Configurações."
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/language-buddy-app",
            "X-Title": "Language Buddy App"
        }

        payload = {
            "model": config.get("model", "meta-llama/llama-3.3-70b-instruct:free"),
            "messages": [
                {"role": "system", "content": PROMPT_GERAR_LICAO},
                {"role": "user", "content": f"Gere uma lição sobre o tópico: '{topico}'"}
            ],
            "temperature": 0.5,
            "max_tokens": 1000
        }

        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                content = res_data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.replace("```json", "").replace("```", "").strip()

                parsed_json = json.loads(content)
                parsed_json["id"] = f"custom_{len(self.lessons) + 1}"
                
                # Guarda na lista local em memória
                self.lessons.append(parsed_json)
                return {"sucesso": True, "licao": parsed_json}
            else:
                return {"sucesso": False, "erro": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Erro ao gerar lição por IA: {e}")
            return {"sucesso": False, "erro": f"Falha na requisição da IA: {e}"}

    def calcular_similaridade_pronuncia(self, texto_esperado: str, texto_falado: str) -> float:
        """Calcula percentual de similaridade (0 a 100%) entre a frase original e a fala transcrita."""
        if not texto_esperado or not texto_falado:
            return 0.0
        
        # Limpa pontuações para comparar palavras reais
        esperado_limpo = "".join(c.lower() for c in texto_esperado if c.isalnum() or c.isspace()).strip()
        falado_limpo = "".join(c.lower() for c in texto_falado if c.isalnum() or c.isspace()).strip()

        ratio = difflib.SequenceMatcher(None, esperado_limpo, falado_limpo).ratio()
        return round(ratio * 100, 1)

# Instância global do serviço de escuta
listening_service = ListeningService()
