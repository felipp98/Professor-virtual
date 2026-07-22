import os
import re
import tempfile
import threading
import time

# Oculta mensagem do Pygame e evita inicializar drivers de tela (apenas áudio)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

def sanitizar_texto_fala(texto: str) -> str:
    """Limpa marcações de sistema, chaves JSON, URLs e caracteres markdown para uma fala humana e fluida."""
    if not texto:
        return ""

    # Se o texto for uma string JSON bruta vazada
    if texto.strip().startswith('{') and 'fala_audio_pt' in texto:
        try:
            m = re.search(r'\"fala_audio_pt\"\s*:\s*\"((?:[^\"]|\\\")*)\"', texto)
            if m:
                texto = m.group(1).replace('\\"', '"')
        except Exception:
            pass

    # Remove nomes de chaves de sistema (fala_audio_pt, texto_chat, etc.)
    texto = re.sub(r'\"?(?:fala_audio_pt|texto_chat|termo_en|pronuncia_abrasileirada|instrucao_aluno|modo_resposta)\"?\s*:\s*\"?', '', texto, flags=re.IGNORECASE)

    # Remove símbolos markdown (**, *, #, >, `, _, ~) para evitar leitura de "underline", "asterisco", etc.
    texto = re.sub(r'[\*\#\>\`\_]+', '', texto)

    # Limpa aspas e chaves residuais
    texto = texto.replace('{', '').replace('}', '').replace('"', '').strip()
    return texto

# Tenta carregar edge-tts para controle de velocidade e vozes neurais realistas
HAS_EDGE_TTS = False
try:
    import edge_tts
    import asyncio
    HAS_EDGE_TTS = True
except Exception as e:
    print(f"edge-tts não inicializado: {e}")
    HAS_EDGE_TTS = False

# Helper para carregamento preguiçoso (lazy loading) do Pygame e mixer
_PYGAME_MODULE = None

def _obter_pygame():
    global _PYGAME_MODULE
    if _PYGAME_MODULE is None:
        try:
            import pygame
            _PYGAME_MODULE = pygame
        except Exception as e:
            print(f"Pygame não disponível: {e}")
            _PYGAME_MODULE = False
    return _PYGAME_MODULE if _PYGAME_MODULE is not False else None

def _garantir_mixer_init():
    pg = _obter_pygame()
    if pg is not None:
        try:
            if not pg.mixer.get_init():
                pg.mixer.init()
            return True
        except Exception as e:
            print(f"Erro ao inicializar mixer do Pygame: {e}")
            return False
    return False

# Tenta carregar gTTS para reprodução de áudio
HAS_GTTS = False
try:
    from gtts import gTTS
    HAS_GTTS = True
except Exception as e:
    print(f"gTTS não inicializado: {e}")
    HAS_GTTS = False

# Tenta carregar SpeechRecognition e PyAudio para microfone
HAS_STT = False
try:
    import speech_recognition as sr
    HAS_STT = True
except Exception as e:
    print(f"SpeechRecognition não inicializado: {e}")
    HAS_STT = False

