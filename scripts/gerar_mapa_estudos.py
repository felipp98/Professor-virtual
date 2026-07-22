import os
import glob
import re
import sys
import pypdf
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUTPUT_PDF = os.path.join(DOCS_DIR, "Mapa_de_Estudos_Ingles.pdf")
OUTPUT_MD = os.path.join(DOCS_DIR, "Mapa_de_Estudos_Ingles.md")

# ==========================================
# 1. EXTRATOR E LIMPADOR DE DADOS DOS PDFS
# ==========================================
def extrair_cards_do_pdf(filepath):
    """Lê um PDF da pasta docs/ e extrai os pares (Termo em Inglês, Tradução em PT)."""
    try:
        reader = pypdf.PdfReader(filepath)
        linhas = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                for l in t.split('\n'):
                    l_str = l.strip()
                    if l_str:
                        linhas.append(l_str)
        
        # Filtra linhas indesejadas (links, cabeçalhos repetitivos)
        linhas_filtradas = []
        for l in linhas:
            if l.startswith("https://") or l.startswith("http://"):
                continue
            if l in ["Flashcards", "Exercite estas frases copiando-as para seu caderno, para o Anki, e sempre ouvindo e repetindo os", "áudios. Você também poderá recortar os Cards para estudar! Bons estudos!", "áudios. Você também poderá recortar os Cards para estudar! Bons estudos"]:
                continue
            if re.match(r"^Deck \d+:", l):
                continue
            linhas_filtradas.append(l)

        # Agrupa em pares (Inglês, Português)
        pares = []
        i = 0
        while i < len(linhas_filtradas):
            item = linhas_filtradas[i]
            # Se for título de tópico repetido no topo, ignora
            if i + 1 < len(linhas_filtradas):
                prox = linhas_filtradas[i+1]
                # Se o próximo for tradução em português (ou tiver texto)
                pares.append((item, prox))
                i += 2
            else:
                pares.append((item, ""))
                i += 1
        return pares
    except Exception as e:
        print(f"Erro ao extrair {filepath}: {e}")
        return []

def carregar_todos_os_decks():
    """Carrega todos os arquivos da pasta docs/ organizando em dicionário por nome."""
    arquivos = glob.glob(os.path.join(DOCS_DIR, "*.pdf"))
    decks = {}
    for f in sorted(arquivos):
        name = os.path.basename(f)
        if "Justicativa" in name:
            continue  # Ignora arquivo não relacionado a inglês
        
        pares = extrair_cards_do_pdf(f)
        decks[name] = pares
    return decks

