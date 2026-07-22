import requests
import json
from .config import load_config
from .logger import logger

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Você é um assistente especialista em ensino de Inglês para Profissionais Brasileiros (especialmente áreas de TI, Negócios, RPA e Engenharia de Software).

Sua tarefa é receber uma palavra, expressão ou frase em inglês informada pelo usuário e retornar ESTREITAMENTE um objeto JSON válido (sem marcação de markdown ```json, apenas a string JSON pura).

O JSON deve conter exatamente as seguintes chaves:
- "termo_ingles": O termo ou frase corrigida/formatada em inglês.
- "traducao": A tradução direta e contextualizada em português do Brasil.
- "pronuncia_abrasileirada": A pronúncia no "jeitão brasileiro", dividida em sílabas fonéticas em maiúsculas/minúsculas para indicar a sílaba tônica (Exemplo para 'Schedule': "SKÉ-djiul", para 'Deploy': "di-PLÓI", para 'Framework': "FRÉIM-uôrk").
- "dica_articulacao": Uma dica física da posição da língua/boca ou um macete mental simples de memória (Exemplo: "👅 Posicione a ponta da língua perto do céu da boca sem encostar...").
- "exemplo_contexto": Uma frase curta em inglês aplicando o termo em um contexto de trabalho (reuniões, e-mails, desenvolvimento de software, etc.).
- "traducao_exemplo": A tradução em português da frase de exemplo.

REGRAS:
1. Responda APENAS com o JSON válido.
2. A pronúncia abrasileirada deve ser extremamente intuitiva para um falante de português do Brasil.
3. Não inclua texto explicativo antes ou depois do JSON.
"""

def consultar_openrouter(termo: str) -> dict:
    """
    Envia uma requisição para a API do OpenRouter e retorna os dados estruturados em dict.
    Trata erros e tenta modelos de fallback caso necessário.
    """
    config = load_config()
    api_key = config.get("api_key", "").strip()

    if not api_key:
        return {
            "sucesso": False,
            "erro": "Chave de API do OpenRouter não configurada. Por favor, cadastre sua chave na aba Configurações."
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/language-buddy-app",
        "X-Title": "Language Buddy App"
    }

    payload_base = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Termo/Frase: '{termo}'"}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    modelos_para_testar = [config.get("model")] + [m for m in config.get("fallback_models", []) if m != config.get("model")]

    ultimo_erro = ""

    for modelo in modelos_para_testar:
        if not modelo:
            continue
        try:
            payload = payload_base.copy()
            payload["model"] = modelo

            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=25)
            
            if response.status_code == 200:
                res_data = response.json()
                content = res_data["choices"][0]["message"]["content"].strip()

                # Limpa tags de código markdown se o modelo tiver incluído
                if content.startswith("```"):
                    content = content.replace("```json", "").replace("```", "").strip()

                parsed_json = json.loads(content)
                return {
                    "sucesso": True,
                    "modelo_usado": modelo,
                    "dados": parsed_json
                }
            elif response.status_code == 401:
                return {
                    "sucesso": False,
                    "erro": "Chave de API inválida (401 Unauthorized). Verifique sua chave no openrouter.ai."
                }
            else:
                ultimo_erro = f"Modelo {modelo} retornou HTTP {response.status_code}: {response.text}"
                logger.warning(ultimo_erro)

        except json.JSONDecodeError:
            # Caso a IA não responda em JSON válido
            ultimo_erro = "A IA respondeu em formato inválido. Tentando outro modelo..."
        except requests.exceptions.Timeout:
            ultimo_erro = f"Tempo limite excedido ao chamar {modelo}."
        except requests.exceptions.RequestException as e:
            ultimo_erro = f"Erro de conexão com OpenRouter: {e}"

    return {
        "sucesso": False,
        "erro": f"Não foi possível obter resposta da IA. {ultimo_erro}"
    }
