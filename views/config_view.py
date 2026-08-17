import customtkinter as ctk
from tkinter import messagebox
from services.config import load_config, save_config, obter_api_key
from services.logger import logger

class ConfigView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.mostrar_chave = False
        self.build_ui()

    def build_ui(self):
        lbl_tit = ctk.CTkLabel(self, text="Configurações da API, Sistema & Voz Neural", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_tit.pack(anchor="w", padx=20, pady=(15, 5))

        lbl_sub = ctk.CTkLabel(self, text="Gerencie sua API Key do OpenRouter, os modelos de IA e a voz de síntese do professor.", text_color="gray")
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 20))

        # Form de Configuração
        form_frame = ctk.CTkFrame(self, corner_radius=10)
        form_frame.pack(fill="x", padx=20, pady=10)

        # Header Campo API Key + Status de Segurança
        key_header_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        key_header_frame.pack(fill="x", padx=15, pady=(15, 2))

        lbl_key = ctk.CTkLabel(key_header_frame, text="Chave de API do OpenRouter (API Key):", font=ctk.CTkFont(weight="bold"))
        lbl_key.pack(side="left")

        self.lbl_status_cofre = ctk.CTkLabel(
            key_header_frame, 
            text="🔒 Protegida no Windows Credential Manager", 
            font=ctk.CTkFont(size=11), 
            text_color="#22C55E"
        )
        self.lbl_status_cofre.pack(side="right")

        # Container do Input de API Key com Botão Toggle (👁️)
        key_input_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        key_input_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_api_key = ctk.CTkEntry(
            key_input_frame, 
            placeholder_text="sk-or-v1-...", 
            show="*", 
            width=460, 
            height=38
        )
        self.entry_api_key.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_toggle_eye = ctk.CTkButton(
            key_input_frame,
            text="👁️",
            width=42,
            height=38,
            fg_color="#27272A",
            hover_color="#3F3F46",
            font=ctk.CTkFont(size=14),
            command=self.toggle_visibilidade_chave
        )
        self.btn_toggle_eye.pack(side="left")

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

    def toggle_visibilidade_chave(self):
        """Alterna a exibição da chave entre texto oculto (*) e visível."""
        self.mostrar_chave = not self.mostrar_chave
        if self.mostrar_chave:
            self.entry_api_key.configure(show="")
            self.btn_toggle_eye.configure(fg_color="#3B82F6")
        else:
            self.entry_api_key.configure(show="*")
            self.btn_toggle_eye.configure(fg_color="#27272A")

    def carregar_configuracoes_ui(self):
        cfg = load_config()
        key_atual = obter_api_key()

        self.entry_api_key.delete(0, "end")
        if key_atual:
            self.entry_api_key.insert(0, key_atual)
            self.lbl_status_cofre.configure(text="🔒 Protegida no Windows Credential Manager", text_color="#22C55E")
        else:
            self.lbl_status_cofre.configure(text="⚠️ Nenhuma chave cadastrada", text_color="#EAB308")

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
            if api_key:
                self.lbl_status_cofre.configure(text="🔒 Protegida no Windows Credential Manager", text_color="#22C55E")
            else:
                self.lbl_status_cofre.configure(text="⚠️ Nenhuma chave cadastrada", text_color="#EAB308")
            messagebox.showinfo("Sucesso", f"Configurações e chave protegida salvas com sucesso!")
        else:
            messagebox.showerror("Erro", "Não foi possível salvar as configurações.")
