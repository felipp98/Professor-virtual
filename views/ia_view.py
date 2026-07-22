import customtkinter as ctk
from tkinter import messagebox
import threading
from services.ai_service import consultar_openrouter
from services.audio_service import audio_engine
from services.database import salvar_termo
from services.logger import logger

class IAView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.resultado_atual_ia = None
        self.build_ui()

    def build_ui(self):
        # Título da seção
        header = ctk.CTkLabel(
            self, 
            text="Abrasileirar Pronúncia & Contexto de Trabalho", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(anchor="w", padx=20, pady=(15, 5))

        subtitle = ctk.CTkLabel(
            self, 
            text="Digite um termo em inglês para receber a tradução, pronúncia fonética abrasileirada e exemplo prático.", 
            text_color="gray"
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 15))

        # Frame de Busca
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
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
        self.lbl_status_ia = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13))
        self.lbl_status_ia.pack(pady=5)

        # Card de Resultado
        self.card_resultado = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color="#3B82F6")
        self.card_resultado.pack(fill="both", expand=True, padx=20, pady=10)

        # Conteúdo interno do Card
        self.lbl_res_termo = self.app.criar_campo_texto_selecionavel(
            self.card_resultado, texto="---", font_size=20, font_weight="bold", text_color="#60A5FA", max_height=45
        )
        self.lbl_res_termo.pack(fill="x", padx=16, pady=(12, 2))

        self.lbl_res_traducao = self.app.criar_campo_texto_selecionavel(
            self.card_resultado, texto="Aguardando consulta...", font_size=15, text_color="#E2E8F0", max_height=45
        )
        self.lbl_res_traducao.pack(fill="x", padx=16, pady=2)

        # Badge de Pronúncia Abrasileirada & Macete da Língua
        self.frame_pronuncia = ctk.CTkFrame(self.card_resultado, fg_color="#1E293B", corner_radius=8)
        self.frame_pronuncia.pack(anchor="w", padx=16, pady=8, fill="x")

        lbl_tit_pron = ctk.CTkLabel(self.frame_pronuncia, text="🗣️ PRONÚNCIA ABRASILEIRADA & MACETE DA LÍNGUA/BOCA:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8")
        lbl_tit_pron.pack(anchor="w", padx=12, pady=(6, 0))

        self.lbl_res_pronuncia = self.app.criar_campo_texto_selecionavel(
            self.frame_pronuncia, texto="---", font_size=18, font_weight="bold", text_color="#F59E0B", fg_color="#1E293B", max_height=45
        )
        self.lbl_res_pronuncia.pack(fill="x", padx=8, pady=(0, 2))

        self.lbl_res_dica = self.app.criar_campo_texto_selecionavel(
            self.frame_pronuncia, texto="---", font_size=13, font_weight="bold", text_color="#C084FC", fg_color="#1E293B", max_height=60
        )
        self.lbl_res_dica.pack(fill="x", padx=8, pady=(0, 6))

        # Contexto de Trabalho
        lbl_tit_ex = ctk.CTkLabel(self.card_resultado, text="💼 EXEMPLO NO TRABALHO:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8")
        lbl_tit_ex.pack(anchor="w", padx=16, pady=(8, 0))

        self.lbl_res_exemplo = self.app.criar_campo_texto_selecionavel(
            self.card_resultado, texto="---", font_size=14, text_color="#F1F5F9", max_height=70
        )
        self.lbl_res_exemplo.pack(fill="x", padx=16, pady=2)

        self.lbl_res_trad_exemplo = self.app.criar_campo_texto_selecionavel(
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
        trad = res.get("traducao", "")
        pron = res.get("pronuncia_abrasileirada", "")
        ex = res.get("exemplo_contexto", "")
        ex_trad = res.get("traducao_exemplo", "")

        texto_copia = f"Termo (EN): {termo}\nTradução: {trad}\nPronúncia Abrasileirada: {pron}\n\nExemplo: {ex}\nTradução Exemplo: {ex_trad}"
        self.app.copiar_para_area_transferencia(texto_copia, "Resultado da Consulta")

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

    def iniciar_consulta_ia(self, termo_override: str = None):
        termo = termo_override if termo_override is not None else self.entry_termo.get().strip()
        if not termo:
            messagebox.showwarning("Aviso", "Digite um termo ou frase em inglês para consultar.")
            return

        self.btn_consultar.configure(state="disabled")
        self.lbl_status_ia.configure(text="⏳ Consultando a IA no OpenRouter... Aguarde.", text_color="#F59E0B")

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
            if hasattr(self.app, "caderno_view"):
                self.app.caderno_view.carregar_caderno()
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
