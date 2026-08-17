import customtkinter as ctk
from tkinter import messagebox, simpledialog
import threading
from typing import Dict, Any, List

from services.listening_service import listening_service
from services.audio_service import audio_engine
from services.database import salvar_termo, registrar_progresso_aula
from services.logger import logger

ETAPAS = [
    {"num": 1, "titulo": "1. Escuta Cega", "desc": "Ouça o áudio em inglês sem ler o texto para medir sua percepção auditiva inicial."},
    {"num": 2, "titulo": "2. Áudio + Texto & PT", "desc": "Ouça o áudio acompanhando o texto em inglês e a tradução em português."},
    {"num": 3, "titulo": "3. Frase por Frase", "desc": "Analise cada frase detalhadamente com a pronúncia abrasileirada e dicas corporativas."},
    {"num": 4, "titulo": "4. Áudio + Texto EN", "desc": "Ouça o áudio acompanhando apenas o texto em inglês (sem tradução visual)."},
    {"num": 5, "titulo": "5. Prática de Pronúncia", "desc": "Grave sua voz repetindo as frases (Shadowing) e receba avaliação imediata da IA."},
    {"num": 6, "titulo": "6. Escuta Final", "desc": "Ouça novamente o áudio completo em inglês e meça sua evolução de compreensão."}
]

