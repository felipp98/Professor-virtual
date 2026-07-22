import customtkinter as ctk
from tkinter import messagebox
from services.logger import logger

class PomodoroView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pomodoro_rodando = False
        self.pomodoro_tempo_restante = 30 * 60
        self.pomodoro_tempo_total = 30 * 60
        self.pomodoro_timer_id = None
        self.build_ui()

    def build_ui(self):
        lbl_titulo = ctk.CTkLabel(self, text="Timer Pomodoro de Estudos", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(pady=(20, 5))

        lbl_desc = ctk.CTkLabel(self, text="Mantenha o foco diário estudando em blocos de tempo sem distrações.", text_color="gray")
        lbl_desc.pack(pady=(0, 20))

        # Seleção de Modo
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(pady=10)

        self.btn_foco = ctk.CTkButton(mode_frame, text="🎯 Foco (30 min)", command=lambda: self.set_pomodoro_modo(30), width=140)
        self.btn_foco.pack(side="left", padx=5)

        self.btn_pausa = ctk.CTkButton(mode_frame, text="☕ Pausa (5 min)", command=lambda: self.set_pomodoro_modo(5), fg_color="#475569", width=140)
        self.btn_pausa.pack(side="left", padx=5)

        # Display do Relógio
        self.lbl_clock = ctk.CTkLabel(self, text="30:00", font=ctk.CTkFont(size=72, weight="bold"), text_color="#60A5FA")
        self.lbl_clock.pack(pady=20)

        # Barra de Progresso
        self.progress_pomodoro = ctk.CTkProgressBar(self, width=400, height=14)
        self.progress_pomodoro.set(1.0)
        self.progress_pomodoro.pack(pady=10)

        # Botões do Timer
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
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
