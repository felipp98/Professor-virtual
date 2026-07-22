import customtkinter as ctk
import tkinter
from tkinter import messagebox

from services.database import init_db
from services.audio_service import audio_engine
from services.logger import logger
from views import TeacherView, IAView, CadernoView, DocsView, PomodoroView, ConfigView

# Configurações do Tema Visual CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LanguageBuddyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inicializa Banco de Dados
        init_db()
        logger.info("Inicializando a aplicação Language Buddy...")

        # Configurações da Janela
        self.title("Language Buddy — Professor Virtual & Painel de Estudos")
        self.geometry("980x750")
        self.minsize(850, 600)

        # Layout Principal (Barra de Abas & Visões Modulares)
        self.setup_ui()

        # Atalhos de Teclado Globais
        self.bind("<Escape>", lambda e: self.teacher_view.parar_audio_teacher())
        self.bind("<Control-f>", lambda e: self._focar_busca_docs())
        self.bind("<Control-F>", lambda e: self._focar_busca_docs())

        # Força visibilidade em primeiro plano após carregar os componentes visuais
        self.after(200, self._bring_to_front)

    def setup_ui(self):
        # Abas da Aplicação
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        tab_teacher = self.tabview.add("🎓 Professor Virtual")
        tab_ia = self.tabview.add("🔎 Consultar IA")
        tab_caderno = self.tabview.add("📖 Meu Caderno")
        tab_docs = self.tabview.add("📚 Decks de Estudo")
        tab_pomodoro = self.tabview.add("⏱️ Timer Pomodoro")
        tab_config = self.tabview.add("⚙️ Configurações")

        # Instancia as visões modulares em cada aba correspondente
        self.teacher_view = TeacherView(tab_teacher, self)
        self.teacher_view.pack(fill="both", expand=True)

        self.ia_view = IAView(tab_ia, self)
        self.ia_view.pack(fill="both", expand=True)

        self.caderno_view = CadernoView(tab_caderno, self)
        self.caderno_view.pack(fill="both", expand=True)

        self.docs_view = DocsView(tab_docs, self)
        self.docs_view.pack(fill="both", expand=True)

        self.pomodoro_view = PomodoroView(tab_pomodoro, self)
        self.pomodoro_view.pack(fill="both", expand=True)

        self.config_view = ConfigView(tab_config, self)
        self.config_view.pack(fill="both", expand=True)

    def _focar_busca_docs(self):
        try:
            self.tabview.set("📚 Decks de Estudo")
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
            if hasattr(self.teacher_view, "lbl_status_teacher") and self.teacher_view.lbl_status_teacher.winfo_exists():
                self.teacher_view.lbl_status_teacher.configure(text=f"📋 {rotulo} copiado para a área de transferência!", text_color="#10b981")
            elif hasattr(self.ia_view, "lbl_status_ia") and self.ia_view.lbl_status_ia.winfo_exists():
                self.ia_view.lbl_status_ia.configure(text=f"📋 {rotulo} copiado para a área de transferência!", text_color="#10b981")
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
            if (event.state & 4 and event.keysym.lower() == 'c') or event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End']:
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
                    if hasattr(self.teacher_view, "lbl_status_teacher") and self.teacher_view.lbl_status_teacher.winfo_exists():
                        self.teacher_view.lbl_status_teacher.configure(text="📋 Trecho selecionado copiado!", text_color="#10b981")
                    elif hasattr(self.ia_view, "lbl_status_ia") and self.ia_view.lbl_status_ia.winfo_exists():
                        self.ia_view.lbl_status_ia.configure(text="📋 Trecho selecionado copiado!", text_color="#10b981")
            except Exception:
                pass

        menu.add_command(label="📋 Copiar seleção", command=_copiar_trecho)
        tb._textbox.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        return tb

if __name__ == "__main__":
    app = LanguageBuddyApp()
    app.mainloop()
