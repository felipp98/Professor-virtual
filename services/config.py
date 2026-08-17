import os
import json
from .logger import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

SERVICE_NAME = "LanguageBuddyApp"
KEYRING_USERNAME = "openrouter_api_key"

# Cache em memória para sessão atual caso o cofre do SO não esteja disponível
_SESSION_API_KEY = ""

DEFAULT_CONFIG = {
    "model": "meta-llama/llama-3.3-70b-instruct:free",
    "voice": "pt-BR-AntonioNeural",
    "fallback_models": [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen-2.5-72b-instruct:free"
    ],
    "pomodoro_work_minutes": 30,
    "pomodoro_break_minutes": 5
}

def obter_api_key() -> str:
    """
    Recupera a chave de API seguindo a ordem de precedência hierárquica:
    1º Variável de Ambiente (OPENROUTER_API_KEY / ANTHROPIC_AUTH_TOKEN)
    2º Cofre do SO (Windows Credential Manager via keyring)
    3º Cache em memória da sessão
    """
    global _SESSION_API_KEY
    # 1. Variável de Ambiente
    env_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if env_key:
        return env_key.strip()

    # 2. Windows Credential Manager / Keyring
    try:
        import keyring
        key = keyring.get_password(SERVICE_NAME, KEYRING_USERNAME)
        if key:
            return key.strip()
    except Exception as e:
        logger.warning(f"Não foi possível acessar o cofre de credenciais do SO: {e}")

    # 3. Fallback em memória
    return _SESSION_API_KEY

def salvar_api_key(api_key: str) -> bool:
    """Armazena a chave de API de forma segura no cofre do sistema operacional (CWE-312 / CWE-522)."""
    global _SESSION_API_KEY
    _SESSION_API_KEY = (api_key or "").strip()
    try:
        import keyring
        if _SESSION_API_KEY:
            keyring.set_password(SERVICE_NAME, KEYRING_USERNAME, _SESSION_API_KEY)
            logger.info("Chave de API salva com sucesso no cofre de credenciais do SO.")
        else:
            try:
                keyring.delete_password(SERVICE_NAME, KEYRING_USERNAME)
            except Exception:
                pass
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar chave no cofre do SO ({e}). Mantida apenas na sessão atual.")
        return False

def load_config() -> dict:
    """
    Carrega as configurações do arquivo JSON local.
    Executa migração automática caso exista api_key em texto puro no JSON legado.
    """
    config = DEFAULT_CONFIG.copy()
    precisa_purgar_json = False

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_config = json.load(f)

            # Migração com Purga: Se houver api_key no JSON legado
            if "api_key" in saved_config and saved_config["api_key"]:
                legado_key = saved_config.pop("api_key").strip()
                if legado_key:
                    logger.info("Migrando chave de API legada em texto puro para o cofre do SO...")
                    salvar_api_key(legado_key)
                precisa_purgar_json = True

            for key, val in saved_config.items():
                if val is not None and val != "":
                    config[key] = val

            if precisa_purgar_json:
                save_config(config)

        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
    else:
        save_config(config)

    # Injeta a chave de API recuperada de forma segura para compatibilidade
    config["api_key"] = obter_api_key()
    return config

def save_config(config_data: dict) -> bool:
    """
    Salva as preferências gerais no JSON local expurgando qualquer chave de API.
    A chave de API é direcionada para o cofre seguro.
    """
    try:
        dados_salvar = config_data.copy()

        # Se vier com campo api_key, salva no cofre seguro e remove do JSON
        if "api_key" in dados_salvar:
            chave = dados_salvar.pop("api_key")
            if chave is not None and chave != "":
                salvar_api_key(chave)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(dados_salvar, f, indent=4, ensure_ascii=False)
        logger.info("Configurações não-sensíveis salvas no config.json.")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configurações no JSON: {e}")
        return False