# ==========================================
# 2. MAPEAMENTO E ESTRUTURA DO CURSO (AULAS)
# ==========================================
CURRICULO = [
    {
        "modulo": "MÓDULO 1: Primeiros Passos & Cumprimentos",
        "descricao": "Fundamentos essenciais para iniciar qualquer conversa em inglês com segurança.",
        "aulas": [
            {
                "titulo": "Aula 01: Cumprimentos & Se Apresentando (Greetings & Intro)",
                "dica_professor": "Em inglês, a forma de cumprimentar varia com o horário e o nível de formalidade. Lembre-se: 'Good evening' é para quando você chega e 'Good night' é exclusivamente para quando você se despede ou vai dormir!",
                "arquivos": ["Deck_1_Greetings.pdf", "Deck_2_Introducing+yourself.pdf"]
            },
            {
                "titulo": "Aula 02: Origens, Países & Nacionalidades",
                "dica_professor": "Ao falar de onde você é, use 'I am from Brazil' (Eu sou do Brasil). Para dizer sua nacionalidade, use 'I am Brazilian'. Note que em inglês as nacionalidades SEMPRE começam com letra maiúscula!",
                "arquivos": ["Deck_3_Where+are+you+from.pdf", "Deck_61_Nationalities+and+Countries.pdf", "Nacionalidades+em+Inglês.pdf"]
            },
            {
                "titulo": "Aula 03: Alfabeto & Soletrando ('How do you spell that?')",
                "dica_professor": "Soletrar é fundamental no ambiente corporativo (ao confirmar e-mails, nomes de repositórios ou chamados). Treine a pronúncia das vogais: A (Éi), E (Í), I (Ái), O (Óu), U (Iú).",
                "arquivos": ["Deck_4_How+do+you+spell+that.pdf"]
            },
            {
                "titulo": "Aula 04: Números, Dias da Semana & Meses",
                "dica_professor": "Os dias da semana e meses do ano em inglês TAMBÉM exigem letra maiúscula inicial (ex: Monday, January). Preposição para dias da semana: use 'ON' (On Monday, On Friday).",
                "arquivos": ["Deck_5_Numbers.pdf", "Deck_23_Days+of+Week+_+Month.pdf"]
            },
            {
                "titulo": "Aula 05: Cores & Características Pessoais",
                "dica_professor": "Em inglês, os adjetivos vêm ANTES do substantivo e nunca vão para o plural (ex: 'blue cars' e não 'blues cars').",
                "arquivos": ["Deck_18_Colors.pdf", "Deck_16_Características+Pessoais.pdf"]
            }
        ]
    },
    {
        "modulo": "MÓDULO 2: Estrutura Gramatical Básica",
        "descricao": "Domine o verbo To Be, pronomes, demonstrativos e artigos.",
        "aulas": [
            {
                "titulo": "Aula 06: Pronomes Pessoais & O Verbo 'To Be'",
                "dica_professor": "O verbo 'To Be' significa 'Ser' ou 'Estar'. Suas formas no presente são AM, IS e ARE. Para fazer perguntas, basta inverter a ordem: 'Are you ready?' em vez de 'You are ready'.",
                "arquivos": ["Deck_6_Subject+Pronouns.pdf", "Deck_7_To+be.pdf", "Deck_8_To+be+2.pdf", "Deck_9_To+be+3.pdf"]
            },
            {
                "titulo": "Aula 07: Pronomes Demonstrativos (This, These, That, Those)",
                "dica_professor": "Use 'THIS' (este/esta - perto no singular), 'THESE' (estes/estas - perto no plural), 'THAT' (aquele/aquela - longe no singular) e 'THOSE' (aqueles/aquelas - longe no plural).",
                "arquivos": ["Deck_10_This+_+These+_+That+_+Those.pdf"]
            },
            {
                "titulo": "Aula 08: Possessivos (Possessives & Adjetivos)",
                "dica_professor": "Possessivos indicam de quem é o objeto: My (meu), Your (seu), His (dele), Her (dela), Our (nosso), Their (deles). Nunca mudam para o plural!",
                "arquivos": ["Deck_11_Possessives.pdf", "Deck_22_Possessives.pdf"]
            },
            {
                "titulo": "Aula 09: Artigos (A, An, The)",
                "dica_professor": "Use 'A' antes de som de consoante ('a book') e 'AN' antes de som de vogal ('an apple', 'an hour'). Use 'THE' para coisas específicas já conhecidas.",
                "arquivos": ["Deck_19_Articles.pdf"]
            },
            {
                "titulo": "Aula 10: O Verbo 'Haver' (There is / There are)",
                "dica_professor": "Não use o verbo 'Have' para dizer que existe algo! Em inglês, use 'THERE IS' (singular) e 'THERE ARE' (plural) para dizer 'Existe / Há'.",
                "arquivos": ["Deck_58_Haver.pdf"]
            }
        ]
    },
    {
        "modulo": "MÓDULO 3: Ações do Dia a Dia & Present Simple",
        "descricao": "Aprenda a falar sobre sua rotina, hábitos diários e regras do presente.",
        "aulas": [
            {
                "titulo": "Aula 11: Present Simple (Regras & Terceira Pessoa)",
                "dica_professor": "Na 3ª pessoa do singular (He, She, It), adicione um 'S' ao verbo no afirmativo (ex: 'He works'). Nas negativas e perguntas, use o auxiliar DOES / DOESN'T.",
                "arquivos": ["Deck_20_Present+Simple+1.pdf", "Deck_21_Present+Simple+2.pdf"]
            },
            {
                "titulo": "Aula 12: Hábitos, Rotinas & Frequência",
                "dica_professor": "Expressões como 'every day', 'usually', 'always' acompanham o Present Simple para relatar seu dia de trabalho e tarefas diárias.",
                "arquivos": ["Deck_55_Habits+_+Routine.pdf"]
            },
            {
                "titulo": "Aula 13: Diferença entre 'DO' e 'MAKE'",
                "dica_professor": "Dica de ouro: Use 'DO' para tarefas, deveres e atividades gerais ('do homework', 'do a favor'). Use 'MAKE' para criar, produzir ou construir algo ('make coffee', 'make a decision').",
                "arquivos": ["Deck_57_Do+_+Make.pdf"]
            },
            {
                "titulo": "Aula 14: Preposições de Tempo e Lugar (IN, ON, AT)",
                "dica_professor": "Regra da Pirâmide: 'IN' é geral/grande (anos, meses, cidades), 'ON' é intermediário (dias da semana, datas, ruas), 'AT' é específico/exato (horas, endereços com número, 'at home').",
                "arquivos": ["Deck_25_Preposition+of+Time+_+Place.pdf", "Deck_64_Prepositions+of+Place+-+Review.pdf"]
            }
        ]
    },
    {
        "modulo": "MÓDULO 4: Vocabulário Temático Prático",
        "descricao": "Vocabulário do cotidiano para expandir seu repertório de palavras.",
        "aulas": [
            {
                "titulo": "Aula 15: Roupas & A Casa (Clothing & House)",
                "dica_professor": "Aprenda os nomes dos cômodos da casa e itens de vestuário para aplicar em conversas informais.",
                "arquivos": ["Deck_30_Clothing.pdf", "Deck_63_House.pdf"]
            },
            {
                "titulo": "Aula 16: Animais & Natureza (Animals & Nature)",
                "dica_professor": "Vocabulário útil sobre o meio ambiente, clima e animais.",
                "arquivos": ["Deck_27_Animal.pdf", "Deck_66_Nature+-+Lesson.pdf"]
            },
            {
                "titulo": "Aula 17: Meios de Transporte & Deslocamento",
                "dica_professor": "Para dizer 'ir de carro/ônibus/trem', use 'by car', 'by bus', 'by train'. Mas para dizer 'a pé', use a preposição 'ON foot'.",
                "arquivos": ["Deck_28_Transportation.pdf", "Deck_65_Means+of+Transportation.pdf"]
            },
            {
                "titulo": "Aula 18: Direções, Esportes & Entretenimento",
                "dica_professor": "Como pedir informações no trânsito ('turn left', 'go straight') e falar sobre hobbies no tempo livre.",
                "arquivos": ["Deck_67_Directions+-+Lesson.pdf", "Deck_62_Sports.pdf", "Deck_68_Entertainment+-+Lesson.pdf"]
            }
        ]
    },
    {
        "modulo": "MÓDULO 5: O Passado & Verbos Irregulares",
        "descricao": "Domine a comunicação sobre eventos passados e relatórios de trabalho.",
        "aulas": [
            {
                "titulo": "Aula 19: Simple Past (Verbos Regulares & Expressões)",
                "dica_professor": "Em verbos regulares, adicionamos '-ED' para o passado ('worked', 'played'). O verbo auxiliar no passado para perguntas e negativas é DID / DIDN'T.",
                "arquivos": ["Deck_59_Past.pdf"]
            },
            {
                "titulo": "Aula 20: To Be no Passado (Was / Were)",
                "dica_professor": "'WAS' é usado para I, He, She, It ('I was at work'). 'WERE' é usado para You, We, They ('We were in a meeting').",
                "arquivos": ["Deck_69_To+be+-+Past.pdf"]
            },
            {
                "titulo": "Aula 21: Guia dos Verbos Irregulares Mais Comuns",
                "dica_professor": "Verbos irregulares não seguem a regra do '-ED'. Eles têm formas próprias no passado (ex: Go → Went, See → Saw, Take → Took). Memorize a lista praticando diariamente!",
                "arquivos": ["most-common-irregular-verbs.pdf"]
            },
            {
                "titulo": "Aula 22: Pronúncia do 'R' em Inglês",
                "dica_professor": "O 'R' em inglês americano é bem enrolado (como no 'caipira' do interior de SP em 'porta/caipira'). Nunca arranhe a garganta como no 'R' do português carioca/paulistano!",
                "arquivos": ["Deck_54_Pronúncia+-+R.pdf"]
            }
        ]
    },
    {
        "modulo": "MÓDULO 6: O Futuro & Verbos Modais",
        "descricao": "Expresse planos futuros, possibilidades, obrigações e conselhos.",
        "aulas": [
            {
                "titulo": "Aula 23: Futuro com 'Going to' (Planos & Intenções)",
                "dica_professor": "Use 'BE GOING TO' para planos já decididos e intenções futuras ('I am going to study English tonight'). Na fala rápida, soa como 'gonna'.",
                "arquivos": ["Deck_70_Going+to.pdf"]
            },
            {
                "titulo": "Aula 24: Verbos Modais (Can, Could, Should, Must)",
                "dica_professor": "CAN = habilidade/permissão ('I can code'); COULD = possibilidade/pedido educado ('Could you help me?'); SHOULD = conselho ('You should rest'); MUST = obrigação/necessidade.",
                "arquivos": ["Deck_73_Modal+Verbs.pdf"]
            },
            {
                "titulo": "Aula 25: Interação Social & Diálogos (Interacting 1 & 2)",
                "dica_professor": "Frases prontas para manter conversas fluidas em reuniões, pequenos encontros e interações de trabalho.",
                "arquivos": ["Deck_71_Interacting+1.pdf", "Deck_72_Interacting+2.pdf"]
            }
        ]
    },
    {
        "modulo": "MÓDULO 7: Imersão & Frases Essenciais de Trabalho",
        "descricao": "Frases do dia a dia corporativo, expressões de imersão e exercícios de fixação.",
        "aulas": [
            {
                "titulo": "Aula 26: Frases do Dia a Dia & Post-its de Imersão",
                "dica_professor": "Coloque post-its com essas frases no seu monitor ou ambiente de estudo para acelerar a memorização involuntária!",
                "arquivos": ["Deck_75_Frases+do+Dia+a+Dia+-+1.pdf", "Imersao-PostIts.pdf", "Deck_26_Vocabulário+-+Imersão+01.pdf"]
            },
            {
                "titulo": "Aula 27: Como Estudar com Flashcards (Manual do Aluno)",
                "dica_professor": "A técnica de Repetição Espaçada (SRS) é o método científico mais eficiente para dominar vocabulário em tempo recorde.",
                "arquivos": ["ManualFC.pdf"]
            },
            {
                "titulo": "Aula 28: Compilação de Exercícios Práticos & Desafios",
                "dica_professor": "Testes práticos para consolidar todo o aprendizado abordado nas aulas anteriores.",
                "arquivos": ["Ingles+Extremo+1.0+-+Exercise+Compilation.pdf"]
            }
        ]
    }
]

