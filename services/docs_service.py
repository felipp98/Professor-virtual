import os
import glob
import re
import pypdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")

def formatar_nome_deck(filename: str) -> str:
    """Converte o nome do arquivo em um título legível para o usuário."""
    if "00_Mapa_de_Estudos" in filename:
        return "⭐ MAPA DE ESTUDOS COMPLETO (Guia do Professor)"
    nome = os.path.splitext(filename)[0]
    nome = nome.replace("+", " ").replace("_", " ")
    # Limpa múltiplos espaços
    nome = re.sub(r'\s+', ' ', nome).strip()
    return nome

def listar_documentos() -> list:
    """Retorna uma lista de dicionários com informações de cada PDF em docs/."""
    if not os.path.exists(DOCS_DIR):
        return []
    
    arquivos = sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf")))
    lista = []
    for filepath in arquivos:
        filename = os.path.basename(filepath)
        titulo = formatar_nome_deck(filename)
        lista.append({
            "filename": filename,
            "filepath": filepath,
            "titulo": titulo
        })
    return lista

def ler_pdf(filepath: str) -> dict:
    """
    Lê um arquivo PDF e retorna as páginas e o texto extraído.
    """
    if not os.path.exists(filepath):
        return {"sucesso": False, "erro": "Arquivo não encontrado", "paginas": [], "texto_completo": ""}
    
    try:
        reader = pypdf.PdfReader(filepath)
        paginas = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            # Limpeza básica do texto
            text_clean = text.strip()
            paginas.append({
                "numero": index + 1,
                "texto": text_clean
            })
        
        texto_completo = "\n\n--- PÁGINA ---\n\n".join([p["texto"] for p in paginas if p["texto"]])
        return {
            "sucesso": True,
            "total_paginas": len(reader.pages),
            "paginas": paginas,
            "texto_completo": texto_completo
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "paginas": [],
            "texto_completo": ""
        }

def buscar_nos_documentos(termo: str) -> list:
    """
    Pesquisa por um termo/palavra-chave em todos os PDFs da pasta docs/.
    Retorna os documentos e trechos onde o termo foi encontrado.
    """
    if not termo or not termo.strip():
        return []
    
    termo_lower = termo.strip().lower()
    docs = listar_documentos()
    resultados = []
    
    for doc in docs:
        dados = ler_pdf(doc["filepath"])
        if not dados["sucesso"]:
            continue
        
        matches_doc = []
        for pag in dados["paginas"]:
            if termo_lower in pag["texto"].lower():
                # Extrai trechos contendo o termo
                linhas = pag["texto"].split('\n')
                linhas_relevantes = [l.strip() for ll in linhas for l in [ll.strip()] if termo_lower in l.lower()]
                trecho = " | ".join(linhas_relevantes[:3]) if linhas_relevantes else pag["texto"][:150]
                matches_doc.append({
                    "pagina": pag["numero"],
                    "trecho": trecho
                })
        
        if matches_doc:
            resultados.append({
                "filename": doc["filename"],
                "titulo": doc["titulo"],
                "filepath": doc["filepath"],
                "matches": matches_doc
            })
            
    return resultados
