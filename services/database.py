import os
import sqlite3
import csv
from datetime import datetime
from .logger import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_NAME = os.path.join(DATA_DIR, "estudos.db")

from contextlib import contextmanager

@contextmanager
def get_connection():
    """Retorna um gerenciador de contexto com conexão SQLite com fechamento garantido."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Cria as tabelas do banco de dados caso não existam."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                termo_ingles TEXT NOT NULL,
                traducao TEXT NOT NULL,
                pronuncia_abrasileirada TEXT NOT NULL,
                exemplo_contexto TEXT,
                traducao_exemplo TEXT,
                data_cadastro TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perfil_aluno (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                nivel TEXT DEFAULT 'Básico',
                ultimo_topico TEXT,
                data_cadastro TEXT NOT NULL
            )
        """)
        # Migração automática para adicionar a coluna nivel se o banco já existia
        try:
            cursor.execute("ALTER TABLE perfil_aluno ADD COLUMN nivel TEXT DEFAULT 'Básico'")
        except Exception:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progresso_aulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topico TEXT NOT NULL,
                status TEXT NOT NULL,
                nota_pronuncia INTEGER DEFAULT 0,
                data_atualizacao TEXT NOT NULL
            )
        """)
        conn.commit()

def salvar_termo(termo_ingles: str, traducao: str, pronuncia_abrasileirada: str, exemplo_contexto: str = "", traducao_exemplo: str = "") -> bool:
    """Insere um novo termo no banco de dados."""
    try:
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vocabulario (termo_ingles, traducao, pronuncia_abrasileirada, exemplo_contexto, traducao_exemplo, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (termo_ingles.strip(), traducao.strip(), pronuncia_abrasileirada.strip(), exemplo_contexto.strip(), traducao_exemplo.strip(), data_atual))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao salvar termo no banco: {e}")
        return False

def listar_termos(busca: str = "") -> list:
    """Busca e retorna todos os termos do banco, com suporte a filtro de busca."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if busca.strip():
            termo_busca = f"%{busca.strip()}%"
            cursor.execute("""
                SELECT * FROM vocabulario 
                WHERE termo_ingles LIKE ? OR traducao LIKE ? OR pronuncia_abrasileirada LIKE ?
                ORDER BY id DESC
            """, (termo_busca, termo_busca, termo_busca))
        else:
            cursor.execute("SELECT * FROM vocabulario ORDER BY id DESC")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def deletar_termo(termo_id: int) -> bool:
    """Deleta um termo do banco de dados pelo ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vocabulario WHERE id = ?", (termo_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao deletar termo: {e}")
        return False

def obter_estatisticas() -> dict:
    """Retorna estatísticas do caderno de estudos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM vocabulario")
        total = cursor.fetchone()["total"]
        return {"total_termos": total}

def exportar_csv(filepath: str) -> bool:
    """Exporta todos os termos cadastrados para um arquivo CSV."""
    try:
        termos = listar_termos()
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Termo em Inglês", "Tradução", "Pronúncia Abrasileirada", "Exemplo no Trabalho", "Tradução do Exemplo", "Data de Cadastro"])
            for t in termos:
                writer.writerow([
                    t["id"],
                    t["termo_ingles"],
                    t["traducao"],
                    t["pronuncia_abrasileirada"],
                    t.get("exemplo_contexto", ""),
                    t.get("traducao_exemplo", ""),
                    t["data_cadastro"]
                ])
        return True
    except Exception as e:
        logger.error(f"Erro ao exportar CSV: {e}")
        return False

def obter_perfil_aluno() -> dict:
    """Retorna o perfil do aluno ou None se não cadastrado."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM perfil_aluno ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

def salvar_perfil_aluno(nome: str, nivel: str = "Básico", ultimo_topico: str = "") -> bool:
    """Cria ou atualiza o perfil do aluno incluindo seu nível de proficiência."""
    try:
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        perfil = obter_perfil_aluno()
        with get_connection() as conn:
            cursor = conn.cursor()
            if perfil:
                nivel_final = nivel if nivel else perfil.get("nivel", "Básico")
                cursor.execute("""
                    UPDATE perfil_aluno 
                    SET nome = ?, nivel = ?, ultimo_topico = ?
                    WHERE id = ?
                """, (nome.strip(), nivel_final.strip(), ultimo_topico.strip(), perfil["id"]))
            else:
                cursor.execute("""
                    INSERT INTO perfil_aluno (nome, nivel, ultimo_topico, data_cadastro)
                    VALUES (?, ?, ?, ?)
                """, (nome.strip(), nivel.strip(), ultimo_topico.strip(), data_atual))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao salvar perfil do aluno: {e}")
        return False

def registrar_progresso_aula(topico: str, status: str, nota_pronuncia: int = 0) -> bool:
    """Registra ou atualiza o progresso de uma lição."""
    try:
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO progresso_aulas (topico, status, nota_pronuncia, data_atualizacao)
                VALUES (?, ?, ?, ?)
            """, (topico.strip(), status.strip(), nota_pronuncia, data_atual))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao registrar progresso de aula: {e}")
        return False

