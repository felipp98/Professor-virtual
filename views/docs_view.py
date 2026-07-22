import customtkinter as ctk
from tkinter import messagebox
from services.docs_service import listar_documentos, ler_pdf, buscar_nos_documentos
from services.database import salvar_termo
from services.logger import logger

class DocsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.lista_documentos = []
        self.doc_atual = None
        self.build_ui()

    def build_ui(self):
        header = ctk.CTkLabel(self, text="📚 Decks de Estudo & Materiais de Apoio", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(anchor="w", padx=20, pady=(15, 5))

        subtitle = ctk.CTkLabel(self, text="Consulte o conteúdo dos PDFs da pasta 'docs/' diretamente no app sem precisar abrir arquivos externos.", text_color="gray")
        subtitle.pack(anchor="w", padx=20, pady=(0, 10))

        # Frame de Controles / Seleção e Busca
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
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
        act_frame = ctk.CTkFrame(self, fg_color="transparent")
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
        self.lbl_status_doc = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color="#60A5FA")
        self.lbl_status_doc.pack(anchor="w", padx=20, pady=(2, 2))

        # Área de Texto do Documento
        self.textbox_pdf = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            corner_radius=8
        )
        self.textbox_pdf.pack(fill="both", expand=True, padx=20, pady=(0, 15))

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
        
        self.app.tabview.set("🔎 Consultar IA")
        if hasattr(self.app, "ia_view"):
            self.app.ia_view.entry_termo.delete(0, "end")
            self.app.ia_view.entry_termo.insert(0, texto_sel)
            self.app.ia_view.iniciar_consulta_ia()

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
            if hasattr(self.app, "caderno_view"):
                self.app.caderno_view.carregar_caderno()
        else:
            messagebox.showerror("Erro", "Não foi possível salvar no banco de dados.")