# ==========================================
# 3. GERADOR DO DOCUMENTO MARKDOWN (.MD)
# ==========================================
def gerar_markdown(decks_dados):
    md = []
    md.append("# 🗺️ MAPA DE ESTUDOS DE INGLÊS DO ZERO AO AVANÇADO\n")
    md.append("> **Guia Completo de Aprendizado Estruturado com Explicações do Professor**\n")
    md.append("Este mapa de estudos consolida todo o conteúdo dos 48 decks da pasta `docs/` em um curso passo a passo, sem links quebrados, organizado por aulas e módulos de aprendizado.\n\n")

    md.append("---")
    
    for mod in CURRICULO:
        md.append(f"\n## {mod['modulo']}")
        md.append(f"*{mod['descricao']}*\n")
        
        for aula in mod["aulas"]:
            md.append(f"### 📘 {aula['titulo']}")
            md.append(f"> 💡 **DICA DO PROFESSOR:** {aula['dica_professor']}\n")
            
            # Coleta os termos dos arquivos desta aula
            termos_aula = []
            for arq in aula["arquivos"]:
                if arq in decks_dados:
                    termos_aula.extend(decks_dados[arq])
            
            if termos_aula:
                md.append("| Termo em Inglês | Tradução / Significado |")
                md.append("| :--- | :--- |")
                vistos = set()
                for eng, pt in termos_aula:
                    key = (eng.strip().lower(), pt.strip().lower())
                    if key in vistos or not eng.strip():
                        continue
                    vistos.add(key)
                    # Limpa quebras de linha dentro das células
                    eng_clean = eng.replace("\n", " ").replace("|", "/")
                    pt_clean = pt.replace("\n", " ").replace("|", "/")
                    md.append(f"| **{eng_clean}** | {pt_clean} |")
                md.append("\n")
            else:
                md.append("*Conteúdo prático/exercícios explicados no guia do aluno.*\n")
    
    md.append("\n---\n")
    md.append("### 🎯 COMO EXECUTAR SEU PLANO DE ESTUDOS DIÁRIO\n")
    md.append("1. Estudando 1 Aula por dia, você concluirá todo o mapa em **28 Dias**.\n")
    md.append("2. Use o **Timer Pomodoro** na aplicação (aba `⏱️ Timer Pomodoro`) em blocos de 30 minutos de foco.\n")
    md.append("3. Para qualquer termo que queira ouvir a pronúncia nativa ou ver exemplos no trabalho, use a aba `🔎 Consultar IA` do **Language Buddy**.\n")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Markdown gerado com sucesso: {OUTPUT_MD}")

