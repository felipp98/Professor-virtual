import customtkinter as ctk
import tkinter
from tkinter import messagebox

from services.database import init_db
from services.audio_service import audio_engine
from services.logger import logger
from views import TeacherView, IAView, CadernoView, DocsView, PomodoroView, ConfigView, AudioPracticeView

# Configurações do Tema Visual CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TabViewAdapter:
    """Adaptador de compatibilidade para manter suporte a self.app.tabview.set(...) em views legadas."""
    def __init__(self, app):
        self.app = app

    def set(self, nome_aba: str):
        mapa_abas = {
            "🎓 Professor Virtual": "teacher",
            "🎧 Escuta & Pronúncia": "audio",
            "🔎 Consultar IA": "ia",
            "📖 Meu Caderno": "caderno",
            "📚 Decks de Estudo": "docs",
            "⏱️ Timer Pomodoro": "pomodoro",
            "⚙️ Configurações": "config"
        }
        chave = mapa_abas.get(nome_aba, nome_aba)
        self.app.navegar_para(chave)


class LanguageBuddyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inicializa Banco de Dados
        init_db()
        logger.info("Inicializando a aplicação Language Buddy...")

        # Configurações da Janela
        self.title("Language Buddy — Professor Virtual & Painel de Estudos")
        self.geometry("1080x800")
        self.minsize(920, 680)

        # Estado do Menu Lateral
        self.is_sidebar_collapsed = False
        self.current_view_id = "teacher"
        self.botoes_nav = {}
        self.categoria_labels = []
        self.visoes = {}

        # Adaptador para compatibilidade retroativa
        self.tabview = TabViewAdapter(self)

        # Configuração do Layout Principal
        self.setup_ui()

        # Atalhos de Teclado Globais
        self.bind("<Escape>", lambda e: self.teacher_view.parar_audio_teacher() if hasattr(self, "teacher_view") else None)
        self.bind("<Control-f>", lambda e: self._focar_busca_docs())
        self.bind("<Control-F>", lambda e: self._focar_busca_docs())

        # Força visibilidade em primeiro plano após carregar os componentes visuais
        self.after(200, self._bring_to_front)

    def setup_ui(self):
        # Grid Principal de 1 linha e 2 colunas
        self.grid_columnconfigure(0, weight=0)  # Sidebar (largura fixa / animada)
        self.grid_columnconfigure(1, weight=1)  # Conteúdo Principal (expansível)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # 1. MENU LATERAL (SIDEBAR)
        # ----------------------------------------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="#18181b")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # Topo do Sidebar (Branding & Toggle)
        self.sidebar_header = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=60)
        self.sidebar_header.pack(fill="x", padx=10, pady=(15, 10))

        self.lbl_logo_icon = ctk.CTkLabel(
            self.sidebar_header,
            text="🗣️",
            font=ctk.CTkFont(size=24)
        )
        self.lbl_logo_icon.pack(side="left", padx=(5, 5))

        self.lbl_logo_text = ctk.CTkLabel(
            self.sidebar_header,
            text="Language Buddy",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f4f4f5"
        )
        self.lbl_logo_text.pack(side="left", padx=5)

        self.btn_toggle_sidebar = ctk.CTkButton(
            self.sidebar_header,
            text="◀",
            width=32,
            height=32,
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_sidebar
        )
        self.btn_toggle_sidebar.pack(side="right", padx=2)

        # Separador do Topo
        ctk.CTkFrame(self.sidebar_frame, height=1, fg_color="#27272a").pack(fill="x", padx=10, pady=5)

        # Container dos Itens de Navegação (Scrollable)
        self.nav_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Definição das Seções e Módulos
        self.secoes_nav = [
            {
                "titulo": "🎯 PRÁTICA",
                "items": [
                    {"id": "teacher", "icon": "🎓", "label": "Professor Virtual", "sub": "Conversação & Aulas"},
                    {"id": "audio", "icon": "🎧", "label": "Escuta & Pronúncia", "sub": "Treino de Fala"},
                ]
            },
            {
                "titulo": "📚 MATERIAIS",
                "items": [
                    {"id": "ia", "icon": "🔎", "label": "Consultar IA", "sub": "Dicionário Inteligente"},
                    {"id": "caderno", "icon": "📖", "label": "Meu Caderno", "sub": "Anotações e Vocabulário"},
                    {"id": "docs", "icon": "📚", "label": "Decks de Estudo", "sub": "Leitura & PDFs"},
                ]
            },
            {
                "titulo": "🛠️ FERRAMENTAS",
                "items": [
                    {"id": "pomodoro", "icon": "⏱️", "label": "Timer Pomodoro", "sub": "Foco nos Estudos"},
                    {"id": "config", "icon": "⚙️", "label": "Configurações", "sub": "Vozes & Preferências"},
                ]
            }
        ]

        # Constrói os botões da barra lateral
        self.meta_items = {}
        for secao in self.secoes_nav:
            lbl_cat = ctk.CTkLabel(
                self.nav_scroll,
                text=secao["titulo"],
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#a1a1aa",
                anchor="w"
            )
            lbl_cat.pack(fill="x", padx=10, pady=(12, 4))
            self.categoria_labels.append(lbl_cat)

            for item in secao["items"]:
                item_id = item["id"]
                self.meta_items[item_id] = item

                btn = ctk.CTkButton(
                    self.nav_scroll,
                    text=f"  {item['icon']}  {item['label']}",
                    anchor="w",
                    height=42,
                    corner_radius=8,
                    font=ctk.CTkFont(size=13, weight="normal"),
                    fg_color="transparent",
                    text_color="#d4d4d8",
                    hover_color="#27272a",
                    command=lambda id_mod=item_id: self.navegar_para(id_mod)
                )
                btn.pack(fill="x", padx=5, pady=2)
                self.botoes_nav[item_id] = btn

        # Rodapé do Sidebar (Status da Aplicação)
        self.sidebar_footer = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=40)
        self.sidebar_footer.pack(fill="x", side="bottom", padx=10, pady=10)

        self.lbl_status = ctk.CTkLabel(
            self.sidebar_footer,
            text="● Online | v2.0",
            font=ctk.CTkFont(size=11),
            text_color="#22c55e"
        )
        self.lbl_status.pack(side="left", padx=5)

        # ----------------------------------------------------
        # 2. ÁREA PRINCIPAL (HEADER + CONTEÚDO DAS TELAS)
        # ----------------------------------------------------
        self.main_area = ctk.CTkFrame(self, fg_color="#09090b", corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)

        # Header Superior com Contexto da Tela Ativa
        self.header_frame = ctk.CTkFrame(self.main_area, fg_color="#18181b", height=60, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_propagate(False)

        self.lbl_header_icon = ctk.CTkLabel(
            self.header_frame,
            text="🎓",
            font=ctk.CTkFont(size=22)
        )
        self.lbl_header_icon.pack(side="left", padx=(20, 8), pady=12)

        self.lbl_header_title = ctk.CTkLabel(
            self.header_frame,
            text="Professor Virtual",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#f4f4f5"
        )
        self.lbl_header_title.pack(side="left", padx=0, pady=12)

        self.lbl_header_sub = ctk.CTkLabel(
            self.header_frame,
            text="— Conversação & Aulas Interativas",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        self.lbl_header_sub.pack(side="left", padx=8, pady=12)

        self.lbl_header_dica = ctk.CTkLabel(
            self.header_frame,
            text="💡 Atalhos: Ctrl+F (Buscar Decks) | Esc (Parar Áudio)",
            font=ctk.CTkFont(size=11),
            text_color="#71717a"
        )
        self.lbl_header_dica.pack(side="right", padx=20, pady=12)

        # Container do Conteúdo das Visões Modulares
        self.content_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)

        # Instancia as visões dentro do container principal
        self.teacher_view = TeacherView(self.content_frame, self)
        self.audio_practice_view = AudioPracticeView(self.content_frame, self)
        self.ia_view = IAView(self.content_frame, self)
        self.caderno_view = CadernoView(self.content_frame, self)
        self.docs_view = DocsView(self.content_frame, self)
        self.pomodoro_view = PomodoroView(self.content_frame, self)
        self.config_view = ConfigView(self.content_frame, self)

        self.visoes = {
            "teacher": self.teacher_view,
            "audio": self.audio_practice_view,
            "ia": self.ia_view,
            "caderno": self.caderno_view,
            "docs": self.docs_view,
            "pomodoro": self.pomodoro_view,
            "config": self.config_view
        }

        # Exibe a tela inicial padrão (Professor Virtual)
        self.navegar_para("teacher")

    def navegar_para(self, id_visao: str):
        """Muda suavemente a tela exibida no container principal e atualiza o estado do sidebar/header."""
        if id_visao not in self.visoes:
            return

        self.current_view_id = id_visao

        # Esconde todas as telas e exibe a selecionada
        for key, view in self.visoes.items():
            if key == id_visao:
                view.pack(fill="both", expand=True)
            else:
                view.pack_forget()

        # Atualiza a iluminação visual dos botões no sidebar
        for item_id, btn in self.botoes_nav.items():
            if item_id == id_visao:
                btn.configure(
                    fg_color="#2563eb",
                    text_color="#ffffff",
                    hover_color="#1d4ed8"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color="#d4d4d8",
                    hover_color="#27272a"
                )

        # Atualiza o cabeçalho superior com as informações da tela ativa
        meta = self.meta_items.get(id_visao, {})
        if meta:
            self.lbl_header_icon.configure(text=meta.get("icon", ""))
            self.lbl_header_title.configure(text=meta.get("label", ""))
            self.lbl_header_sub.configure(text=f"— {meta.get('sub', '')}")

    def toggle_sidebar(self):
        """Alterna a barra lateral entre o modo expandido (completo) e recolhido (apenas ícones)."""
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed

        if self.is_sidebar_collapsed:
            # Encolhe largura para modo compacto
            self.sidebar_frame.configure(width=68)
            self.lbl_logo_text.pack_forget()
            self.lbl_status.configure(text="●")
            self.btn_toggle_sidebar.configure(text="▶")

            # Esconde títulos das categorias
            for lbl in self.categoria_labels:
                lbl.pack_forget()

            # Ajusta botões para exibir apenas o ícone
            for item_id, btn in self.botoes_nav.items():
                meta = self.meta_items.get(item_id, {})
                btn.configure(text=f"{meta.get('icon', '')}", anchor="center")
        else:
            # Expande largura para modo normal
            self.sidebar_frame.configure(width=230)
            self.lbl_logo_text.pack(side="left", padx=5)
            self.lbl_status.configure(text="● Online | v2.0")
            self.btn_toggle_sidebar.configure(text="◀")

            # Reexibe botões completos com categoria
            # Reorganiza o scrollframe para restaurar ordem de categorias e botões
            for lbl in self.categoria_labels:
                lbl.pack_forget()

            for item_id, btn in self.botoes_nav.items():
                btn.pack_forget()

            for secao in self.secoes_nav:
                # Encontra e re-exibe a label correspondente
                for lbl in self.categoria_labels:
                    if lbl.cget("text") == secao["titulo"]:
                        lbl.pack(fill="x", padx=10, pady=(12, 4))
                        break

                for item in secao["items"]:
                    item_id = item["id"]
                    btn = self.botoes_nav[item_id]
                    btn.configure(text=f"  {item['icon']}  {item['label']}", anchor="w")
                    btn.pack(fill="x", padx=5, pady=2)

    def _focar_busca_docs(self):
        try:
            self.navegar_para("docs")
            if hasattr(self.docs_view, "entry_busca_docs"):
                self.docs_view.entry_busca_docs.focus_set()
        except Exception:
            pass

    def _bring_to_front(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(1000, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def copiar_para_area_transferencia(self, texto: str, rotulo: str = "Texto"):
        """Copia um texto diretamente para a área de transferência do sistema."""
        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.update()
            messagebox.showinfo("Copiado! 📋", f"{rotulo} copiado para a área de transferência com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao copiar para a área de transferência: {e}")
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

        def _bloquear_edicao(event):
            # Permite Ctrl+C, Ctrl+A, navegacao e selecao com mouse
            if (event.state & 4 and event.keysym.lower() in ['c', 'a']) or event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End']:
                return None
            return 'break'

        tb.bind("<Key>", _bloquear_edicao)

        menu = tkinter.Menu(tb._textbox, tearoff=0)
        def _copiar_trecho():
            try:
                sel = tb._textbox.get("sel.first", "sel.last")
                if sel:
                    self.clipboard_clear()
                    self.clipboard_append(sel)
                    self.update()
                else:
                    self.clipboard_clear()
                    self.clipboard_append(tb.get("1.0", "end-1c"))
                    self.update()
            except Exception:
                try:
                    self.clipboard_clear()
                    self.clipboard_append(tb.get("1.0", "end-1c"))
                    self.update()
                except Exception:
                    pass

        menu.add_command(label="📋 Copiar texto", command=_copiar_trecho)
        tb._textbox.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        return tb

if __name__ == "__main__":
    app = LanguageBuddyApp()
    app.mainloop()