class AudioPracticeView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.etapa_atual = 1
        self.velocidade_audio = 1.0
        self.licao_atual: Dict[str, Any] = listening_service.listar_licoes()[0]
        self.gravando = False
        self.frase_selecionada_idx = 0

        self.build_ui()

    def build_ui(self):
        # 1. Barra Superior: Seleção de Lição & Velocidade & Criar com IA
        top_bar = ctk.CTkFrame(self, fg_color=("gray85", "#1e1e2e"), corner_radius=10)
        top_bar.pack(fill="x", padx=15, pady=(10, 5))

        lbl_topico = ctk.CTkLabel(top_bar, text="🎧 Treino:", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_topico.pack(side="left", padx=(15, 5), pady=10)

        # Opções de Lições
        self.opcoes_licoes = [l["titulo"] for l in listening_service.listar_licoes()]
        self.combo_licao = ctk.CTkOptionMenu(
            top_bar, 
            values=self.opcoes_licoes, 
            command=self._ao_selecionar_licao,
            width=260
        )
        self.combo_licao.pack(side="left", padx=5, pady=10)
        self.combo_licao.set(self.licao_atual["titulo"])

        # Botão Criar por IA
        btn_criar_ia = ctk.CTkButton(
            top_bar,
            text="✨ Nova Lição com IA",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self._gerar_licao_ia_dialog,
            width=160
        )
        btn_criar_ia.pack(side="left", padx=10, pady=10)

        # Velocidade do Áudio
        lbl_vel = ctk.CTkLabel(top_bar, text="⚡ Velocidade:", font=ctk.CTkFont(size=12))
        lbl_vel.pack(side="left", padx=(20, 5))

        combo_vel = ctk.CTkOptionMenu(
            top_bar,
            values=["1.0x", "1.25x", "1.5x"],
            command=self._alterar_velocidade,
            width=80
        )
        combo_vel.pack(side="left", padx=5)
        combo_vel.set("1.0x")

        # 2. Barra de Etapas (1 a 6)
        self.frame_etapas = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_etapas.pack(fill="x", padx=15, pady=5)
        self._renderizar_barra_etapas()

        # 3. Painel de Conteúdo Principal (Dinâmico conforme a etapa)
        self.frame_conteudo = ctk.CTkFrame(self, fg_color=("gray90", "#181825"), corner_radius=12)
        self.frame_conteudo.pack(fill="both", expand=True, padx=15, pady=5)

        # 4. Barra Inferior de Navegação entre Etapas (Anterior / Próximo)
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=15, pady=(5, 10))

        self.btn_anterior = ctk.CTkButton(
            bottom_bar, 
            text="◀️ Passo Anterior", 
            command=self._passo_anterior,
            fg_color="#4b5563",
            hover_color="#374151",
            width=140
        )
        self.btn_anterior.pack(side="left")

        self.lbl_instrucao_etapa = ctk.CTkLabel(
            bottom_bar, 
            text="", 
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#9ca3af"
        )
        self.lbl_instrucao_etapa.pack(side="left", fill="x", expand=True, padx=10)

        self.btn_proximo = ctk.CTkButton(
            bottom_bar, 
            text="Próximo Passo ▶️", 
            command=self._proximo_passo,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=140
        )
        self.btn_proximo.pack(side="right")

        # Renderiza a primeira etapa
        self.carregar_etapa()

    def _renderizar_barra_etapas(self):
        for child in self.frame_etapas.winfo_children():
            child.destroy()

        for step in ETAPAS:
            num = step["num"]
            ativo = (num == self.etapa_atual)
            concluido = (num < self.etapa_atual)

            bg_col = "#2563eb" if ativo else ("#10b981" if concluido else "#374151")
            txt_col = "white"

            btn_step = ctk.CTkButton(
                self.frame_etapas,
                text=f"{num}. {step['titulo'].split('.')[1].strip()}",
                fg_color=bg_col,
                text_color=txt_col,
                hover_color="#3b82f6" if not ativo else "#2563eb",
                height=32,
                font=ctk.CTkFont(size=11, weight="bold" if ativo else "normal"),
                command=lambda n=num: self._ir_para_etapa(n)
            )
            btn_step.pack(side="left", fill="x", expand=True, padx=2)

    def _ir_para_etapa(self, num_etapa: int):
        audio_engine.parar()
        self.etapa_atual = num_etapa
        self._renderizar_barra_etapas()
        self.carregar_etapa()

    def _passo_anterior(self):
        if self.etapa_atual > 1:
            self._ir_para_etapa(self.etapa_atual - 1)

    def _proximo_passo(self):
        if self.etapa_atual < 6:
            self._ir_para_etapa(self.etapa_atual + 1)

    def _alterar_velocidade(self, valor_str: str):
        try:
            self.velocidade_audio = float(valor_str.replace("x", ""))
        except Exception:
            self.velocidade_audio = 1.0

    def _ao_selecionar_licao(self, titulo_selecionado: str):
        for l in listening_service.listar_licoes():
            if l["titulo"] == titulo_selecionado:
                self.licao_atual = l
                break
        self._ir_para_etapa(1)

    def _gerar_licao_ia_dialog(self):
        topico = simpledialog.askstring(
            "Nova Lição com IA",
            "Digite o tema técnico/profissional em inglês ou português:\n(Ex: Code Deploy Failure, Salary Negotiation, Client Demo)",
            parent=self
        )
        if topico and topico.strip():
            # Mostra mensagem de carregamento
            lbl_carregando = ctk.CTkLabel(
                self.frame_conteudo, 
                text="⏳ Criando nova lição customizada com a IA... Aguarde alguns segundos.",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#3b82f6"
            )
            lbl_carregando.pack(pady=50)

            def _thread_ia():
                res = listening_service.gerar_licao_com_ia(topico.strip())
                if res.get("sucesso"):
                    nova_licao = res["licao"]
                    self.licao_atual = nova_licao
                    self.opcoes_licoes = [l["titulo"] for l in listening_service.listar_licoes()]
                    self.combo_licao.configure(values=self.opcoes_licoes)
                    self.combo_licao.set(nova_licao["titulo"])
                    self._ir_para_etapa(1)
                else:
                    messagebox.showerror("Erro ao Gerar Lição", res.get("erro", "Erro desconhecido."))
                    self.carregar_etapa()

            threading.Thread(target=_thread_ia, daemon=True).start()

    def carregar_etapa(self):
        # Limpa o conteúdo do painel principal
        for child in self.frame_conteudo.winfo_children():
            child.destroy()

        # Atualiza texto de instrução no rodape
        info_etapa = ETAPAS[self.etapa_atual - 1]
        self.lbl_instrucao_etapa.configure(text=f"💡 {info_etapa['desc']}")

        # Atualiza botões de navegação
        self.btn_anterior.configure(state="normal" if self.etapa_atual > 1 else "disabled")
        if self.etapa_atual == 6:
            self.btn_proximo.configure(text="🎉 Finalizar", fg_color="#10b981", hover_color="#059669")
        else:
            self.btn_proximo.configure(text="Próximo Passo ▶️", fg_color="#2563eb", hover_color="#1d4ed8")

        # Chama a função de renderização da etapa específica
        if self.etapa_atual == 1:
            self._render_etapa1_blind_listening()
        elif self.etapa_atual == 2:
            self._render_etapa2_audio_texto_pt()
        elif self.etapa_atual == 3:
            self._render_etapa3_frase_por_frase()
        elif self.etapa_atual == 4:
            self._render_etapa4_audio_texto_en()
        elif self.etapa_atual == 5:
            self._render_etapa5_pratica_pronuncia()
        elif self.etapa_atual == 6:
            self._render_etapa6_escuta_final()

    # --- ETAPA 1: Blind Listening (Apenas Áudio) ---
    def _render_etapa1_blind_listening(self):
        lbl_header = ctk.CTkLabel(
            self.frame_conteudo,
            text=f"Etapa 1: Escuta Cega (Blind Listening)\n{self.licao_atual['titulo']}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_header.pack(pady=(25, 10))

        lbl_inst = ctk.CTkLabel(
            self.frame_conteudo,
            text="🎧 Feche os olhos ou apenas escute atentamente ao áudio abaixo.\nNão leia nada ainda. O objetivo é testar quanto você entende naturalmente de primeira.",
            font=ctk.CTkFont(size=13),
            text_color="#a1a1aa",
            justify="center"
        )
        lbl_inst.pack(pady=10)

        card_audio = ctk.CTkFrame(self.frame_conteudo, fg_color=("gray85", "#27272a"), corner_radius=12)
        card_audio.pack(padx=30, pady=20, fill="x")

        btn_play = ctk.CTkButton(
            card_audio,
            text="🔊 Tocar Áudio Completo em Inglês",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=50,
            command=self._tocar_audio_completo
        )
        btn_play.pack(padx=20, pady=20)

    # --- ETAPA 2: Áudio + Texto EN + Tradução PT ---
    def _render_etapa2_audio_texto_pt(self):
        lbl_header = ctk.CTkLabel(
            self.frame_conteudo,
            text="Etapa 2: Áudio com Texto e Tradução em Português",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_header.pack(pady=(15, 5))

        top_btns = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        top_btns.pack(pady=5)

        btn_play = ctk.CTkButton(
            top_btns,
            text="🔊 Ouvir Áudio Completo",
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            command=self._tocar_audio_completo
        )
        btn_play.pack(side="left", padx=5)

        btn_copiar_en = ctk.CTkButton(
            top_btns,
            text="📋 Copiar Texto EN",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            height=38,
            command=lambda: self.app.copiar_para_area_transferencia(self.licao_atual["texto_en"], "Texto em Inglês")
        )
        btn_copiar_en.pack(side="left", padx=5)

        btn_copiar_pt = ctk.CTkButton(
            top_btns,
            text="📋 Copiar Tradução PT",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            height=38,
            command=lambda: self.app.copiar_para_area_transferencia(self.licao_atual["texto_pt"], "Tradução em Português")
        )
        btn_copiar_pt.pack(side="left", padx=5)

        # Container do Texto Inglês + Tradução
        box_textos = ctk.CTkScrollableFrame(self.frame_conteudo, fg_color="transparent")
        box_textos.pack(fill="both", expand=True, padx=20, pady=10)

        card_en = ctk.CTkFrame(box_textos, fg_color=("gray85", "#27272a"), corner_radius=10)
        card_en.pack(fill="x", pady=5, padx=5)

        lbl_en_title = ctk.CTkLabel(card_en, text="🇬🇧 Texto em Inglês:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3b82f6")
        lbl_en_title.pack(anchor="w", padx=15, pady=(10, 2))

        tb_en = self.app.criar_campo_texto_selecionavel(card_en, self.licao_atual["texto_en"], font_size=14)
        tb_en.pack(fill="x", padx=15, pady=(0, 10))

        card_pt = ctk.CTkFrame(box_textos, fg_color=("gray85", "#27272a"), corner_radius=10)
        card_pt.pack(fill="x", pady=5, padx=5)

        lbl_pt_title = ctk.CTkLabel(card_pt, text="🇧🇷 Tradução em Português:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981")
        lbl_pt_title.pack(anchor="w", padx=15, pady=(10, 2))

        tb_pt = self.app.criar_campo_texto_selecionavel(card_pt, self.licao_atual["texto_pt"], font_size=14)
        tb_pt.pack(fill="x", padx=15, pady=(0, 10))

    # --- ETAPA 3: Frase por Frase ---
    def _render_etapa3_frase_por_frase(self):
        lbl_header = ctk.CTkLabel(
            self.frame_conteudo,
            text="Etapa 3: Estudo Detalhado Frase por Frase",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_header.pack(pady=(15, 5))

        scroll_frases = ctk.CTkScrollableFrame(self.frame_conteudo, fg_color="transparent")
        scroll_frases.pack(fill="both", expand=True, padx=15, pady=5)

        for f in self.licao_atual["frases"]:
            card_f = ctk.CTkFrame(scroll_frases, fg_color=("gray85", "#27272a"), corner_radius=10)
            card_f.pack(fill="x", pady=6, padx=5)

            # Cabeçalho da frase
            hdr = ctk.CTkFrame(card_f, fg_color="transparent")
            hdr.pack(fill="x", padx=12, pady=(10, 2))

            lbl_num = ctk.CTkLabel(hdr, text=f"Frase #{f['id']}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3b82f6")
            lbl_num.pack(side="left")

            btn_play_f = ctk.CTkButton(
                hdr,
                text="🔊 Ouvir Frase",
                width=100,
                height=28,
                fg_color="#10b981",
                hover_color="#059669",
                command=lambda txt=f["texto_en"]: self._tocar_texto(txt)
            )
            btn_play_f.pack(side="right", padx=3)

            btn_copiar_f = ctk.CTkButton(
                hdr,
                text="📋 Copiar Frase",
                width=110,
                height=28,
                fg_color="#3b82f6",
                hover_color="#2563eb",
                command=lambda txt=f["texto_en"]: self.app.copiar_para_area_transferencia(txt, "Frase em Inglês")
            )
            btn_copiar_f.pack(side="right", padx=3)

            btn_salvar_cad = ctk.CTkButton(
                hdr,
                text="💾 Salvar no Caderno",
                width=130,
                height=28,
                fg_color="#8b5cf6",
                hover_color="#7c3aed",
                command=lambda frase_obj=f: self._salvar_frase_caderno(frase_obj)
            )
            btn_salvar_cad.pack(side="right", padx=3)

            # Texto em Inglês selecionável
            tb_en = self.app.criar_campo_texto_selecionavel(card_f, f["texto_en"], font_size=15, font_weight="bold", text_color="#ffffff", max_height=80)
            tb_en.pack(fill="x", padx=12, pady=2)

            # Tradução em PT
            tb_pt = self.app.criar_campo_texto_selecionavel(card_f, f"🇧🇷 {f['texto_pt']}", font_size=13, text_color="#a1a1aa", max_height=80)
            tb_pt.pack(fill="x", padx=12, pady=2)

            # Pronúncia Abrasileirada
            tb_fon = self.app.criar_campo_texto_selecionavel(card_f, f"🗣️ Pronúncia Abrasileirada: {f['pronuncia_abrasileirada']}", font_size=13, font_weight="bold", text_color="#f59e0b", max_height=80)
            tb_fon.pack(fill="x", padx=12, pady=2)

            # Dica de articulação / vocabulário
            if f.get("dica"):
                tb_dica = self.app.criar_campo_texto_selecionavel(card_f, f"💡 Dica: {f['dica']}", font_size=12, text_color="#38bdf8", max_height=80)
                tb_dica.pack(fill="x", padx=12, pady=(2, 8))

    # --- ETAPA 4: Áudio + Texto EN (Sem Tradução) ---
    def _render_etapa4_audio_texto_en(self):
        lbl_header = ctk.CTkLabel(
            self.frame_conteudo,
            text="Etapa 4: Áudio com Texto Exclusivo em Inglês",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_header.pack(pady=(15, 5))

        lbl_sub = ctk.CTkLabel(
            self.frame_conteudo,
            text="Agora sem a tradução em português! Foque em associar o som direto com a escrita em inglês.",
            font=ctk.CTkFont(size=13),
            text_color="#a1a1aa"
        )
        lbl_sub.pack(pady=5)

        btns_e4 = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        btns_e4.pack(pady=5)

        btn_play = ctk.CTkButton(
            btns_e4,
            text="🔊 Ouvir Áudio Completo em Inglês",
            fg_color="#10b981",
            hover_color="#059669",
            height=40,
            command=self._tocar_audio_completo
        )
        btn_play.pack(side="left", padx=5)

        btn_copiar_e4 = ctk.CTkButton(
            btns_e4,
            text="📋 Copiar Texto em Inglês",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            height=40,
            command=lambda: self.app.copiar_para_area_transferencia(self.licao_atual["texto_en"], "Texto em Inglês")
        )
        btn_copiar_e4.pack(side="left", padx=5)

        card_en = ctk.CTkFrame(self.frame_conteudo, fg_color=("gray85", "#27272a"), corner_radius=10)
        card_en.pack(fill="both", expand=True, padx=25, pady=10)

        tb_en = self.app.criar_campo_texto_selecionavel(card_en, self.licao_atual["texto_en"], font_size=16, font_weight="bold")
        tb_en.pack(fill="both", expand=True, padx=15, pady=15)

    # --- ETAPA 5: Prática de Pronúncia (Shadowing) ---
    def _render_etapa5_pratica_pronuncia(self):
        lbl_header = ctk.CTkLabel(
            self.frame_conteudo,
            text="Etapa 5: Prática de Fala & Pronúncia (Shadowing)",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_header.pack(pady=(15, 5))

        frases = self.licao_atual["frases"]
        if not frases:
            return

        # Seleção de Frase para praticar
        frame_sel = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        frame_sel.pack(fill="x", padx=20, pady=5)

        lbl_sel = ctk.CTkLabel(frame_sel, text="Escolha a frase para praticar:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_sel.pack(side="left", padx=(0, 10))

        opcoes_frases = [f"Frase #{f['id']}: {f['texto_en'][:40]}..." for f in frases]
        self.combo_frases_practice = ctk.CTkOptionMenu(
            frame_sel,
            values=opcoes_frases,
            command=self._ao_selecionar_frase_practice,
            width=380
        )
        self.combo_frases_practice.pack(side="left")
        self.combo_frases_practice.set(opcoes_frases[self.frase_selecionada_idx])

        # Card da Frase Atual
        self.card_frase_pratica = ctk.CTkFrame(self.frame_conteudo, fg_color=("gray85", "#27272a"), corner_radius=12)
        self.card_frase_pratica.pack(fill="x", padx=20, pady=10)

        self._atualizar_card_pratica()

    def _ao_selecionar_frase_practice(self, escolha_str: str):
        idx = int(escolha_str.split("#")[1].split(":")[0]) - 1
        self.frase_selecionada_idx = idx
        self._atualizar_card_pratica()

    def _atualizar_card_pratica(self):
        for child in self.card_frase_pratica.winfo_children():
            child.destroy()

        f = self.licao_atual["frases"][self.frase_selecionada_idx]

        # Texto em Inglês Selecionável
        tb_en = self.app.criar_campo_texto_selecionavel(self.card_frase_pratica, f["texto_en"], font_size=16, font_weight="bold", text_color="#3b82f6", max_height=80)
        tb_en.pack(fill="x", padx=15, pady=(15, 2))

        # Pronúncia Abrasileirada Selecionável
        tb_fon = self.app.criar_campo_texto_selecionavel(self.card_frase_pratica, f"🗣️ Pronúncia: {f['pronuncia_abrasileirada']}", font_size=14, font_weight="bold", text_color="#f59e0b", max_height=80)
        tb_fon.pack(fill="x", padx=15, pady=2)

        # Botões de Ação
        frame_btns_action = ctk.CTkFrame(self.card_frase_pratica, fg_color="transparent")
        frame_btns_action.pack(pady=10)

        btn_modelo = ctk.CTkButton(
            frame_btns_action,
            text="🔊 Ouvir Modelo Nativo",
            fg_color="#10b981",
            hover_color="#059669",
            width=180,
            command=lambda: self._tocar_texto(f["texto_en"])
        )
        btn_modelo.pack(side="left", padx=5)

        btn_copiar = ctk.CTkButton(
            frame_btns_action,
            text="📋 Copiar Frase",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            width=140,
            command=lambda: self.app.copiar_para_area_transferencia(f["texto_en"], "Frase em Inglês")
        )
        btn_copiar.pack(side="left", padx=5)

        # Painel de Gravação e Resultado
        frame_mic = ctk.CTkFrame(self.card_frase_pratica, fg_color="transparent")
        frame_mic.pack(pady=10)

        self.btn_rec = ctk.CTkButton(
            frame_mic,
            text="🎙️ Gravar Minha Voz (Falar)",
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            width=220,
            command=lambda: self._gravar_e_avaliar_pronuncia(f["texto_en"])
        )
        self.btn_rec.pack()

        self.lbl_status_rec = ctk.CTkLabel(
            self.card_frase_pratica,
            text="Clique no botão acima, aguarde o sinal e fale a frase em inglês no seu microfone.",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        self.lbl_status_rec.pack(pady=5)

        self.lbl_resultado_pron = ctk.CTkLabel(
            self.card_frase_pratica,
            text="",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.lbl_resultado_pron.pack(pady=(5, 15))

    def _gravar_e_avaliar_pronuncia(self, frase_esperada: str):
        if self.gravando:
            return
        self.gravando = True
        self.btn_rec.configure(state="disabled", text="🔴 Ouvindo seu microfone...")
        self.lbl_status_rec.configure(text="🎙️ Fale agora... (Captação de áudio ativa)", text_color="#ef4444")
        self.lbl_resultado_pron.configure(text="")

        def _thread_stt():
            res = audio_engine.ouvir_microfone(timeout=6, phrase_time_limit=10, idioma="en-US")
            self.gravando = False
            self.btn_rec.configure(state="normal", text="🎙️ Gravar Minha Voz (Falar)")

            if res.get("sucesso"):
                texto_falado = res["texto"]
                sim = listening_service.calcular_similaridade_pronuncia(frase_esperada, texto_falado)

                if sim >= 80:
                    cor = "#10b981"
                    feedback = "🎉 Excelente pronúncia! Fluência quase perfeita!"
                elif sim >= 55:
                    cor = "#f59e0b"
                    feedback = "👍 Muito bom! Boa compreensão, continue praticando."
                else:
                    cor = "#ef4444"
                    feedback = "💡 Tente novamente. Dica: Ouça a voz nativa modelo primeiro!"

                msg = f"Você falou: \"{texto_falado}\"\nPrecisão: {sim}% — {feedback}"
                self.lbl_status_rec.configure(text="✅ Gravado com sucesso!", text_color="#10b981")
                self.lbl_resultado_pron.configure(text=msg, text_color=cor)
            else:
                self.lbl_status_rec.configure(text=f"⚠️ {res.get('erro', 'Falha na gravação.')}", text_color="#ef4444")

        threading.Thread(target=_thread_stt, daemon=True).start()

    # --- ETAPA 6: Escuta Final & Avaliação ---
    def _render_etapa6_escuta_final(self):
        lbl_header = ctk.CTkLabel(
            self.frame_conteudo,
            text="Etapa 6: Escuta Final & Autoavaliação",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_header.pack(pady=(20, 5))

        lbl_inst = ctk.CTkLabel(
            self.frame_conteudo,
            text="Agora que você estudou o texto, a tradução, as frases e praticou a pronúncia,\nouça o áudio em inglês uma última vez!",
            font=ctk.CTkFont(size=13),
            text_color="#a1a1aa"
        )
        lbl_inst.pack(pady=5)

        btn_play = ctk.CTkButton(
            self.frame_conteudo,
            text="🔊 Ouvir Áudio Completo em Inglês (Teste Final)",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=45,
            command=self._tocar_audio_completo
        )
        btn_play.pack(pady=15)

        # Form de autoavaliação
        card_eval = ctk.CTkFrame(self.frame_conteudo, fg_color=("gray85", "#27272a"), corner_radius=10)
        card_eval.pack(padx=30, pady=10, fill="x")

        lbl_eval_q = ctk.CTkLabel(
            card_eval,
            text="Quanto você sentiu que entendeu do áudio nesta escuta final?",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_eval_q.pack(pady=(15, 10))

        frame_btns = ctk.CTkFrame(card_eval, fg_color="transparent")
        frame_btns.pack(pady=(0, 15))

        self.nota_compreensao = 100
        def _set_nota(val: int):
            self.nota_compreensao = val
            messagebox.showinfo("Autoavaliação", f"Compreensão de {val}% selecionada! Clique em 'Finalizar' para registrar.")

        btn_25 = ctk.CTkButton(frame_btns, text="25% (Pouco)", width=100, command=lambda: _set_nota(25), fg_color="#ef4444")
        btn_25.pack(side="left", padx=5)

        btn_50 = ctk.CTkButton(frame_btns, text="50% (Médio)", width=100, command=lambda: _set_nota(50), fg_color="#f59e0b")
        btn_50.pack(side="left", padx=5)

        btn_75 = ctk.CTkButton(frame_btns, text="75% (Bom)", width=100, command=lambda: _set_nota(75), fg_color="#3b82f6")
        btn_75.pack(side="left", padx=5)

        btn_100 = ctk.CTkButton(frame_btns, text="100% (Total!)", width=100, command=lambda: _set_nota(100), fg_color="#10b981")
        btn_100.pack(side="left", padx=5)

        btn_concluir = ctk.CTkButton(
            self.frame_conteudo,
            text="🎉 Finalizar Lição & Salvar no Meu Histórico",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            height=42,
            command=self._salvar_conclusao_licao
        )
        btn_concluir.pack(pady=15)

    def _salvar_conclusao_licao(self):
        sucesso = registrar_progresso_aula(
            topico=self.licao_atual["titulo"],
            status="Concluído",
            nota_pronuncia=self.nota_compreensao
        )
        if sucesso:
            messagebox.showinfo("Parabéns! 🎉", f"Lição '{self.licao_atual['titulo']}' concluída e salva com sucesso!")
            self._ir_para_etapa(1)
        else:
            messagebox.showerror("Erro", "Não foi possível salvar o progresso da lição.")

    # --- Métodos de Áudio ---
    def _tocar_audio_completo(self):
        texto = self.licao_atual["texto_en"]
        self._tocar_texto(texto)

    def _tocar_texto(self, texto: str):
        def _thread_play():
            audio_engine.gerar_e_tocar(texto, lang="en", velocity=self.velocidade_audio)
        threading.Thread(target=_thread_play, daemon=True).start()

    def _salvar_frase_caderno(self, frase_obj: Dict[str, Any]):
        sucesso = salvar_termo(
            termo_ingles=frase_obj["texto_en"],
            traducao=frase_obj["texto_pt"],
            pronuncia_abrasileirada=frase_obj["pronuncia_abrasileirada"],
            exemplo_contexto=frase_obj.get("dica", ""),
            traducao_exemplo=self.licao_atual["titulo"]
        )
        if sucesso:
            messagebox.showinfo("Sucesso", f"Frase #{frase_obj['id']} salva no Caderno de Estudos com sucesso!")
        else:
            messagebox.showerror("Erro", "Erro ao salvar frase no caderno.")
