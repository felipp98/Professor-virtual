import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
from services.database import listar_termos, deletar_termo, obter_estatisticas, exportar_csv
from services.audio_service import audio_engine
from services.logger import logger

class CadernoView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.build_ui()

    def build_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        lbl_titulo = ctk.CTkLabel(header_frame, text="Seu Vocabulário Salvo", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(side="left")

        self.lbl_stats = ctk.CTkLabel(header_frame, text="Total: 0 termos", font=ctk.CTkFont(size=14), text_color="#A1A1AA")
        self.lbl_stats.pack(side="right")

        # Barra de Busca e Ações
        bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        bar_frame.pack(fill="x", padx=20, pady=5)

        self.entry_busca = ctk.CTkEntry(bar_frame, placeholder_text="🔍 Filtrar por palavra, tradução ou pronúncia...", height=38)
        self.entry_busca.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_busca.bind("<KeyRelease>", lambda e: self.carregar_caderno())

        btn_exportar = ctk.CTkButton(bar_frame, text="📥 Exportar CSV", width=130, height=38, command=self.exportar_caderno_csv)
        btn_exportar.pack(side="right")

        # Lista Scrollável de Termos
        self.scroll_caderno = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.scroll_caderno.pack(fill="both", expand=True, padx=20, pady=10)

        # Carrega dados iniciais
        self.carregar_caderno()

    def carregar_caderno(self):
        for child in self.scroll_caderno.winfo_children():
            child.destroy()

        termo_busca = self.entry_busca.get()
        termos = listar_termos(termo_busca)

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

            top_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            top_frame.pack(fill="x", padx=12, pady=(10, 2))

            lbl_t_ingles = ctk.CTkLabel(top_frame, text=t["termo_ingles"], font=ctk.CTkFont(size=16, weight="bold"), text_color="#60A5FA")
            lbl_t_ingles.pack(side="left")

            lbl_pron = ctk.CTkLabel(top_frame, text=f'"{t["pronuncia_abrasileirada"]}"', font=ctk.CTkFont(size=14, weight="bold"), text_color="#F59E0B")
            lbl_pron.pack(side="left", padx=15)

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

            lbl_trad = ctk.CTkLabel(item_frame, text=f"Tradução: {t['traducao']}", font=ctk.CTkFont(size=13))
            lbl_trad.pack(anchor="w", padx=12, pady=2)

            if t.get("exemplo_contexto"):
                lbl_ex = ctk.CTkLabel(item_frame, text=f"Contexto: {t['exemplo_contexto']} → {t.get('traducao_exemplo', '')}", font=ctk.CTkFont(size=12, slant="italic"), text_color="#94A3B8")
                lbl_ex.pack(anchor="w", padx=12, pady=(2, 10))

    def _worker_tocar_audio(self, texto):
        audio_engine.falar(texto_pt="", termo_en=texto)

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