class AudioService:

    def __init__(self):
        self._speaking_thread = None
        self._is_speaking = False
        self._stop_requested = False
        self.velocidade = 1.0  # Velocidade padrão (1.0, 1.25, 1.5)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def parar_fala(self):
        """Interrompe a reprodução de áudio atual."""
        self._stop_requested = True
        pg = _obter_pygame()
        if pg and pg.mixer.get_init():
            try:
                pg.mixer.music.stop()
            except Exception:
                pass
        self._is_speaking = False

    def falar(self, texto_pt: str, termo_en: str = "", pronuncia_abrasileirada: str = "", velocidade: float = None, callback_fim=None):
        """
        Executa a síntese de fala em uma Thread paralela para não congelar a interface.
        Fala primeiro a explicação em PT, depois o termo em EN nativo, e opcionalmente a pronúncia abrasileirada.
        Suporta aceleração (1.0x, 1.25x, 1.5x).
        """
        if velocidade is None:
            velocidade = self.velocidade

        self.parar_fala()
        self._stop_requested = False
        self._speaking_thread = threading.Thread(
            target=self._executar_fala_thread,
            args=(texto_pt, termo_en, pronuncia_abrasileirada, velocidade, callback_fim),
            daemon=True
        )
        self._speaking_thread.start()

    def _executar_fala_thread(self, texto_pt: str, termo_en: str, pronuncia_abrasileirada: str, velocidade: float, callback_fim):
        self._is_speaking = True
        temp_files = []

        try:
            if not HAS_GTTS:
                print("Recurso de áudio não disponível (pygame ausente).")
                self._is_speaking = False
                if callback_fim:
                    callback_fim()
                return

            # Combina a explicação, o termo em inglês e a pronúncia em um único texto contínuo
            texto_pt_limpo = sanitizar_texto_fala(texto_pt)
            partes_fala = []
            if texto_pt_limpo and texto_pt_limpo.strip():
                partes_fala.append(texto_pt_limpo.strip())
            if termo_en and termo_en.strip():
                partes_fala.append(f"Em inglês: {termo_en.strip()}")
            if pronuncia_abrasileirada and pronuncia_abrasileirada.strip():
                pron_limpa = sanitizar_texto_fala(pronuncia_abrasileirada)
                partes_fala.append(f"Pronúncia fonética: {pron_limpa.strip()}")

            texto_completo = ". ".join(partes_fala).strip()
            if not texto_completo:
                self._is_speaking = False
                if callback_fim:
                    callback_fim()
                return

            rate_percent = int((velocidade - 1.0) * 100)
            rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            temp_files.append(path)

            gerado_com_sucesso = False

            # 1. Tenta gerar áudio contínuo com edge-tts (Voz Neural Masculina Antonio)
            if HAS_EDGE_TTS:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        communicate = edge_tts.Communicate(texto_completo, "pt-BR-AntonioNeural", rate=rate_str)
                        loop.run_until_complete(communicate.save(path))
                        gerado_com_sucesso = True
                    finally:
                        loop.close()
                except Exception as e_edge:
                    print(f"Fallback edge-tts -> gtts ({e_edge})")

            # 2. Fallback para gTTS se edge-tts falhar
            if not gerado_com_sucesso:
                tts = gTTS(text=texto_completo, lang='pt', slow=False)
                tts.save(path)

            if self._stop_requested:
                return

            # Toca o áudio único do início ao fim sem interrupções
            if not _garantir_mixer_init():
                print("Não foi possível inicializar o mixer de áudio.")
                return

            pg = _obter_pygame()
            pg.mixer.music.load(path)
            pg.mixer.music.play()

            while pg.mixer.music.get_busy():
                if self._stop_requested:
                    pg.mixer.music.stop()
                    break
                time.sleep(0.1)

            # Aguarda o buffer de áudio da placa de som finalizar para não cortar o final do som
            if not self._stop_requested:
                time.sleep(0.4)

            pg.mixer.music.unload()

        except Exception as e:
            print(f"Erro na execução da fala por áudio: {e}")

        finally:
            # Limpa arquivos temporários gerados
            for p in temp_files:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

            self._is_speaking = False
            if callback_fim and not self._stop_requested:
                try:
                    callback_fim()
                except Exception as cb_err:
                    print(f"Erro no callback de áudio: {cb_err}")

    def ouvir_microfone(self, idioma: str = "auto", timeout_escrita: int = 7) -> dict:
        """
        Escuta o microfone do usuário e retorna a transcrição inteligente.
        Suporta detecção bilingue (pt-BR e en-US) para alunos brasileiros aprendendo inglês.
        """
        if not HAS_STT:
            return {
                "sucesso": False,
                "erro": "Módulo de reconhecimento de voz (SpeechRecognition/pyaudio) não instalado."
            }

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                print("Escutando microfone...")
                audio = recognizer.listen(source, timeout=timeout_escrita, phrase_time_limit=10)

            texto_pt = None
            texto_en = None

            # Tenta reconhecer em Português (pt-BR)
            try:
                texto_pt = recognizer.recognize_google(audio, language="pt-BR")
            except Exception:
                pass

            # Tenta reconhecer em Inglês (en-US)
            try:
                texto_en = recognizer.recognize_google(audio, language="en-US")
            except Exception:
                pass

            if not texto_pt and not texto_en:
                return {
                    "sucesso": False,
                    "erro": "Não foi possível compreender o áudio. Tente falar novamente com mais clareza."
                }

            # Palavras-chave típicas do aluno brasileiro interagindo com o professor em Português
            palavras_chave_pt = [
                "bora", "começar", "comecar", "sim", "não", "nao", "professor", "aula", 
                "dúvida", "duvida", "ajuda", "olá", "ola", "bom", "boa", "entendi", 
                "como", "falar", "dizer", "significa", "exemplo", "meu", "nome", "chamo", "estudo"
            ]

            # Se identificou em PT e o texto contém palavras típicas de interação em português
            if texto_pt:
                texto_pt_lower = texto_pt.lower()
                if any(p in texto_pt_lower for p in palavras_chave_pt) or not texto_en or idioma == "pt-BR":
                    return {
                        "sucesso": True,
                        "texto": texto_pt,
                        "idioma_usado": "pt-BR"
                    }

            # Caso contrário, se identificou em EN e parece um termo ou frase em inglês
            if texto_en:
                return {
                    "sucesso": True,
                    "texto": texto_en,
                    "idioma_usado": "en-US"
                }

            # Fallback final para texto_pt se existir
            return {
                "sucesso": True,
                "texto": texto_pt,
                "idioma_usado": "pt-BR"
            }

        except sr.WaitTimeoutError:
            return {
                "sucesso": False,
                "erro": "Nenhum áudio detectado no microfone dentro do tempo limite."
            }
        except sr.RequestError as e:
            return {
                "sucesso": False,
                "erro": f"Serviço de reconhecimento de voz indisponível: {e}"
            }
        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro no microfone: {e}"
            }

# Instância global do serviço de áudio
audio_engine = AudioService()
