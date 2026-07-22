import os
import sys
import unittest

# Adiciona o diretório raiz ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from services.database import init_db, salvar_termo, listar_termos, deletar_termo, salvar_perfil_aluno, obter_perfil_aluno
from services.teacher_service import extrair_json_resposta, sanitizar_texto_chat
from services.docs_service import formatar_nome_deck
from services.audio_service import sanitizar_texto_fala
from services.config import load_config, save_config
from services.logger import logger

class TestDatabase(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_salvar_e_listar_termo(self):
        termo = "Deploy_UnitTest"
        traducao = "Implantação"
        pronuncia = "di-PLÓI"
        
        sucesso = salvar_termo(termo, traducao, pronuncia)
        self.assertTrue(sucesso)

        termos = listar_termos(busca="UnitTest")
        self.assertGreaterEqual(len(termos), 1)
        item = termos[0]
        self.assertEqual(item["termo_ingles"], termo)
        self.assertEqual(item["traducao"], traducao)

        # Limpa o termo de teste
        deletar_termo(item["id"])

    def test_perfil_aluno(self):
        sucesso = salvar_perfil_aluno(nome="Dev Teste", nivel="Intermediário")
        self.assertTrue(sucesso)

        perfil = obter_perfil_aluno()
        self.assertIsNotNone(perfil)
        self.assertEqual(perfil["nome"], "Dev Teste")
        self.assertEqual(perfil["nivel"], "Intermediário")


class TestTeacherServiceParsers(unittest.TestCase):
    def test_extrair_json_com_think_tags(self):
        raw_llm_output = """<think>
        User is asking about deadline. Let's build a JSON response.
        </think>
        {
            "fala_audio_pt": "Deadline é a data limite!",
            "termo_en": "Deadline",
            "pronuncia_abrasileirada": "DÉD-láin",
            "dica_articulacao": "Articule o D inicial limpo.",
            "texto_chat": "### 🗓️ Deadline\\nSignifica prazo final.",
            "modo_resposta": "voz",
            "instrucao_aluno": "Tente usar numa frase."
        }"""
        data = extrair_json_resposta(raw_llm_output)
        self.assertEqual(data.get("termo_en"), "Deadline")
        self.assertEqual(data.get("pronuncia_abrasileirada"), "DÉD-láin")

    def test_sanitizar_texto_chat(self):
        texto_sujo = "We need to output JSON... {\"texto_chat\": \"### Olá Dev!\"}"
        texto_limpo = sanitizar_texto_chat(texto_sujo)
        self.assertNotIn("We need to output", texto_limpo)


class TestAudioService(unittest.TestCase):
    def test_sanitizar_texto_fala(self):
        texto = "**Schedule** significa *agendamento*! Veja: #1"
        limpo = sanitizar_texto_fala(texto)
        self.assertNotIn("**", limpo)
        self.assertNotIn("*", limpo)
        self.assertNotIn("#", limpo)


class TestDocsService(unittest.TestCase):
    def test_formatar_nome_deck(self):
        nome = "00_Mapa_de_Estudos.pdf"
        titulo = formatar_nome_deck(nome)
        self.assertIn("MAPA DE ESTUDOS", titulo)


class TestConfigAndLogger(unittest.TestCase):
    def test_carregar_e_salvar_config(self):
        cfg = load_config()
        self.assertIn("voice", cfg)
        self.assertIn("model", cfg)

        # Salva com uma voz alternativa
        cfg["voice"] = "pt-BR-FranciscaNeural"
        salvo = save_config(cfg)
        self.assertTrue(salvo)

        cfg_reloaded = load_config()
        self.assertEqual(cfg_reloaded["voice"], "pt-BR-FranciscaNeural")

        # Restaura padrao
        cfg["voice"] = "pt-BR-AntonioNeural"
        save_config(cfg)

    def test_logger_funcional(self):
        logger.info("Teste de log unitário executado com sucesso.")
        log_path = os.path.join(BASE_DIR, "data", "app.log")
        self.assertTrue(os.path.exists(log_path))


if __name__ == "__main__":
    unittest.main()
