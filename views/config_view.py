import customtkinter as ctk
from tkinter import messagebox
from services.config import load_config, save_config
from services.logger import logger

class ConfigView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.build_ui()

    def build_ui(self):
        lbl_tit = ctk.CTkLabel(self, text="Configurações da API, Sistema & Voz Neural", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_tit.pack(anchor="w", padx=20, pady=(15, 5))

        lbl_sub = ctk.CTkLabel(self, text="Gerencie sua API Key do OpenRouter, os modelos de IA e a voz de síntese do professor.", text_color="gray")
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 20))

        # Form de Configuração
        form_frame = ctk.CTkFrame(self, corner_radius=10)
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
        self.combo_modelo.pack(anchor="w", padx=15, pady=(0, 10))

        # Campo Seleção de Voz Neural TTS
        lbl_voice = ctk.CTkLabel(form_frame, text="🎙️ Voz Neural do Professor (Síntese por Voz):", font=ctk.CTkFont(weight="bold"))
        lbl_voice.pack(anchor="w", padx=15, pady=(10, 2))

        self.combo_voz = ctk.CTkComboBox(
            form_frame,
            values=[
                "pt-BR-AntonioNeural (Masculino Neural)",
                "pt-BR-FranciscaNeural (Feminino Neural)",
                "pt-BR-ThalitaNeural (Feminino Suave)"
            ],
            width=500,
            height=38
        )
        self.combo_voz.pack(anchor="w", padx=15, pady=(0, 20))

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

        self.carregar_configuracoes_ui()

    def carregar_configuracoes_ui(self):
        cfg = load_config()
        if cfg.get("api_key"):
            self.entry_api_key.insert(0, cfg["api_key"])
        if cfg.get("model"):
            self.combo_modelo.set(cfg["model"])
        
        voz = cfg.get("voice", "pt-BR-AntonioNeural")
        if "Francisca" in voz:
            self.combo_voz.set("pt-BR-FranciscaNeural (Feminino Neural)")
        elif "Thalita" in voz:
            self.combo_voz.set("pt-BR-ThalitaNeural (Feminino Suave)")
        else:
            self.combo_voz.set("pt-BR-AntonioNeural (Masculino Neural)")

    def salvar_configuracoes_ui(self):
        api_key = self.entry_api_key.get().strip()
        model = self.combo_modelo.get().strip()
        voz_sel = self.combo_voz.get().strip()

        if "Francisca" in voz_sel:
            voice_code = "pt-BR-FranciscaNeural"
        elif "Thalita" in voz_sel:
            voice_code = "pt-BR-ThalitaNeural"
        else:
            voice_code = "pt-BR-AntonioNeural"

        cfg = load_config()
        cfg["api_key"] = api_key
        cfg["model"] = model
        cfg["voice"] = voice_code

        if save_config(cfg):
            messagebox.showinfo("Sucesso", f"Configurações e voz ('{voice_code}') salvas com sucesso!")
        else:
            messagebox.showerror("Erro", "Não foi possível salvar as configurações.")
