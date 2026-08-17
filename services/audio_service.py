import os
import re
import tempfile
import threading
import time
from .logger import logger
from .config import load_config

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
    logger.warning(f"edge-tts não inicializado: {e}")
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
            logger.warning(f"Pygame não disponível: {e}")
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
            logger.error(f"Erro ao inicializar mixer do Pygame: {e}")
            return False
    return False

# Tenta carregar gTTS para reprodução de áudio
HAS_GTTS = False
try:
    from gtts import gTTS
    HAS_GTTS = True
except Exception as e:
    logger.warning(f"gTTS não inicializado: {e}")
    HAS_GTTS = False

# Tenta carregar SpeechRecognition e PyAudio para microfone
HAS_STT = False
try:
    import speech_recognition as sr
    HAS_STT = True
except Exception as e:
    logger.warning(f"SpeechRecognition não inicializado: {e}")
    HAS_STT = False

# Tenta carregar faster-whisper para transcrição local ultra-rápida e offline
HAS_WHISPER = False
_WHISPER_MODEL = None
_WHISPER_LOCK = threading.Lock()

def _obter_modelo_whisper():
    global HAS_WHISPER, _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        with _WHISPER_LOCK:
            if _WHISPER_MODEL is None:
                try:
                    from faster_whisper import WhisperModel
                    logger.info("Inicializando modelo Whisper local (base - CPU)...")
                    _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
                    HAS_WHISPER = True
                except Exception as e:
                    logger.warning(f"faster-whisper não disponível ({e}). Usando fallback Google STT.")
                    _WHISPER_MODEL = False
                    HAS_WHISPER = False
    return _WHISPER_MODEL if _WHISPER_MODEL is not False else None

