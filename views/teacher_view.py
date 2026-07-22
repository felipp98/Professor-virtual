import customtkinter as ctk
import tkinter
import threading
from services.audio_service import audio_engine
from services.teacher_service import teacher_engine, TeacherService
from services.database import obter_perfil_aluno, salvar_perfil_aluno
from services.logger import logger

class TeacherView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.ultimo_pacote_professor = None
        self.build_ui()

    def build_ui(self):
        # Header / Status Card Topo
        top_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray17"), corner_radius=10)
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
        self.status_bar_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
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

        # Switch de Modo Conversa Viva (Hands-Free) estilo ChatGPT
        self.switch_conversa_viva = ctk.CTkSwitch(
            self.status_bar_frame,
            text="🔄 Conversa Viva",
            command=self._toggle_conversa_viva,
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color="#10b981"
        )
        self.switch_conversa_viva.pack(side="right", padx=(0, 10), pady=8)

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
        self.chat_scroll = ctk.CTkScrollableFrame(self, fg_color=("gray90", "#0f172a"), corner_radius=10)
        self.chat_scroll.pack(fill="both", expand=True, padx=15, pady=5)

        # Frame de Entrada de Texto e Botão de Voz na parte inferior
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
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

    def _toggle_conversa_viva(self):
        """Ativa ou desativa o modo de conversa contínua mãos-livres (estilo ChatGPT Voice)."""
        val = bool(self.switch_conversa_viva.get())
        audio_engine.conversa_viva_ativa = val
        if val:
            self.lbl_status_teacher.configure(text="🔄 Conversa Viva Ativa! Pode falar direto sem clicar no botão.", text_color="#10b981")
            if not audio_engine.is_speaking:
                self.ouvir_microfone_teacher()
        else:
            self.lbl_status_teacher.configure(text="⏸️ Conversa Viva pausada. Use o botão para falar.", text_color="gray")

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
        """Para qualquer áudio em reprodução e pausa a conversa viva se ativada."""
        audio_engine.parar_fala()
        if hasattr(self, "switch_conversa_viva") and self.switch_conversa_viva.get() == 1:
            self.switch_conversa_viva.deselect()
            audio_engine.conversa_viva_ativa = False
        self.lbl_status_teacher.configure(text="⏹️ Áudio e conversa contínua interrompidos.", text_color="gray")

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
            engine_info = res.get("engine", "")
            info_str = f" [{engine_info}]" if engine_info else ""
            self.lbl_status_teacher.configure(text=f"✅ Voz reconhecida{info_str}: '{texto}'", text_color="#10b981")
            self.enviar_mensagem_teacher(texto_aluno=texto)
        else:
            erro = res.get("erro", "Não entendi.")
            self.lbl_status_teacher.configure(text=f"⚠️ {erro}", text_color="#ef4444")
            
            if getattr(audio_engine, "conversa_viva_ativa", False):
                if "Nenhum áudio detectado" in erro:
                    self.after(1000, self.ouvir_microfone_teacher)
            else:
                audio_engine.falar(texto_pt="Desculpe, não consegui entender o que você disse no microfone. Pode repetir ou digitar por favor?")

    def enviar_mensagem_teacher(self, texto_aluno: str = None):
        if texto_aluno is None:
            texto_aluno = self.entry_teacher.get().strip()
            self.entry_teacher.delete(0, "end")

        if not texto_aluno:
            return

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
        traducao_pt = pacote.get("traducao_pt", "")
        pronuncia = pacote.get("pronuncia_abrasileirada", "")
        dica_articulacao = pacote.get("dica_articulacao", "")
        texto_chat = pacote.get("texto_chat", "")
        modo_resp = pacote.get("modo_resposta", "voz")
        instrucao = pacote.get("instrucao_aluno", "")

        self._adicionar_balao_chat("professor", texto_chat, fala_pt, termo_en, traducao_pt, pronuncia, instrucao, dica_articulacao)

        if modo_resp == "voz":
            if getattr(audio_engine, "conversa_viva_ativa", False):
                self.lbl_status_teacher.configure(text="🎙️ Conversa Viva Ativa: Ouve você automaticamente após a fala!", text_color="#10b981")
            else:
                self.lbl_status_teacher.configure(text="🎙️ Modo Voz: Responda usando o botão de microfone!", text_color="#10b981")
        else:
            self.lbl_status_teacher.configure(text="⌨️ Modo Texto: Digite sua resposta abaixo.", text_color="#38bdf8")

        def _ao_finalizar_audio_professor():
            self.lbl_status_teacher.configure(text="👂 Aguardando sua resposta...", text_color="#a855f7")
            if getattr(audio_engine, "conversa_viva_ativa", False) and not audio_engine.stop_requested:
                self.after(600, self.ouvir_microfone_teacher)

        if fala_pt:
            audio_engine.falar(
                texto_pt=fala_pt,
                termo_en=termo_en,
                pronuncia_abrasileirada=pronuncia,
                callback_fim=_ao_finalizar_audio_professor
            )
        else:
            if getattr(audio_engine, "conversa_viva_ativa", False):
                self.after(600, self.ouvir_microfone_teacher)

        self.after(50, self._rolar_chat_para_fim)
        self.after(200, self._rolar_chat_para_fim)

    def _rolar_chat_para_fim(self):
        """Garante que a barra de rolagem do chat vá para o final de forma suave."""
        try:
            self.update_idletasks()
            if hasattr(self, "chat_scroll") and hasattr(self.chat_scroll, "_parent_canvas") and self.chat_scroll._parent_canvas.winfo_exists():
                self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _adicionar_balao_chat(self, remetente: str, texto: str, fala_pt: str = "", termo_en: str = "", traducao_pt: str = "", pronuncia: str = "", instrucao: str = "", dica_articulacao: str = ""):
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

        tb_content = self.app.criar_campo_texto_selecionavel(
            card, 
            texto=texto, 
            font_size=14, 
            text_color="#f8fafc" if remetente == "professor" else "#ffffff", 
            fg_color=card_bg
        )
        tb_content.pack(fill="x", padx=8, pady=(0, 4))

        if remetente == "professor":
            if termo_en:
                tb_en = self.app.criar_campo_texto_selecionavel(
                    card, 
                    texto=f"🇺🇸 Termo em Inglês: {termo_en}", 
                    font_size=14, 
                    font_weight="bold", 
                    text_color="#38bdf8", 
                    fg_color=card_bg,
                    max_height=50
                )
                tb_en.pack(fill="x", padx=8, pady=(0, 2))

            if traducao_pt:
                tb_trad = self.app.criar_campo_texto_selecionavel(
                    card, 
                    texto=f"🇧🇷 Tradução em Português: {traducao_pt}", 
                    font_size=14, 
                    font_weight="bold", 
                    text_color="#10b981", 
                    fg_color=card_bg,
                    max_height=50
                )
                tb_trad.pack(fill="x", padx=8, pady=(0, 2))

            if pronuncia:
                tb_pron = self.app.criar_campo_texto_selecionavel(
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
                tb_dica = self.app.criar_campo_texto_selecionavel(
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

            texto_para_copiar = f"Termo: {termo_en}\nTradução: {traducao_pt}\nPronúncia: {pronuncia}\n\n{texto}" if termo_en else texto
            btn_copiar = ctk.CTkButton(
                btn_frame,
                text="📋 Copiar Tudo",
                width=90,
                height=26,
                fg_color="#475569",
                hover_color="#334155",
                font=ctk.CTkFont(size=11),
                command=lambda t=texto_para_copiar: self.app.copiar_para_area_transferencia(t, "Mensagem do Professor")
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
                command=lambda t=texto: self.app.copiar_para_area_transferencia(t, "Sua Mensagem")
            )
            btn_copiar_aluno.pack(side="right")

        self._rolar_chat_para_fim()
        self.after(50, self._rolar_chat_para_fim)
        self.after(150, self._rolar_chat_para_fim)
        self.after(300, self._rolar_chat_para_fim)
