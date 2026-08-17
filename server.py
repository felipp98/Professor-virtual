import os
import io
import tempfile
import asyncio
import socket
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.database import (
    init_db, listar_termos, salvar_termo, deletar_termo,
    obter_estatisticas, exportar_csv, obter_perfil_aluno,
    salvar_perfil_aluno, registrar_progresso_aula
)
from services.teacher_service import teacher_engine
from services.ai_service import consultar_openrouter
from services.docs_service import listar_documentos, ler_pdf, buscar_nos_documentos
from services.config import load_config, save_config, obter_api_key, salvar_api_key
from services.logger import logger

# Inicializa banco de dados
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="Language Buddy Mobile API",
    description="Backend Web e PWA para o Professor Virtual & Painel de Estudos",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# MODELOS DE REQUISIÇÃO (PYDANTIC)
# ----------------------------------------------------
class TeacherInteractionRequest(BaseModel):
    mensagem: str

class SalvarTermoRequest(BaseModel):
    termo_ingles: str
    traducao: str
    pronuncia_abrasileirada: str
    exemplo_contexto: Optional[str] = ""
    traducao_exemplo: Optional[str] = ""

class SalvarPerfilRequest(BaseModel):
    nome: str
    nivel: Optional[str] = "Básico"
    ultimo_topico: Optional[str] = ""

class SalvarConfigRequest(BaseModel):
    model: Optional[str] = None
    voice: Optional[str] = None
    api_key: Optional[str] = None

class ConsultarIARequest(BaseModel):
    termo: str


# ----------------------------------------------------
# ROTAS DO PROFESSOR VIRTUAL (TEACHER ALEX)
# ----------------------------------------------------
@app.get("/api/teacher/start")
def teacher_start():
    """Inicia a sessão com o professor virtual ou retorna o estado de onboarding."""
    return teacher_engine.iniciar_aula()

@app.post("/api/teacher/interact")
def teacher_interact(req: TeacherInteractionRequest):
    """Processa a interação por fala/texto do aluno e retorna a resposta pedagógica."""
    if not req.mensagem or not req.mensagem.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode ser vazia.")
    resultado = teacher_engine.processar_interacao(req.mensagem.strip())
    return resultado


# ----------------------------------------------------
# ROTAS DE SÍNTESE E TRANSCRIÇÃO DE ÁUDIO
# ----------------------------------------------------
@app.get("/api/audio/tts")
async def audio_tts(
    texto: str = Query(..., description="Texto a ser falado"),
    lang: str = Query("pt", description="Idioma: pt ou en"),
    voz: Optional[str] = Query(None, description="Voz neural opcional")
):
    """
    Sintetiza qualquer texto em áudio MP3 neural e transmite como streaming de áudio
    diretamente para o player HTML5 do celular.
    """
    if not texto or not texto.strip():
        raise HTTPException(status_code=400, detail="Texto para áudio não informado.")

    texto_limpo = texto.strip()
    cfg = load_config()
    
    # Determina a voz neural
    if voz:
        voz_selecionada = voz
    elif lang == "en":
        voz_selecionada = "en-US-AnaNeural"
    else:
        voz_selecionada = cfg.get("voice", "pt-BR-AntonioNeural")

    temp_path = None
    try:
        # Tenta gerar com edge-tts (voz neural realista)
        try:
            import edge_tts
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            
            communicate = edge_tts.Communicate(texto_limpo, voz_selecionada)
            await communicate.save(temp_path)
            
            with open(temp_path, "rb") as f:
                audio_bytes = f.read()
                
            return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
        except Exception as e_edge:
            logger.warning(f"Fallback edge-tts -> gTTS no servidor web: {e_edge}")
            from gtts import gTTS
            tts = gTTS(text=texto_limpo, lang=lang, slow=False)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            return StreamingResponse(buffer, media_type="audio/mpeg")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.post("/api/audio/stt")
async def audio_stt(file: UploadFile = File(...)):
    """
    Recebe o áudio gravado no microfone do celular (WebM/WAV) e realiza transcrição.
    """
    temp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1] or ".wav"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # 1. Tenta transcrever com faster-whisper local
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(temp_path, language="pt")
            texto_transcrito = " ".join([s.text for s in segments]).strip()
            if texto_transcrito:
                return {"sucesso": True, "texto": texto_transcrito}
        except Exception as e_w:
            logger.warning(f"Whisper STT falhou: {e_w}. Tentando SpeechRecognition...")

        # 2. Fallback SpeechRecognition
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(temp_path) as source:
                audio_data = r.record(source)
                texto_transcrito = r.recognize_google(audio_data, language="pt-BR")
                return {"sucesso": True, "texto": texto_transcrito}
        except Exception as e_sr:
            logger.warning(f"SpeechRecognition falhou: {e_sr}")

        return {"sucesso": False, "erro": "Não foi possível transcrever o áudio gravado."}

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ----------------------------------------------------
# ROTAS DO CADERNO DE ESTUDOS (VOCABULÁRIO)
# ----------------------------------------------------
@app.get("/api/caderno/listar")
def caderno_listar(busca: str = Query("", description="Termo de filtro")):
    termos = listar_termos(busca)
    stats = obter_estatisticas()
    return {"termos": termos, "estatisticas": stats}

