import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "meta-llama/llama-3.3-70b-instruct:free",
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

def load_config() -> dict:
    """Carrega as configurações do arquivo JSON local ou cria com valores padrão."""
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                for key, val in saved_config.items():
                    if val:  # Substitui se houver valor salvo
                        config[key] = val
        except Exception:
            pass
    else:
        save_config(config)

    # Fallback para variáveis de ambiente se a chave não estiver no JSON
    if not config.get("api_key"):
        env_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENROUTER_API_KEY")
        if env_key:
            config["api_key"] = env_key

    return config

def save_config(config_data: dict) -> bool:
    """Salva as configurações no arquivo JSON local."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")
        return False
