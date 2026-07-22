import customtkinter as ctk
import tkinter
from tkinter import messagebox, filedialog
import threading
import time
import os
import tempfile

from services.config import load_config, save_config
from services.database import init_db, salvar_termo, listar_termos, deletar_termo, obter_estatisticas, exportar_csv, obter_perfil_aluno, salvar_perfil_aluno
from services.ai_service import consultar_openrouter
from services.docs_service import listar_documentos, ler_pdf, buscar_nos_documentos
from services.audio_service import audio_engine
from services.teacher_service import teacher_engine, TeacherService



# Configurações do Tema Visual CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LanguageBuddyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inicializa Banco de Dados
        init_db()

        # Configurações da Janela
        self.title("Language Buddy — Professor Virtual & Painel de Estudos")
        self.geometry("980x750")
        self.minsize(850, 600)

        # Variáveis de Estado
        self.resultado_atual_ia = None
        self.pomodoro_rodando = False
        self.pomodoro_tempo_restante = 30 * 60  # 30 minutos padrão
        self.pomodoro_tempo_total = 30 * 60
        self.pomodoro_timer_id = None

        # Variáveis de Estado do Professor Virtual
        self.teacher_is_listening = False
        self.ultimo_pacote_professor = None

        # Variáveis de Estado dos Documentos (PDFs)
        self.lista_documentos = []
        self.doc_atual = None

        # Layout Principal (Barra de Abas)
        self.setup_ui()

        # Força visibilidade em primeiro plano após carregar os componentes visuais
        self.after(200, self._bring_to_front)

    def _bring_to_front(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(1000, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def setup_ui(self):
        # Abas da Aplicação
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_teacher = self.tabview.add("🎓 Professor Virtual")
        self.tab_ia = self.tabview.add("🔎 Consultar IA")
        self.tab_caderno = self.tabview.add("📖 Meu Caderno")
        self.tab_docs = self.tabview.add("📚 Decks de Estudo")
        self.tab_pomodoro = self.tabview.add("⏱️ Timer Pomodoro")
        self.tab_config = self.tabview.add("⚙️ Configurações")

        # Inicializa cada tela
        self.build_tab_teacher()
        self.build_tab_ia()
        self.build_tab_caderno()
        self.build_tab_docs()
        self.build_tab_pomodoro()
        self.build_tab_config()


    # ==========================================
    # 🎓 ABA 0: PROFESSOR VIRTUAL (VOZ & TEXTO)
    # ==========================================
    def build_tab_teacher(self):
        # Header / Status Card Topo
        top_frame = ctk.CTkFrame(self.tab_teacher, fg_color=("gray85", "gray17"), corner_radius=10)
        top_frame.pack(fill="x", padx=15, pady=(10, 5))

        title_label = ctk.CTkLabel(
            top_frame, 
            text="🎓 Professor Virtual Alex — Aulas por Voz e Texto", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(side="left", padx=15, pady=12)

        self.btn_iniciar_aula = ctk.CTkButton(
            top_frame, 
            text="▶️ Iniciar / Reiniciar Aula", 
            command=self.iniciar_aula_teacher,
            fg_color="#2b5b84",
            hover_color="#1d3d59",
            width=160
        )
        self.btn_iniciar_aula.pack(side="right", padx=15, pady=12)

        # Barra de Status Dinâmica do Áudio / Professor
        self.status_bar_frame = ctk.CTkFrame(self.tab_teacher, fg_color="#1e293b", corner_radius=8)
        self.status_bar_frame.pack(fill="x", padx=15, pady=5)

        self.lbl_status_teacher = ctk.CTkLabel(
            self.status_bar_frame, 
            text="🗣️ Clique em '▶️ Iniciar Aula' para começar sua lição guiada por voz.", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_status_teacher.pack(side="left", padx=15, pady=8)

        self.btn_parar_audio = ctk.CTkButton(
            self.status_bar_frame, 
            text="⏹️ Parar Áudio", 
            command=self.parar_audio_teacher,
            fg_color="#e11d48",
            hover_color="#9f1239",
            width=100,
            height=28
        )
        self.btn_parar_audio.pack(side="right", padx=15, pady=8)

        # Seletor de Velocidade do Áudio (1.0x, 1.25x, 1.5x)
        self.opt_speed = ctk.CTkOptionMenu(
            self.status_bar_frame,
            values=["⚡ 1.0x (Normal)", "⚡ 1.25x (Rápido)", "⚡ 1.5x (Super Rápido)"],
            command=self._mudar_velocidade_audio,
            width=145,
            height=28,
            fg_color="#334155",
            button_color="#475569"
        )
        self.opt_speed.set("⚡ 1.0x (Normal)")
        self.opt_speed.pack(side="right", padx=(0, 8), pady=8)

        # Seletor de Nível de Inglês (Básico, Intermediário, Avançado)
        self.opt_nivel = ctk.CTkOptionMenu(
            self.status_bar_frame,
            values=["🌱 Básico", "🌿 Intermediário", "🚀 Avançado"],
            command=self._mudar_nivel_aluno,
            width=135,
            height=28,
            fg_color="#1e293b",
            button_color="#334155"
        )
        perfil_atual = obter_perfil_aluno()
        nivel_salvo = perfil_atual.get("nivel", "Básico") if perfil_atual else "Básico"
        if nivel_salvo == "Intermediário":
            self.opt_nivel.set("🌿 Intermediário")
        elif nivel_salvo == "Avançado":
            self.opt_nivel.set("🚀 Avançado")
        else:
            self.opt_nivel.set("🌱 Básico")

        self.opt_nivel.pack(side="right", padx=(0, 8), pady=8)

        # Chat Scrollable Frame (Histórico da Aula)
        self.chat_scroll = ctk.CTkScrollableFrame(self.tab_teacher, fg_color=("gray90", "#0f172a"), corner_radius=10)
        self.chat_scroll.pack(fill="both", expand=True, padx=15, pady=5)

        # Frame de Entrada de Texto e Botão de Voz na parte inferior
        controls_frame = ctk.CTkFrame(self.tab_teacher, fg_color="transparent")
        controls_frame.pack(fill="x", padx=15, pady=(5, 10))

        self.btn_mic = ctk.CTkButton(
            controls_frame, 
            text="🎙️ Responder por Voz", 
            command=self.ouvir_microfone_teacher,
            fg_color="#059669",
            hover_color="#047857",
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=170
        )
        self.btn_mic.pack(side="left", padx=(0, 10))

        self.entry_teacher = ctk.CTkEntry(
            controls_frame, 
            placeholder_text="Digite sua resposta ou dúvida para o professor...", 
            height=45, 
            font=ctk.CTkFont(size=14)
        )
        self.entry_teacher.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_teacher.bind("<Return>", lambda event: self.enviar_mensagem_teacher())

        self.btn_send_teacher = ctk.CTkButton(
            controls_frame, 
            text="Enviar 📤", 
            command=self.enviar_mensagem_teacher,
            height=45,
            width=100,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_send_teacher.pack(side="right")

    def _mudar_velocidade_audio(self, escolha: str):
        """Altera a velocidade de fala do professor virtual (1.0x, 1.25x, 1.5x)."""
        if "1.25x" in escolha:
            audio_engine.velocidade = 1.25
        elif "1.5x" in escolha:
            audio_engine.velocidade = 1.5
        else:
            audio_engine.velocidade = 1.0

    def _mudar_nivel_aluno(self, escolha: str):
        """Altera e salva no banco de dados o nível de proficiência de inglês do aluno."""
        nivel_limpo = escolha.replace("🌱 ", "").replace("🌿 ", "").replace("🚀 ", "").strip()
        perfil = obter_perfil_aluno()
        nome = perfil.get("nome", "Aluno") if perfil else "Aluno"
        salvar_perfil_aluno(nome=nome, nivel=nivel_limpo)
        self.lbl_status_teacher.configure(text=f"🎯 Nível de ensino atualizado para: {nivel_limpo}!", text_color="#10b981")

    def iniciar_aula_teacher(self):
        """Inicia a sessão do professor virtual e executa a mensagem inicial."""
        audio_engine.parar_fala()
        pacote = TeacherService.iniciar_aula()
        self.exibir_resposta_professor(pacote)

    def parar_audio_teacher(self):
        """Para qualquer áudio em reprodução."""
        audio_engine.parar_fala()
        self.lbl_status_teacher.configure(text="⏹️ Áudio interrompido.", text_color="gray")

    def ouvir_microfone_teacher(self):
        """Escuta a voz do aluno no microfone em uma thread separada."""
        if audio_engine.is_speaking:
            audio_engine.parar_fala()

        self.lbl_status_teacher.configure(text="🎙️ Fale agora no microfone... (Escutando)", text_color="#f59e0b")
        self.btn_mic.configure(state="disabled", fg_color="#d97706")

        def _worker_mic():
            res = audio_engine.ouvir_microfone(idioma="auto", timeout_escrita=7)
            self.after(0, lambda: self._processar_resultado_mic(res))

        threading.Thread(target=_worker_mic, daemon=True).start()

    def _processar_resultado_mic(self, res: dict):
        self.btn_mic.configure(state="normal", fg_color="#059669")
        if res.get("sucesso"):
            texto = res.get("texto", "").strip()
            self.lbl_status_teacher.configure(text=f"✅ Voz reconhecida: '{texto}'", text_color="#10b981")
            self.enviar_mensagem_teacher(texto_aluno=texto)
        else:
            erro = res.get("erro", "Não entendi.")
            self.lbl_status_teacher.configure(text=f"⚠️ {erro}", text_color="#ef4444")
            audio_engine.falar(texto_pt="Desculpe, não consegui entender o que você disse no microfone. Pode repetir ou digitar por favor?")

    def enviar_mensagem_teacher(self, texto_aluno: str = None):
        if texto_aluno is None:
            texto_aluno = self.entry_teacher.get().strip()
            self.entry_teacher.delete(0, "end")

        if not texto_aluno:
            return

        # Adiciona mensagem do aluno no chat
        self._adicionar_balao_chat("aluno", texto_aluno)
        self.lbl_status_teacher.configure(text="🤔 Professor Alex está pensando...", text_color="#38bdf8")

        def _worker_ia():
            pacote = teacher_engine.processar_interacao(texto_aluno)
            self.after(0, lambda: self.exibir_resposta_professor(pacote))

        threading.Thread(target=_worker_ia, daemon=True).start()

    def exibir_resposta_professor(self, pacote: dict):
        self.ultimo_pacote_professor = pacote
        fala_pt = pacote.get("fala_audio_pt", "")
        termo_en = pacote.get("termo_en", "")
        pronuncia = pacote.get("pronuncia_abrasileirada", "")
        dica_articulacao = pacote.get("dica_articulacao", "")
        texto_chat = pacote.get("texto_chat", "")
        modo_resp = pacote.get("modo_resposta", "voz")
        instrucao = pacote.get("instrucao_aluno", "")

        # Adiciona balão do professor no chat
        self._adicionar_balao_chat("professor", texto_chat, fala_pt, termo_en, pronuncia, instrucao, dica_articulacao)

        # Atualiza barra de status
        if modo_resp == "voz":
            self.lbl_status_teacher.configure(text="🎙️ Modo Voz: Responda usando o botão de microfone!", text_color="#10b981")
        else:
            self.lbl_status_teacher.configure(text="⌨️ Modo Texto: Digite sua resposta abaixo.", text_color="#38bdf8")

        # Reproduz áudio do professor
        if fala_pt:
            audio_engine.falar(
                texto_pt=fala_pt,
                termo_en=termo_en,
                pronuncia_abrasileirada=pronuncia,
                callback_fim=lambda: self.lbl_status_teacher.configure(text="👂 Aguardando sua resposta...", text_color="#a855f7")
            )
        self.after(50, self._rolar_chat_para_fim)
        self.after(200, self._rolar_chat_para_fim)

    def _rolar_chat_para_fim(self):
        """Garante que a barra de rolagem do chat vá para o final de forma suave e precisa."""
        try:
            self.update_idletasks()
            if hasattr(self, "chat_scroll") and hasattr(self.chat_scroll, "_parent_canvas") and self.chat_scroll._parent_canvas.winfo_exists():
                self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def copiar_para_area_transferencia(self, texto: str, rotulo: str = "Texto"):
        """Copia um texto diretamente para a área de transferência do Windows."""
        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.update()
            if hasattr(self, "lbl_status_teacher") and self.lbl_status_teacher.winfo_exists():
                self.lbl_status_teacher.configure(text=f"📋 {rotulo} copiado para a área de transferência!", text_color="#10b981")
            elif hasattr(self, "lbl_status_ia") and self.lbl_status_ia.winfo_exists():
                self.lbl_status_ia.configure(text=f"📋 {rotulo} copiado para a área de transferência!", text_color="#10b981")
        except Exception as e:
            messagebox.showerror("Erro ao Copiar", f"Não foi possível copiar: {e}")

    def criar_campo_texto_selecionavel(self, master, texto: str, font_size: int = 14, font_weight: str = "normal", text_color: str = "white", fg_color: str = "transparent", max_height: int = 250) -> ctk.CTkTextbox:
        """Cria um widget de texto selecionável pelo mouse que suporta seleção de trechos, Ctrl+C e botão direito."""
        linhas = texto.count('\n') + 1
        char_count = len(texto)
        linhas_estimadas = max(linhas, (char_count // 52) + 1)
        altura = max(36, min(max_height, linhas_estimadas * 22 + 10))

        tb = ctk.CTkTextbox(
            master,
            fg_color=fg_color,
            text_color=text_color,
            font=ctk.CTkFont(size=font_size, weight=font_weight),
            wrap="word",
            height=altura,
            border_width=0,
            activate_scrollbars=True if altura >= max_height else False
        )
        tb.insert("1.0", texto)

        # Permite apenas seleção de texto, cópia por Ctrl+C e navegação por setas
        def _bloquear_edicao(event):
            if (event.state & 4 and event.keysym.lower() == 'c') or event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End']:
                return None
            return 'break'

        tb.bind("<Key>", _bloquear_edicao)

        # Menu de Contexto ao Clicar com o Botão Direito no Texto
        menu = tkinter.Menu(tb._textbox, tearoff=0)
        def _copiar_trecho():
            try:
                sel = tb._textbox.get("sel.first", "sel.last")
                if sel:
                    self.clipboard_clear()
                    self.clipboard_append(sel)
                    self.update()
                    if hasattr(self, "lbl_status_teacher") and self.lbl_status_teacher.winfo_exists():
                        self.lbl_status_teacher.configure(text=f"📋 Trecho selecionado copiado!", text_color="#10b981")
                    elif hasattr(self, "lbl_status_ia") and self.lbl_status_ia.winfo_exists():
                        self.lbl_status_ia.configure(text=f"📋 Trecho selecionado copiado!", text_color="#10b981")
            except Exception:
                pass

        menu.add_command(label="📋 Copiar seleção", command=_copiar_trecho)
        tb._textbox.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        return tb

    def _adicionar_balao_chat(self, remetente: str, texto: str, fala_pt: str = "", termo_en: str = "", pronuncia: str = "", instrucao: str = "", dica_articulacao: str = ""):
        card_bg = "#1e293b" if remetente == "professor" else "#1e3a8a"
        card = ctk.CTkFrame(
            self.chat_scroll, 
            fg_color=card_bg, 
            corner_radius=12
        )
        card.pack(fill="x", padx=10, pady=6, anchor="w" if remetente == "professor" else "e")

        header_str = "🎓 Professor Alex" if remetente == "professor" else "👤 Você"
        lbl_sender = ctk.CTkLabel(
            card, 
            text=header_str, 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8" if remetente == "professor" else "#93c5fd"
        )
        lbl_sender.pack(anchor="w", padx=12, pady=(8, 2))

        # Texto da mensagem selecionável com o mouse
        tb_content = self.criar_campo_texto_selecionavel(
            card, 
            texto=texto, 
            font_size=14, 
            text_color="#f8fafc" if remetente == "professor" else "#ffffff", 
            fg_color=card_bg
        )
        tb_content.pack(fill="x", padx=8, pady=(0, 4))

        if remetente == "professor":
            if termo_en:
                tb_en = self.criar_campo_texto_selecionavel(
                    card, 
                    texto=f"🇺🇸 Termo em Inglês: {termo_en}", 
                    font_size=14, 
                    font_weight="bold", 
                    text_color="#38bdf8", 
                    fg_color=card_bg,
                    max_height=50
                )
                tb_en.pack(fill="x", padx=8, pady=(0, 2))

            if pronuncia:
                tb_pron = self.criar_campo_texto_selecionavel(
                    card, 
                    texto=f"🗣️ Pronúncia Abrasileirada: {pronuncia}", 
                    font_size=13, 
                    font_weight="bold", 
                    text_color="#f59e0b", 
                    fg_color=card_bg,
                    max_height=50
                )
                tb_pron.pack(fill="x", padx=8, pady=(0, 4))

            if dica_articulacao:
                tb_dica = self.criar_campo_texto_selecionavel(
                    card, 
                    texto=f"👅 Dica da Língua & Boca: {dica_articulacao}", 
                    font_size=13, 
                    font_weight="bold", 
                    text_color="#c084fc", 
                    fg_color=card_bg,
                    max_height=65
                )
                tb_dica.pack(fill="x", padx=8, pady=(0, 4))

            if instrucao:
                lbl_inst = ctk.CTkLabel(
                    card, 
                    text=f"👉 {instrucao}", 
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="#94a3b8"
                )
                lbl_inst.pack(anchor="w", padx=12, pady=(0, 6))

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(anchor="w", padx=12, pady=(0, 8))

            btn_replay = ctk.CTkButton(
                btn_frame, 
                text="🔊 Ouvir Novamente", 
                width=130, 
                height=26,
                fg_color="#3b82f6",
                hover_color="#1d4ed8",
                font=ctk.CTkFont(size=11),
                command=lambda: audio_engine.falar(fala_pt, termo_en, pronuncia)
            )
            btn_replay.pack(side="left", padx=(0, 8))

            texto_para_copiar = f"Termo: {termo_en}\nPronúncia: {pronuncia}\n\n{texto}" if termo_en else texto
            btn_copiar = ctk.CTkButton(
                btn_frame,
                text="📋 Copiar Tudo",
                width=90,
                height=26,
                fg_color="#475569",
                hover_color="#334155",
                font=ctk.CTkFont(size=11),
                command=lambda t=texto_para_copiar: self.copiar_para_area_transferencia(t, "Mensagem do Professor")
            )
            btn_copiar.pack(side="left")

        else:
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(anchor="e", padx=12, pady=(0, 8))

            btn_copiar_aluno = ctk.CTkButton(
                btn_frame,
                text="📋 Copiar Tudo",
                width=90,
                height=24,
                fg_color="#1e40af",
                hover_color="#1d4ed8",
                font=ctk.CTkFont(size=11),
                command=lambda t=texto: self.copiar_para_area_transferencia(t, "Sua Mensagem")
            )
            btn_copiar_aluno.pack(side="right")

        self._rolar_chat_para_fim()
        self.after(50, self._rolar_chat_para_fim)
        self.after(150, self._rolar_chat_para_fim)
        self.after(300, self._rolar_chat_para_fim)

    # ==========================================
    # 📑 ABA 1: CONSULTAR IA (ABRASILEIRAR)
    # ==========================================
    def build_tab_ia(self):

        # Título da seção
        header = ctk.CTkLabel(
            self.tab_ia, 
            text="Abrasileirar Pronúncia & Contexto de Trabalho", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(anchor="w", padx=20, pady=(15, 5))

        subtitle = ctk.CTkLabel(
            self.tab_ia, 
            text="Digite um termo em inglês para receber a tradução, pronúncia fonética abrasileirada e exemplo prático.", 
            text_color="gray"
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 15))

        # Frame de Busca
        input_frame = ctk.CTkFrame(self.tab_ia, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=5)

        self.entry_termo = ctk.CTkEntry(
            input_frame, 
            placeholder_text="Ex: Schedule, Deploy, Feedback, Standup...", 
            height=45, 
            font=ctk.CTkFont(size=15)
        )
        self.entry_termo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_termo.bind("<Return>", lambda event: self.iniciar_consulta_ia())

        self.btn_voz = ctk.CTkButton(
            input_frame, 
            text="🎙️ Falar", 
            height=45, 
            width=90, 
            fg_color="#8B5CF6",
            hover_color="#7C3AED",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.ouvir_microfone
        )
        self.btn_voz.pack(side="left", padx=(0, 10))

        self.btn_consultar = ctk.CTkButton(
            input_frame, 
            text="⚡ Abrasileirar", 
            height=45, 
            width=140, 
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.iniciar_consulta_ia
        )
        self.btn_consultar.pack(side="right")

        # Label de Status / Spinner
        self.lbl_status_ia = ctk.CTkLabel(self.tab_ia, text="", font=ctk.CTkFont(size=13))
        self.lbl_status_ia.pack(pady=5)

        # Card de Resultado
        self.card_resultado = ctk.CTkFrame(self.tab_ia, corner_radius=12, border_width=1, border_color="#3B82F6")
        self.card_resultado.pack(fill="both", expand=True, padx=20, pady=10)

        # Conteúdo interno do Card
        self.lbl_res_termo = self.criar_campo_texto_selecionavel(
            self.card_resultado, texto="---", font_size=20, font_weight="bold", text_color="#60A5FA", max_height=45
        )
        self.lbl_res_termo.pack(fill="x", padx=16, pady=(12, 2))

        self.lbl_res_traducao = self.criar_campo_texto_selecionavel(
            self.card_resultado, texto="Aguardando consulta...", font_size=15, text_color="#E2E8F0", max_height=45
        )
        self.lbl_res_traducao.pack(fill="x", padx=16, pady=2)

        # Badge de Pronúncia Abrasileirada & Macete da Língua
        self.frame_pronuncia = ctk.CTkFrame(self.card_resultado, fg_color="#1E293B", corner_radius=8)
        self.frame_pronuncia.pack(anchor="w", padx=16, pady=8, fill="x")

        lbl_tit_pron = ctk.CTkLabel(self.frame_pronuncia, text="🗣️ PRONÚNCIA ABRASILEIRADA & MACETE DA LÍNGUA/BOCA:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8")
        lbl_tit_pron.pack(anchor="w", padx=12, pady=(6, 0))

        self.lbl_res_pronuncia = self.criar_campo_texto_selecionavel(
            self.frame_pronuncia, texto="---", font_size=18, font_weight="bold", text_color="#F59E0B", fg_color="#1E293B", max_height=45
        )
        self.lbl_res_pronuncia.pack(fill="x", padx=8, pady=(0, 2))

        self.lbl_res_dica = self.criar_campo_texto_selecionavel(
            self.frame_pronuncia, texto="---", font_size=13, font_weight="bold", text_color="#C084FC", fg_color="#1E293B", max_height=60
        )
        self.lbl_res_dica.pack(fill="x", padx=8, pady=(0, 6))

        # Contexto de Trabalho
        lbl_tit_ex = ctk.CTkLabel(self.card_resultado, text="💼 EXEMPLO NO TRABALHO:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8")
        lbl_tit_ex.pack(anchor="w", padx=16, pady=(8, 0))

        self.lbl_res_exemplo = self.criar_campo_texto_selecionavel(
            self.card_resultado, texto="---", font_size=14, text_color="#F1F5F9", max_height=70
        )
        self.lbl_res_exemplo.pack(fill="x", padx=16, pady=2)

        self.lbl_res_trad_exemplo = self.criar_campo_texto_selecionavel(
            self.card_resultado, texto="---", font_size=13, text_color="#A1A1AA", max_height=70
        )
        self.lbl_res_trad_exemplo.pack(fill="x", padx=16, pady=(2, 10))

        # Rodapé do Card (Botões de Ação)
        frame_acoes = ctk.CTkFrame(self.card_resultado, fg_color="transparent")
        frame_acoes.pack(anchor="e", padx=20, pady=(0, 15))

        self.btn_ouvir = ctk.CTkButton(
            frame_acoes, 
            text="🔊 Ouvir Pronúncia", 
            fg_color="#374151", 
            hover_color="#4B5563",
            width=140,
            command=self.ouvir_pronuncia_atual
        )
        self.btn_ouvir.pack(side="left", padx=(0, 10))

        self.btn_copiar_ia = ctk.CTkButton(
            frame_acoes, 
            text="📋 Copiar Resultado", 
            fg_color="#374151", 
            hover_color="#4B5563",
            width=140,
            command=self.copiar_resultado_ia
        )
        self.btn_copiar_ia.pack(side="left", padx=(0, 10))

        self.btn_salvar = ctk.CTkButton(
            frame_acoes, 
            text="💾 Salvar no Meu Caderno", 
            fg_color="#16A34A", 
            hover_color="#15803D",
            width=180,
            font=ctk.CTkFont(weight="bold"),
            command=self.salvar_resultado_no_banco
        )
        self.btn_salvar.pack(side="left")

    def copiar_resultado_ia(self):
        if not self.resultado_atual_ia:
            messagebox.showinfo("Aviso", "Nenhum resultado para copiar no momento.")
            return

        res = self.resultado_atual_ia
        termo = res.get("termo_ingles", "")
        trad = res.get("traducao_portugues", "")
        pron = res.get("pronuncia_abrasileirada", "")
        ex = res.get("exemplo_frase_ingles", "")
        ex_trad = res.get("exemplo_traducao_portugues", "")

        texto_copia = f"Termo (EN): {termo}\nTradução: {trad}\nPronúncia Abrasileirada: {pron}\n\nExemplo: {ex}\nTradução Exemplo: {ex_trad}"
        self.copiar_para_area_transferencia(texto_copia, "Resultado da Consulta")

    def ouvir_microfone(self):
        """Inicia a escuta do microfone em uma thread separada."""
        self.btn_voz.configure(state="disabled")
        self.lbl_status_ia.configure(text="🎙️ Preparando microfone... Fale em inglês ou português.", text_color="#8B5CF6")
        threading.Thread(target=self._worker_ouvir_microfone, daemon=True).start()

    def _worker_ouvir_microfone(self):
        self.after(0, lambda: self.lbl_status_ia.configure(text="🎙️ Ouvindo... Fale agora em inglês ou português!", text_color="#3B82F6"))
        res = audio_engine.ouvir_microfone(idioma="auto", timeout_escrita=7)
        if res.get("sucesso"):
            texto = res.get("texto", "").strip()
            self.after(0, lambda: self._sucesso_transcricao_voz(texto))
        else:
            erro = res.get("erro", "Não entendi o áudio falado. Tente novamente.")
            self.after(0, lambda: self._falha_transcricao_voz(erro))

    def _sucesso_transcricao_voz(self, texto):
        self.btn_voz.configure(state="normal")
        self.entry_termo.delete(0, "end")
        self.entry_termo.insert(0, texto)
        self.lbl_status_ia.configure(text=f"🎙️ Voz reconhecida: '{texto}'! Pesquisando...", text_color="#10B981")
        self.iniciar_consulta_ia()

    def _falha_transcricao_voz(self, msg):
        self.btn_voz.configure(state="normal")
        self.lbl_status_ia.configure(text=f"⚠️ {msg}", text_color="#EF4444")

    def iniciar_consulta_ia(self):
        termo = self.entry_termo.get().strip()
        if not termo:
            messagebox.showwarning("Aviso", "Digite um termo ou frase em inglês para consultar.")
            return

        self.btn_consultar.configure(state="disabled")
        self.lbl_status_ia.configure(text="⏳ Consultando a IA no OpenRouter... Aguarde.", text_color="#F59E0B")

        # Executa em Thread separada para a UI não travar
        threading.Thread(target=self._worker_consultar_ia, args=(termo,), daemon=True).start()

    def _worker_consultar_ia(self, termo):
        resultado = consultar_openrouter(termo)
        self.after(0, lambda: self._atualizar_ui_resultado_ia(resultado))

    def _set_tb_text(self, tb_widget, text: str):
        if hasattr(tb_widget, "delete") and hasattr(tb_widget, "insert"):
            tb_widget.delete("1.0", "end")
            tb_widget.insert("1.0", text)
        elif hasattr(tb_widget, "configure"):
            tb_widget.configure(text=text)

    def _atualizar_ui_resultado_ia(self, resultado):
        self.btn_consultar.configure(state="normal")

        if not resultado["sucesso"]:
            self.lbl_status_ia.configure(text="❌ Erro na consulta.", text_color="#EF4444")
            messagebox.showerror("Erro na API", resultado["erro"])
            return

        dados = resultado["dados"]
        self.resultado_atual_ia = dados

        self.lbl_status_ia.configure(text=f"✅ Sucesso! Resposta gerada via {resultado.get('modelo_usado', 'IA')}", text_color="#10B981")
        
        self._set_tb_text(self.lbl_res_termo, dados.get("termo_ingles", "---"))
        self._set_tb_text(self.lbl_res_traducao, f"Tradução: {dados.get('traducao', '---')}")
        self._set_tb_text(self.lbl_res_pronuncia, f'"{dados.get("pronuncia_abrasileirada", "---")}"')
        
        dica = dados.get("dica_articulacao", "").strip()
        if dica:
            self._set_tb_text(self.lbl_res_dica, f'👅 Macete: {dica}')
        else:
            self._set_tb_text(self.lbl_res_dica, '👅 Macete: Encoste suavemente a boca/língua e solte o ar.')

        self._set_tb_text(self.lbl_res_exemplo, f'"{dados.get("exemplo_contexto", "---")}"')
        self._set_tb_text(self.lbl_res_trad_exemplo, f'→ {dados.get("traducao_exemplo", "---")}')

    def salvar_resultado_no_banco(self):
        if not self.resultado_atual_ia:
            messagebox.showwarning("Aviso", "Consulte um termo primeiro antes de salvar.")
            return

        d = self.resultado_atual_ia
        sucesso = salvar_termo(
            termo_ingles=d.get("termo_ingles", ""),
            traducao=d.get("traducao", ""),
            pronuncia_abrasileirada=d.get("pronuncia_abrasileirada", ""),
            exemplo_contexto=d.get("exemplo_contexto", ""),
            traducao_exemplo=d.get("traducao_exemplo", "")
        )

        if sucesso:
            messagebox.showinfo("Sucesso", f"'{d.get('termo_ingles')}' foi salvo com sucesso no seu caderno!")
            self.carregar_caderno()  # Atualiza a lista da Aba Caderno
        else:
            messagebox.showerror("Erro", "Não foi possível salvar o termo no banco de dados.")

    def ouvir_pronuncia_atual(self):
        if not self.resultado_atual_ia:
            termo = self.entry_termo.get().strip()
        else:
            termo = self.resultado_atual_ia.get("termo_ingles", self.entry_termo.get().strip())

        if not termo:
            messagebox.showwarning("Aviso", "Nenhum termo disponível para pronunciar.")
            return

        threading.Thread(target=self._worker_tocar_audio, args=(termo,), daemon=True).start()

    def _worker_tocar_audio(self, texto):
        audio_engine.falar(texto_pt="", termo_en=texto)


    # ==========================================
    # 📖 ABA 2: MEU CADERNO DE ESTUDOS
    # ==========================================
    def build_tab_caderno(self):
        header_frame = ctk.CTkFrame(self.tab_caderno, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        lbl_titulo = ctk.CTkLabel(header_frame, text="Seu Vocabulário Salvo", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(side="left")

        self.lbl_stats = ctk.CTkLabel(header_frame, text="Total: 0 termos", font=ctk.CTkFont(size=14), text_color="#A1A1AA")
        self.lbl_stats.pack(side="right")

        # Barra de Busca e Ações
        bar_frame = ctk.CTkFrame(self.tab_caderno, fg_color="transparent")
        bar_frame.pack(fill="x", padx=20, pady=5)

        self.entry_busca = ctk.CTkEntry(bar_frame, placeholder_text="🔍 Filtrar por palavra, tradução ou pronúncia...", height=38)
        self.entry_busca.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_busca.bind("<KeyRelease>", lambda e: self.carregar_caderno())

        btn_exportar = ctk.CTkButton(bar_frame, text="📥 Exportar CSV", width=130, height=38, command=self.exportar_caderno_csv)
        btn_exportar.pack(side="right")

        # Lista Scrollável de Termos
        self.scroll_caderno = ctk.CTkScrollableFrame(self.tab_caderno, corner_radius=10)
        self.scroll_caderno.pack(fill="both", expand=True, padx=20, pady=10)

        # Carrega dados iniciais
        self.carregar_caderno()

    def carregar_caderno(self):
        # Limpa widgets existentes
        for child in self.scroll_caderno.winfo_children():
            child.destroy()

        termo_busca = self.entry_busca.get()
        termos = listar_termos(termo_busca)

        # Atualiza contagem
        stats = obter_estatisticas()
        self.lbl_stats.configure(text=f"Total: {stats['total_termos']} termo(s)")

        if not termos:
            lbl_vazio = ctk.CTkLabel(
                self.scroll_caderno, 
                text="Nenhum termo encontrado no caderno. Consulte termos na Aba 1 e salve-os aqui!",
                text_color="gray",
                font=ctk.CTkFont(size=14)
            )
            lbl_vazio.pack(pady=40)
            return

        for t in termos:
            item_frame = ctk.CTkFrame(self.scroll_caderno, corner_radius=8, fg_color="#1E293B")
            item_frame.pack(fill="x", pady=6, padx=5)

            # Cabeçalho do Card
            top_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            top_frame.pack(fill="x", padx=12, pady=(10, 2))

            lbl_t_ingles = ctk.CTkLabel(top_frame, text=t["termo_ingles"], font=ctk.CTkFont(size=16, weight="bold"), text_color="#60A5FA")
            lbl_t_ingles.pack(side="left")

            lbl_pron = ctk.CTkLabel(top_frame, text=f'"{t["pronuncia_abrasileirada"]}"', font=ctk.CTkFont(size=14, weight="bold"), text_color="#F59E0B")
            lbl_pron.pack(side="left", padx=15)

            # Botões de Ação do Item
            btn_del = ctk.CTkButton(
                top_frame, 
                text="🗑️", 
                width=30, 
                height=30, 
                fg_color="#EF4444", 
                hover_color="#DC2626",
                command=lambda id_termo=t["id"]: self.excluir_termo_caderno(id_termo)
            )
            btn_del.pack(side="right")

            btn_som = ctk.CTkButton(
                top_frame, 
                text="🔊", 
                width=30, 
                height=30, 
                fg_color="#374151", 
                hover_color="#4B5563",
                command=lambda txt=t["termo_ingles"]: threading.Thread(target=self._worker_tocar_audio, args=(txt,), daemon=True).start()
            )
            btn_som.pack(side="right", padx=5)

            # Tradução e Exemplo
            lbl_trad = ctk.CTkLabel(item_frame, text=f"Tradução: {t['traducao']}", font=ctk.CTkFont(size=13))
            lbl_trad.pack(anchor="w", padx=12, pady=2)

            if t.get("exemplo_contexto"):
                lbl_ex = ctk.CTkLabel(item_frame, text=f"Contexto: {t['exemplo_contexto']} → {t.get('traducao_exemplo', '')}", font=ctk.CTkFont(size=12, slant="italic"), text_color="#94A3B8")
                lbl_ex.pack(anchor="w", padx=12, pady=(2, 10))

    def excluir_termo_caderno(self, id_termo):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este termo do caderno?"):
            if deletar_termo(id_termo):
                self.carregar_caderno()

    def exportar_caderno_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivos CSV", "*.csv")],
            title="Salvar Caderno de Estudos"
        )
        if filepath:
            if exportar_csv(filepath):
                messagebox.showinfo("Exportação Concluída", f"Seu caderno foi exportado com sucesso para:\n{filepath}")
            else:
                messagebox.showerror("Erro", "Ocorreu uma falha ao exportar para CSV.")


    # ==========================================
    # 📚 ABA 3: DECKS DE ESTUDO & MATERIAIS (PDFs)
    # ==========================================
    def build_tab_docs(self):
        header = ctk.CTkLabel(self.tab_docs, text="📚 Decks de Estudo & Materiais de Apoio", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(anchor="w", padx=20, pady=(15, 5))

        subtitle = ctk.CTkLabel(self.tab_docs, text="Consulte o conteúdo dos PDFs da pasta 'docs/' diretamente no app sem precisar abrir arquivos externos.", text_color="gray")
        subtitle.pack(anchor="w", padx=20, pady=(0, 10))

        # Frame de Controles / Seleção e Busca
        ctrl_frame = ctk.CTkFrame(self.tab_docs, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=5)

        lbl_deck = ctk.CTkLabel(ctrl_frame, text="Selecione o Deck:", font=ctk.CTkFont(weight="bold"))
        lbl_deck.pack(side="left", padx=(0, 10))

        self.combo_docs = ctk.CTkComboBox(
            ctrl_frame,
            values=["Carregando decks..."],
            width=320,
            command=self.ao_selecionar_doc_combo
        )
        self.combo_docs.pack(side="left", padx=(0, 15))

        self.entry_busca_docs = ctk.CTkEntry(
            ctrl_frame,
            placeholder_text="Buscar termo em todos os decks...",
            width=220
        )
        self.entry_busca_docs.pack(side="left", padx=(0, 10))
        self.entry_busca_docs.bind("<Return>", lambda event: self.pesquisar_nos_docs_ui())

        self.btn_buscar_docs = ctk.CTkButton(
            ctrl_frame,
            text="🔍 Pesquisar",
            width=110,
            command=self.pesquisar_nos_docs_ui
        )
        self.btn_buscar_docs.pack(side="left")

        # Frame de Ações Rápidas com Texto Selecionado
        act_frame = ctk.CTkFrame(self.tab_docs, fg_color="transparent")
        act_frame.pack(fill="x", padx=20, pady=(5, 5))

        lbl_dica = ctk.CTkLabel(act_frame, text="💡 Selecione um termo no texto abaixo:", text_color="#94A3B8", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_dica.pack(side="left", padx=(0, 10))

        btn_enviar_ia = ctk.CTkButton(
            act_frame,
            text="⚡ Abrasileirar Seleção na IA",
            fg_color="#8B5CF6",
            hover_color="#7C3AED",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.enviar_selecao_para_ia
        )
        btn_enviar_ia.pack(side="left", padx=(0, 10))

        btn_salvar_cad = ctk.CTkButton(
            act_frame,
            text="💾 Salvar Seleção no Caderno",
            fg_color="#10B981",
            hover_color="#059669",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.salvar_selecao_no_caderno
        )
        btn_salvar_cad.pack(side="left")

        # Status Label
        self.lbl_status_doc = ctk.CTkLabel(self.tab_docs, text="", font=ctk.CTkFont(size=12), text_color="#60A5FA")
        self.lbl_status_doc.pack(anchor="w", padx=20, pady=(2, 2))

        # Área de Texto do Documento
        self.textbox_pdf = ctk.CTkTextbox(
            self.tab_docs,
            wrap="word",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            corner_radius=8
        )
        self.textbox_pdf.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Carrega lista inicial de documentos
        self.carregar_lista_docs_ui()

    def carregar_lista_docs_ui(self):
        self.lista_documentos = listar_documentos()
        if self.lista_documentos:
            titulos = [d["titulo"] for d in self.lista_documentos]
            self.combo_docs.configure(values=titulos)
            self.combo_docs.set(titulos[0])
            self.ao_selecionar_doc_combo(titulos[0])
        else:
            self.combo_docs.configure(values=["Nenhum PDF encontrado em docs/"])
            self.combo_docs.set("Nenhum PDF encontrado em docs/")
            self.textbox_pdf.delete("1.0", "end")
            self.textbox_pdf.insert("1.0", "Nenhum arquivo PDF foi encontrado na pasta 'docs/'. Adicione seus PDFs nessa pasta para que apareçam aqui.")

    def ao_selecionar_doc_combo(self, titulo_selecionado):
        doc_encontrado = None
        for doc in self.lista_documentos:
            if doc["titulo"] == titulo_selecionado:
                doc_encontrado = doc
                break
        
        if not doc_encontrado:
            return

        self.doc_atual = doc_encontrado
        self.lbl_status_doc.configure(text=f"📖 Carregando '{doc_encontrado['filename']}'...")
        self.update_idletasks()

        res = ler_pdf(doc_encontrado["filepath"])
        self.textbox_pdf.delete("1.0", "end")
        if res["sucesso"]:
            header_text = f"=========================================\n  📚 {doc_encontrado['titulo'].upper()}\n  📄 Total de Páginas: {res['total_paginas']} | Arquivo: {doc_encontrado['filename']}\n=========================================\n\n"
            self.textbox_pdf.insert("1.0", header_text + res["texto_completo"])
            self.lbl_status_doc.configure(text=f"Exibindo: {doc_encontrado['titulo']} ({res['total_paginas']} páginas)")
        else:
            self.textbox_pdf.insert("1.0", f"Erro ao ler PDF: {res.get('erro')}")
            self.lbl_status_doc.configure(text=f"Erro ao carregar documento.")

    def pesquisar_nos_docs_ui(self):
        termo = self.entry_busca_docs.get().strip()
        if not termo:
            if self.combo_docs.get():
                self.ao_selecionar_doc_combo(self.combo_docs.get())
            return
        
        self.lbl_status_doc.configure(text=f"🔍 Pesquisando por '{termo}' em todos os PDFs...")
        self.update_idletasks()
        
        resultados = buscar_nos_documentos(termo)
        self.textbox_pdf.delete("1.0", "end")
        
        if not resultados:
            self.textbox_pdf.insert("1.0", f"Nenhum resultado encontrado para o termo '{termo}' nos documentos PDF.")
            self.lbl_status_doc.configure(text=f"Pesquisa concluída: 0 ocorrências.")
            return

        texto_out = f"🔍 RESULTADOS DA BUSCA POR: '{termo.upper()}' ({len(resultados)} decks encontrados)\n"
        texto_out += "=" * 60 + "\n\n"

        for item in resultados:
            texto_out += f"📘 {item['titulo']} ({item['filename']})\n"
            for m in item["matches"]:
                texto_out += f"   • Página {m['pagina']}: {m['trecho']}\n"
            texto_out += "-" * 60 + "\n\n"

        self.textbox_pdf.insert("1.0", texto_out)
        self.lbl_status_doc.configure(text=f"Pesquisa concluída: {len(resultados)} decks encontrados com '{termo}'.")

    def obter_texto_selecionado_pdf(self):
        try:
            texto_sel = self.textbox_pdf.get("sel.first", "sel.last").strip()
            return texto_sel
        except Exception:
            return ""

    def enviar_selecao_para_ia(self):
        texto_sel = self.obter_texto_selecionado_pdf()
        if not texto_sel:
            messagebox.showwarning("Seleção Vazia", "Por favor, selecione um texto/palavra com o mouse dentro do leitor antes de clicar.")
            return
        
        # Muda para a aba Consultar IA
        self.tabview.set("🔎 Consultar IA")
        self.entry_termo.delete(0, "end")
        self.entry_termo.insert(0, texto_sel)
        self.iniciar_consulta_ia()

    def salvar_selecao_no_caderno(self):
        texto_sel = self.obter_texto_selecionado_pdf()
        if not texto_sel:
            messagebox.showwarning("Seleção Vazia", "Por favor, selecione um texto/palavra com o mouse dentro do leitor antes de clicar.")
            return
        
        origem = self.doc_atual['titulo'] if self.doc_atual else 'PDF'
        if salvar_termo(
            termo_ingles=texto_sel,
            traducao="Adicionado via Deck PDF",
            pronuncia_abrasileirada="---",
            exemplo_contexto=f"Origem: {origem}",
            traducao_exemplo=""
        ):
            messagebox.showinfo("Sucesso", f"O termo '{texto_sel}' foi salvo no seu Caderno de Estudos!")
            self.carregar_caderno()
        else:
            messagebox.showerror("Erro", "Não foi possível salvar no banco de dados.")


    # ==========================================
    # ⏱️ ABA 4: TIMER POMODORO
    # ==========================================
    def build_tab_pomodoro(self):
        lbl_titulo = ctk.CTkLabel(self.tab_pomodoro, text="Timer Pomodoro de Estudos", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(pady=(20, 5))

        lbl_desc = ctk.CTkLabel(self.tab_pomodoro, text="Mantenha o foco diário estudando em blocos de tempo sem distrações.", text_color="gray")
        lbl_desc.pack(pady=(0, 20))

        # Seleção de Modo
        mode_frame = ctk.CTkFrame(self.tab_pomodoro, fg_color="transparent")
        mode_frame.pack(pady=10)

        self.btn_foco = ctk.CTkButton(mode_frame, text="🎯 Foco (30 min)", command=lambda: self.set_pomodoro_modo(30), width=140)
        self.btn_foco.pack(side="left", padx=5)

        self.btn_pausa = ctk.CTkButton(mode_frame, text="☕ Pausa (5 min)", command=lambda: self.set_pomodoro_modo(5), fg_color="#475569", width=140)
        self.btn_pausa.pack(side="left", padx=5)

        # Display do Relógio
        self.lbl_clock = ctk.CTkLabel(self.tab_pomodoro, text="30:00", font=ctk.CTkFont(size=72, weight="bold"), text_color="#60A5FA")
        self.lbl_clock.pack(pady=20)

        # Barra de Progresso
        self.progress_pomodoro = ctk.CTkProgressBar(self.tab_pomodoro, width=400, height=14)
        self.progress_pomodoro.set(1.0)
        self.progress_pomodoro.pack(pady=10)

        # Botões do Timer
        ctrl_frame = ctk.CTkFrame(self.tab_pomodoro, fg_color="transparent")
        ctrl_frame.pack(pady=20)

        self.btn_pomo_start = ctk.CTkButton(
            ctrl_frame, 
            text="▶ Iniciar", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            fg_color="#16A34A", 
            hover_color="#15803D",
            width=130, 
            height=45,
            command=self.iniciar_pomodoro
        )
        self.btn_pomo_start.pack(side="left", padx=10)

        self.btn_pomo_pause = ctk.CTkButton(
            ctrl_frame, 
            text="⏸ Pausar", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            fg_color="#D97706", 
            hover_color="#B45309",
            width=130, 
            height=45,
            command=self.pausar_pomodoro
        )
        self.btn_pomo_pause.pack(side="left", padx=10)

        self.btn_pomo_reset = ctk.CTkButton(
            ctrl_frame, 
            text="🔄 Reiniciar", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            fg_color="#4B5563", 
            hover_color="#374151",
            width=130, 
            height=45,
            command=self.resetar_pomodoro
        )
        self.btn_pomo_reset.pack(side="left", padx=10)

    def set_pomodoro_modo(self, minutos):
        self.pausar_pomodoro()
        self.pomodoro_tempo_total = minutos * 60
        self.pomodoro_tempo_restante = self.pomodoro_tempo_total
        self.atualizar_display_pomodoro()

        if minutos == 30:
            self.btn_foco.configure(fg_color="#3B82F6")
            self.btn_pausa.configure(fg_color="#475569")
        else:
            self.btn_foco.configure(fg_color="#475569")
            self.btn_pausa.configure(fg_color="#3B82F6")

    def atualizar_display_pomodoro(self):
        mins = self.pomodoro_tempo_restante // 60
        secs = self.pomodoro_tempo_restante % 60
        self.lbl_clock.configure(text=f"{mins:02d}:{secs:02d}")
        
        pct = self.pomodoro_tempo_restante / self.pomodoro_tempo_total if self.pomodoro_tempo_total > 0 else 0
        self.progress_pomodoro.set(pct)

    def iniciar_pomodoro(self):
        if not self.pomodoro_rodando:
            self.pomodoro_rodando = True
            self.loop_pomodoro()

    def pausar_pomodoro(self):
        self.pomodoro_rodando = False
        if self.pomodoro_timer_id:
            self.after_cancel(self.pomodoro_timer_id)
            self.pomodoro_timer_id = None

    def resetar_pomodoro(self):
        self.pausar_pomodoro()
        self.pomodoro_tempo_restante = self.pomodoro_tempo_total
        self.atualizar_display_pomodoro()

    def loop_pomodoro(self):
        if self.pomodoro_rodando and self.pomodoro_tempo_restante > 0:
            self.pomodoro_tempo_restante -= 1
            self.atualizar_display_pomodoro()
            self.pomodoro_timer_id = self.after(1000, self.loop_pomodoro)
        elif self.pomodoro_tempo_restante == 0:
            self.pomodoro_rodando = False
            messagebox.showinfo("Tempo Concluído! 🎉", "Parabéns! Você concluiu seu ciclo de estudos.")
            try:
                import winsound
                winsound.Beep(1000, 800)
            except Exception:
                pass


    # ==========================================
    # ⚙️ ABA 4: CONFIGURAÇÕES
    # ==========================================
    def build_tab_config(self):
        lbl_tit = ctk.CTkLabel(self.tab_config, text="Configurações da API & Sistema", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_tit.pack(anchor="w", padx=20, pady=(15, 5))

        lbl_sub = ctk.CTkLabel(self.tab_config, text="Gerencie sua API Key do OpenRouter e os modelos de IA utilizados.", text_color="gray")
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 20))

        # Form de Configuração
        form_frame = ctk.CTkFrame(self.tab_config, corner_radius=10)
        form_frame.pack(fill="x", padx=20, pady=10)

        # Campo API Key
        lbl_key = ctk.CTkLabel(form_frame, text="Chave de API do OpenRouter (API Key):", font=ctk.CTkFont(weight="bold"))
        lbl_key.pack(anchor="w", padx=15, pady=(15, 2))

        self.entry_api_key = ctk.CTkEntry(form_frame, placeholder_text="sk-or-v1-...", show="*", width=500, height=38)
        self.entry_api_key.pack(anchor="w", padx=15, pady=(0, 10))

        # Campo Modelo Padrão
        lbl_model = ctk.CTkLabel(form_frame, text="Modelo de IA Padrão (Gratuito):", font=ctk.CTkFont(weight="bold"))
        lbl_model.pack(anchor="w", padx=15, pady=(10, 2))

        self.combo_modelo = ctk.CTkComboBox(
            form_frame, 
            values=[
                "meta-llama/llama-3.3-70b-instruct:free",
                "google/gemini-2.0-flash-exp:free",
                "deepseek/deepseek-r1:free",
                "qwen/qwen-2.5-72b-instruct:free"
            ],
            width=500,
            height=38
        )
        self.combo_modelo.pack(anchor="w", padx=15, pady=(0, 20))

        # Botão Salvar Configurações
        btn_salvar_cfg = ctk.CTkButton(
            form_frame, 
            text="💾 Salvar Configurações", 
            font=ctk.CTkFont(weight="bold"), 
            height=40,
            width=200,
            command=self.salvar_configuracoes_ui
        )
        btn_salvar_cfg.pack(anchor="w", padx=15, pady=(0, 15))

        # Carrega dados salvos no formulário
        self.carregar_configuracoes_ui()

    def carregar_configuracoes_ui(self):
        cfg = load_config()
        if cfg.get("api_key"):
            self.entry_api_key.insert(0, cfg["api_key"])
        if cfg.get("model"):
            self.combo_modelo.set(cfg["model"])

    def salvar_configuracoes_ui(self):
        api_key = self.entry_api_key.get().strip()
        model = self.combo_modelo.get().strip()

        cfg = load_config()
        cfg["api_key"] = api_key
        cfg["model"] = model

        if save_config(cfg):
            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
        else:
            messagebox.showerror("Erro", "Não foi possível salvar as configurações.")

if __name__ == "__main__":
    app = LanguageBuddyApp()
    app.mainloop()