@app.post("/api/caderno/salvar")
def caderno_salvar(req: SalvarTermoRequest):
    sucesso = salvar_termo(
        termo_ingles=req.termo_ingles,
        traducao=req.traducao,
        pronuncia_abrasileirada=req.pronuncia_abrasileirada,
        exemplo_contexto=req.exemplo_contexto or "",
        traducao_exemplo=req.traducao_exemplo or ""
    )
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao salvar termo no banco.")
    return {"sucesso": True, "mensagem": "Termo salvo no caderno com sucesso!"}

@app.delete("/api/caderno/deletar/{termo_id}")
def caderno_deletar(termo_id: int):
    sucesso = deletar_termo(termo_id)
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao deletar termo.")
    return {"sucesso": True}

@app.get("/api/caderno/exportar-csv")
def caderno_exportar_csv():
    fd, temp_csv = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    if exportar_csv(temp_csv):
        return FileResponse(
            temp_csv,
            media_type="text/csv",
            filename="caderno_estudos_ingles.csv",
            headers={"Content-Disposition": "attachment; filename=caderno_estudos_ingles.csv"}
        )
    raise HTTPException(status_code=500, detail="Falha ao gerar arquivo CSV.")


# ----------------------------------------------------
# ROTAS DE CONSULTA IA & DECKS DE ESTUDO (PDFS)
# ----------------------------------------------------
@app.post("/api/ia/consultar")
def ia_consultar(req: ConsultarIARequest):
    if not req.termo or not req.termo.strip():
        raise HTTPException(status_code=400, detail="Termo de busca não pode ser vazio.")
    res = consultar_openrouter(req.termo.strip())
    return res

@app.get("/api/docs/listar")
def docs_listar():
    return {"documentos": listar_documentos()}

@app.get("/api/docs/ler")
def docs_ler(filepath: str = Query(..., description="Caminho do arquivo PDF")):
    return ler_pdf(filepath)

@app.get("/api/docs/buscar")
def docs_buscar(termo: str = Query(..., description="Palavra-chave")):
    return {"resultados": buscar_nos_documentos(termo)}


# ----------------------------------------------------
# ROTAS DE PERFIL E CONFIGURAÇÕES
# ----------------------------------------------------
@app.get("/api/perfil")
def perfil_obter():
    perfil = obter_perfil_aluno()
    return {"perfil": perfil}

@app.post("/api/perfil/salvar")
def perfil_salvar(req: SalvarPerfilRequest):
    sucesso = salvar_perfil_aluno(req.nome, req.nivel or "Básico", req.ultimo_topico or "")
    return {"sucesso": sucesso}

@app.get("/api/config/obter")
def config_obter():
    cfg = load_config()
    key = obter_api_key()
    return {
        "model": cfg.get("model"),
        "voice": cfg.get("voice"),
        "fallback_models": cfg.get("fallback_models", []),
        "pomodoro_work_minutes": cfg.get("pomodoro_work_minutes", 30),
        "pomodoro_break_minutes": cfg.get("pomodoro_break_minutes", 5),
        "has_api_key": bool(key),
        "masked_key": f"sk-...{key[-6:]}" if key and len(key) > 6 else ("sk-..." if key else "")
    }

@app.post("/api/config/salvar")
def config_salvar(req: SalvarConfigRequest):
    cfg = load_config()
    if req.model:
        cfg["model"] = req.model
    if req.voice:
        cfg["voice"] = req.voice
    if req.api_key is not None and req.api_key.strip() != "":
        cfg["api_key"] = req.api_key.strip()
    sucesso = save_config(cfg)
    return {"sucesso": sucesso}


# ----------------------------------------------------
# SERVE ARQUIVOS ESTÁTICOS E PWA NA RAIZ
# ----------------------------------------------------
@app.get("/manifest.json")
def serve_manifest():
    manifest_file = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(manifest_file):
        return FileResponse(manifest_file, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="Manifest não encontrado")

@app.get("/sw.js")
def serve_sw():
    sw_file = os.path.join(STATIC_DIR, "sw.js")
    if os.path.exists(sw_file):
        return FileResponse(
            sw_file, 
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"}
        )
    raise HTTPException(status_code=404, detail="Service Worker não encontrado")

@app.get("/favicon.ico")
def serve_favicon():
    icon_file = os.path.join(STATIC_DIR, "icons", "icon-192.png")
    if os.path.exists(icon_file):
        return FileResponse(icon_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon não encontrado")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def index_html():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="""
    <html>
        <head><title>Language Buddy API</title></head>
        <body style="font-family: sans-serif; background: #09090b; color: #fff; text-align: center; padding: 50px;">
            <h1>🗣️ Language Buddy Server Online</h1>
            <p>Servidor FastAPI ativo. Construindo a interface PWA...</p>
        </body>
    </html>
    """)


def obter_ip_local():
    """Descobre o IP da máquina na rede local para facilitar acesso pelo celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    import uvicorn
    porta = int(os.environ.get("PORT", 8000))
    ip_local = obter_ip_local()
    print("=" * 65)
    print(f"🚀 LANGUAGE BUDDY - SERVIDOR WEB & MOBILE PWA")
    print("=" * 65)
    print(f"📱 Acesso no Computador: http://localhost:{porta}")
    if ip_local != "127.0.0.1":
        print(f"📲 Acesso no Celular (mesmo Wi-Fi): http://{ip_local}:{porta}")
    print("=" * 65)
    uvicorn.run("server:app", host="0.0.0.0", port=porta, reload=False)