# ==========================================
# 4. GERADOR DO DOCUMENTO PDF (REPORTLAB)
# ==========================================
def gerar_pdf(decks_dados):
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Cores personalizadas
    PRIMARY = colors.HexColor("#1E293B")
    SECONDARY = colors.HexColor("#3B82F6")
    TEXT_DARK = colors.HexColor("#0F172A")
    ACCENT = colors.HexColor("#F59E0B")
    BG_LIGHT = colors.HexColor("#F1F5F9")
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=25
    )
    
    mod_style = ParagraphStyle(
        'ModStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=PRIMARY,
        spaceBefore=15,
        spaceAfter=5
    )

    mod_desc_style = ParagraphStyle(
        'ModDescStyle',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12
    )

    aula_style = ParagraphStyle(
        'AulaStyle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4
    )
    
    dica_style = ParagraphStyle(
        'DicaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=8
    )

    cell_eng_style = ParagraphStyle(
        'CellEng',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=TEXT_DARK
    )

    cell_pt_style = ParagraphStyle(
        'CellPt',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334155")
    )
    
    header_table_style = ParagraphStyle(
        'HeaderTable',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.white
    )

    story = []
    
    # ------------------------------------------
    # CAPA / CABEÇALHO DO PDF
    # ------------------------------------------
    story.append(Paragraph("🗺️ MAPA DE ESTUDOS DE INGLÊS", title_style))
    story.append(Paragraph("Guia de Aprendizado Passo a Passo — Do Zero ao Avançado<br/><i>Compilação Exclusiva de Decks de Estudo & Orientações Práticas</i>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=SECONDARY, spaceBefore=0, spaceAfter=15))
    
    # Box de Introdução do Professor
    intro_p = Paragraph(
        "<b>👨‍🏫 MENSAGEM DO PROFESSOR:</b><br/>"
        "Seja bem-vindo ao seu Mapa de Estudos definitivo! Este documento foi criado analisando e integrando todo o conteúdo dos seus 48 Decks de Estudo. "
        "Removemos todos os links desnecessários e organizamos o material em uma sequência pedagógica lógica. "
        "Siga uma Aula por dia, utilize a aba <b>🔎 Consultar IA</b> do seu aplicativo para ouvir a pronúncia e boa jornada!",
        ParagraphStyle('IntroBox', parent=styles['Normal'], fontSize=9.5, leading=14, textColor=PRIMARY)
    )
    intro_table = Table([[intro_p]], colWidths=[520])
    intro_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('CORNER-RADIUS', (0, 0), (-1, -1), 6),
    ]))
    story.append(intro_table)
    story.append(Spacer(1, 15))
    
    # ------------------------------------------
    # CONTEÚDO DOS MÓDULOS E AULAS
    # ------------------------------------------
    for mod in CURRICULO:
        story.append(Paragraph(mod['modulo'].upper(), mod_style))
        story.append(Paragraph(mod['descricao'], mod_desc_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=0, spaceAfter=8))
        
        for aula in mod["aulas"]:
            story.append(Paragraph(aula['titulo'], aula_style))
            
            # Dica do professor em box de aviso
            dica_p = Paragraph(f"<b>💡 DICA DO PROFESSOR:</b> {aula['dica_professor']}", dica_style)
            dica_box = Table([[dica_p]], colWidths=[520])
            dica_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(dica_box)
            story.append(Spacer(1, 6))

            # Tabela de Termos
            termos_aula = []
            for arq in aula["arquivos"]:
                if arq in decks_dados:
                    termos_aula.extend(decks_dados[arq])

            if termos_aula:
                table_data = [[
                    Paragraph("Termo em Inglês", header_table_style),
                    Paragraph("Tradução / Significado em Português", header_table_style)
                ]]
                
                vistos = set()
                for eng, pt in termos_aula:
                    key = (eng.strip().lower(), pt.strip().lower())
                    if key in vistos or not eng.strip():
                        continue
                    vistos.add(key)
                    
                    eng_clean = eng.replace("\n", " ")
                    pt_clean = pt.replace("\n", " ")
                    
                    table_data.append([
                        Paragraph(eng_clean, cell_eng_style),
                        Paragraph(pt_clean, cell_pt_style)
                    ])
                
                if len(table_data) > 1:
                    t = Table(table_data, colWidths=[240, 280])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("<i>Consulte o arquivo de exercícios e manual prático.</i>", cell_pt_style))
                story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 10))
    
    # Constrói o PDF
    doc.build(story)
    print(f"PDF gerado com sucesso: {OUTPUT_PDF}")

if __name__ == "__main__":
    print("Iniciando processamento dos PDFs...")
    decks_dados = carregar_todos_os_decks()
    print(f"Decks carregados: {len(decks_dados)}")
    
    print("Gerando arquivo Markdown...")
    gerar_markdown(decks_dados)
    
    print("Gerando arquivo PDF consolidado...")
    gerar_pdf(decks_dados)
    print("Concluído!")