class AudioService:

    def __init__(self):
        self._speaking_thread = None
        self._is_speaking = False
        self._stop_requested = False
        self.velocidade = 1.0  # Velocidade padrão (1.0, 1.25, 1.5)
        self.conversa_viva_ativa = False  # Modo Conversa Viva / Hands-free

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

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

    def parar(self):
        """Alias para parar_fala()."""
        self.parar_fala()

    def gerar_e_tocar(self, texto: str, lang: str = "en", velocity: float = 1.0, callback_fim=None):
        """
        Sintetiza e reproduz qualquer texto em áudio (Inglês ou Português) de forma assíncrona.
        Ajusta a voz neural (ex: en-US-AnaNeural para Inglês, pt-BR-AntonioNeural para Português) e a velocidade.
        """
        if not texto or not texto.strip():
            return

        self.parar_fala()
        self._stop_requested = False

        def _thread_tocar():
            self._is_speaking = True
            temp_files = []
            try:
                if not HAS_GTTS and not HAS_EDGE_TTS:
                    logger.warning("Recurso de áudio não disponível (edge-tts e gtts ausentes).")
                    self._is_speaking = False
                    return

                rate_percent = int((velocity - 1.0) * 100)
                rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                temp_files.append(path)

                gerado = False
                voz = "en-US-AnaNeural" if lang == "en" else load_config().get("voice", "pt-BR-AntonioNeural")

                if HAS_EDGE_TTS:
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            communicate = edge_tts.Communicate(texto.strip(), voz, rate=rate_str)
                            loop.run_until_complete(communicate.save(path))
                            gerado = True
                        finally:
                            loop.close()
                    except Exception as e_edge:
                        logger.warning(f"Fallback edge-tts ({voz}) -> gTTS ({e_edge})")

                if not gerado and HAS_GTTS:
                    tts = gTTS(text=texto.strip(), lang=lang, slow=False)
                    tts.save(path)

                if self._stop_requested:
                    return

                if not _garantir_mixer_init():
                    return

                pg = _obter_pygame()
                pg.mixer.music.load(path)
                pg.mixer.music.play()

                while pg.mixer.music.get_busy():
                    if self._stop_requested:
                        pg.mixer.music.stop()
                        break
                    time.sleep(0.1)

                if not self._stop_requested:
                    time.sleep(0.3)

            except Exception as e:
                logger.error(f"Erro ao gerar e tocar áudio: {e}")
            finally:
                pg = _obter_pygame()
                if pg and pg.mixer.get_init():
                    try:
                        pg.mixer.music.stop()
                        pg.mixer.music.unload()
                    except Exception:
                        pass
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
                    except Exception:
                        pass

        self._speaking_thread = threading.Thread(target=_thread_tocar, daemon=True)
        self._speaking_thread.start()

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
            if not HAS_GTTS and not HAS_EDGE_TTS:
                logger.warning("Recurso de áudio não disponível (edge-tts e gtts ausentes).")
                self._is_speaking = False
                if callback_fim and not self._stop_requested:
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
                if callback_fim and not self._stop_requested:
                    callback_fim()
                return

            rate_percent = int((velocidade - 1.0) * 100)
            rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            temp_files.append(path)

            gerado_com_sucesso = False

            # Carrega a voz configurada pelo usuário (padrão AntonioNeural)
            cfg = load_config()
            voz_neural = cfg.get("voice", "pt-BR-AntonioNeural")

            # 1. Tenta gerar áudio contínuo com edge-tts (Voz Neural Selecionada)
            if HAS_EDGE_TTS:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        communicate = edge_tts.Communicate(texto_completo, voz_neural, rate=rate_str)
                        loop.run_until_complete(communicate.save(path))
                        gerado_com_sucesso = True
                    finally:
                        loop.close()
                except Exception as e_edge:
                    logger.warning(f"Fallback edge-tts ({voz_neural}) -> gtts ({e_edge})")

            # 2. Fallback para gTTS se edge-tts falhar
            if not gerado_com_sucesso and HAS_GTTS:
                tts = gTTS(text=texto_completo, lang='pt', slow=False)
                tts.save(path)

            if self._stop_requested:
                return

            # Toca o áudio único do início ao fim sem interrupções
            if not _garantir_mixer_init():
                logger.error("Não foi possível inicializar o mixer de áudio.")
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

        except Exception as e:
            logger.error(f"Erro na execução da fala por áudio: {e}")

        finally:
            pg = _obter_pygame()
            if pg and pg.mixer.get_init():
                try:
                    pg.mixer.music.stop()
                    pg.mixer.music.unload()
                except Exception:
                    pass

            # Limpeza garantida dos arquivos temporários de áudio
            for p in temp_files:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception as e_clean:
                    logger.warning(f"Falha ao remover arquivo temporário de áudio '{p}': {e_clean}")

            self._is_speaking = False
            if callback_fim and not self._stop_requested:
                try:
                    callback_fim()
                except Exception as cb_err:
                    logger.error(f"Erro no callback de áudio: {cb_err}")

    def ouvir_microfone(self, idioma: str = "auto", timeout_escrita: int = 7) -> dict:
        """
        Escuta o microfone do usuário e retorna a transcrição inteligente.
        Suporta Whisper local (faster-whisper) com fallback automático para Google Speech API.
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
                logger.info("Escutando microfone...")
                audio = recognizer.listen(source, timeout=timeout_escrita, phrase_time_limit=10)

            # 1. Tenta transcrição local offline e ultra precisa com faster-whisper
            whisper_model = _obter_modelo_whisper()
            if whisper_model:
                temp_wav_path = None
                try:
                    wav_data = audio.get_wav_data()
                    fd, temp_wav_path = tempfile.mkstemp(suffix=".wav")
                    os.close(fd)
                    with open(temp_wav_path, "wb") as f:
                        f.write(wav_data)

                    segments, info = whisper_model.transcribe(temp_wav_path, beam_size=1)
                    texto_transcrito = " ".join([seg.text.strip() for seg in segments if seg.text]).strip()
                    if texto_transcrito:
                        return {
                            "sucesso": True,
                            "texto": texto_transcrito,
                            "idioma_usado": info.language,
                            "engine": "Whisper (Local)"
                        }
                except Exception as e_w:
                    logger.warning(f"Fallback Whisper -> Google STT ({e_w})")
                finally:
                    if temp_wav_path and os.path.exists(temp_wav_path):
                        try:
                            os.remove(temp_wav_path)
                        except Exception as e_del:
                            logger.warning(f"Falha ao deletar temporário WAV '{temp_wav_path}': {e_del}")

            # 2. Fallback para Google Speech Recognition se Whisper não transcrever ou não estiver presente
            texto_pt = None
            texto_en = None

            try:
                texto_pt = recognizer.recognize_google(audio, language="pt-BR")
            except Exception:
                pass

            try:
                texto_en = recognizer.recognize_google(audio, language="en-US")
            except Exception:
                pass

            if not texto_pt and not texto_en:
                return {
                    "sucesso": False,
                    "erro": "Não foi possível compreender o áudio. Tente falar novamente com mais clareza."
                }

            palavras_chave_pt = [
                "bora", "começar", "comecar", "sim", "não", "nao", "professor", "aula", 
                "dúvida", "duvida", "ajuda", "olá", "ola", "bom", "boa", "entendi", 
                "como", "falar", "dizer", "significa", "exemplo", "meu", "nome", "chamo", "estudo"
            ]

            if texto_pt:
                texto_pt_lower = texto_pt.lower()
                if any(p in texto_pt_lower for p in palavras_chave_pt) or not texto_en or idioma == "pt-BR":
                    return {
                        "sucesso": True,
                        "texto": texto_pt,
                        "idioma_usado": "pt-BR",
                        "engine": "Google STT"
                    }

            if texto_en:
                return {
                    "sucesso": True,
                    "texto": texto_en,
                    "idioma_usado": "en-US",
                    "engine": "Google STT"
                }

            return {
                "sucesso": True,
                "texto": texto_pt,
                "idioma_usado": "pt-BR",
                "engine": "Google STT"
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
