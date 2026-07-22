# 🇬🇧 Language Buddy — Professor Virtual & Painel de Estudos de Inglês para Profissionais

O **Language Buddy** é um aplicativo desktop completo e moderno desenvolvido em Python e CustomTkinter, criado sob medida para ajudar profissionais brasileiros (especialmente das áreas de **TI, RPA, Software, Produto e Negócios**) a dominarem o inglês de trabalho com **pronúncia fonética abrasileirada**, **interação por voz com IA**, **leitor de PDFs** e **técnica Pomodoro**.

---

## 🚀 Funcionalidades Principais

### 1. 🎙️ Professor Alex (Mentor Virtual Interativo de IA)
- **Modo Conversa Viva (Hands-Free)**: Alternador no estilo ChatGPT Voice que escuta você automaticamente após cada fala do professor, sem precisar clicar repetidamente no botão do microfone.
- **Reconhecimento de Voz Inteligente**: Suporta transcrição ultra-precisa offline com `faster-whisper` (Local) e fallback automático para a API do Google.
- **Voz Neural Realista**: Fala com pronúncia fluida em Português e Inglês usando sintetizador neural (`edge-tts` / `gTTS`) com ajuste de velocidade (**1.0x**, **1.25x**, **1.5x**).
- **Dicas de Articulação Língua/Boca**: Cada explicação traz uma dica física prática da posição da língua/boca e macetes mentais para destravar a fala.
- **Storytelling de Escritório**: Vocabulário contextualizado com reuniões reais, daily standups, prazos, pull requests e e-mails de trabalho.


### 2. 🔎 Consultar IA ("Abrasileirar Termos")
- Tradução imediata e contextualizada para o ambiente corporativo.
- Pronúncia fonética no "jeitão brasileiro" (ex: *Schedule* → `"SKÉ-djiul"`, *Framework* → `"FRÉIM-uôrk"`).
- Exemplos práticos de uso no dia a dia com tradução.
- Botão de áudio para **🔊 Ouvir a Pronúncia em Inglês**.
- Execução assíncrona (a interface gráfica nunca congela durante a resposta).

### 3. 📖 Meu Caderno de Estudos (Vocabulário Salvo)
- Armazenamento automático em banco de dados SQLite local (`estudos.db`).
- Busca em tempo real por termo, tradução ou pronúncia fonética.
- Botões diretos para **Ouvir a Pronúncia** ou **Excluir** qualquer item salvo.
- **Exportação para CSV**: Permite exportar seus estudos para Excel ou planilhas do Google.

### 4. 📚 Leitor de Decks & Documentos (PDFs Integrados)
- Leitor integrado de arquivos PDF sem necessidade de softwares externos.
- Navegação entre todos os materiais de estudo da pasta `docs/`.
- **Pesquisa Global de Termos**: Encontra trechos de palavras-chave em dezenas de PDFs simultaneamente, exibindo páginas e trechos correspondentes.
- **Integração Inteligente**: Selecione qualquer palavra no PDF e clique em **⚡ Abrasileirar Seleção** ou **💾 Salvar Seleção no Caderno**.

### 5. ⏱️ Timer Pomodoro de Estudos
- Cronômetro regressivo com modos de **Foco (30 min)** e **Pausa Curta (5 min)**.
- Barra de progresso visual com botões de Iniciar, Pausar e Reiniciar.
- Alerta sonoro suave ao concluir os ciclos.

### 6. ⚙️ Painel de Configurações
- Gerenciamento de chave de API do **OpenRouter** diretamente na interface gráfica.
- Suporte a modelos de IA gratuitos ou de alta performance (ex: `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`).

### 7. ⌨️ Atalhos de Teclado Globais
- **`Esc`**: Interrompe imediatamente qualquer áudio ou voz do professor em reprodução.
- **`Ctrl + F`**: Alterna para a aba de **Decks de Estudo** e foca automaticamente no campo de busca de PDFs.
- **`Enter`**: Envia mensagens no chat do professor ou dispara consultas na busca da IA.

---

## 🧪 Testes Automatizados

Para rodar a suíte de testes unitários dos serviços (banco SQLite, síntese de áudio, parsers de IA e leitor PDF):

```bash
python -m unittest tests/test_services.py
```

---

## 📦 Gerar Executável Standalone (.exe)

Para gerar uma versão executável em um único arquivo `.exe` para Windows:

```bash
python scripts/build_exe.py
```
O arquivo `.exe` será gerado na pasta `dist/LanguageBuddy.exe`.

---

## 🛠️ Pré-requisitos & Instalação

### 1. Requisitos do Sistema
- **Python 3.9+** instalado na sua máquina.
- Conexão com a internet (para síntese de voz e consultas de IA).

### 2. Instalação das Dependências

Clone este repositório e navegue até a pasta do projeto:

```bash
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd "Desenvolvimento - Ingles"
```

Crie e ative um ambiente virtual (recomendado):

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências listadas no `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 🔑 Obter Chave Gratuita da API do OpenRouter

1. Acesse [openrouter.ai](https://openrouter.ai) e crie uma conta gratuita.
2. Acesse a aba **Keys** no menu de usuário e clique em **Create Key**.
3. Copie a chave gerada (ex: `sk-or-v1-...`).
4. Abra o aplicativo **Language Buddy**, navegue até a aba **⚙️ Configurações** e cole sua chave.

---

## 🖥️ Como Executar a Aplicação

Com o ambiente virtual ativado, execute:

```bash
python app.py
```

---

## 📁 Estrutura do Projeto

```plaintext
Desenvolvimento - Ingles/
│
├── docs/                      # Coleção de PDFs dos Decks de Estudo
├── services/                  # Módulos e serviços da aplicação
│   ├── ai_service.py          # Conexão HTTP com a API OpenRouter
│   ├── audio_service.py       # Reconhecimento de voz (STT) e síntese neural (TTS)
│   ├── config.py              # Leitura e escrita de configurações (config.json)
│   ├── database.py            # Gestão do banco SQLite (estudos.db) e exportação CSV
│   ├── docs_service.py        # Leitura e busca de textos em PDFs (pypdf)
│   ├── logger.py              # Módulo centralizado de logging (app.log e console)
│   └── teacher_service.py     # Lógica do Professor Alex e parser de respostas JSON
│
├── views/                     # Componentes visuais modulares da interface CustomTkinter
│   ├── teacher_view.py        # Aba do Professor Virtual (Voz e Chat)
│   ├── ia_view.py             # Aba de Consulta à IA (Abrasileirar Termos)
│   ├── caderno_view.py        # Aba do Caderno de Estudos (CRUD & CSV)
│   ├── docs_view.py           # Aba do Leitor e Buscador de PDFs
│   ├── pomodoro_view.py       # Aba do Timer Pomodoro
│   └── config_view.py         # Aba de Configurações de API, Modelo e Voz Neural
│
├── tests/                     # Testes automatizados do sistema
│   └── test_services.py       # Suíte de testes unitários
│
├── scripts/                   # Scripts auxiliares do projeto
│   ├── build_exe.py           # Script para compilação do executável (.exe)
│   └── gerar_mapa_estudos.py  # Script gerador de mapas de estudo
│
├── app.py                     # Inicializador principal da aplicação Desktop
├── requirements.txt           # Lista de dependências Python
├── .gitignore                 # Arquivos ignorados pelo Git (chaves de API, banco local, venv)
└── README.md                  # Documentação do projeto
```

---

## 🔒 Privacidade & Segurança

- **Chaves de API**: Sua chave do OpenRouter fica salva localmente em um arquivo `config.json` na sua máquina e nunca é enviada a repositórios públicos (protegida pelo `.gitignore`).
- **Banco de Dados Local**: Seus termos de estudo são armazenados apenas no arquivo `estudos.db` na sua própria máquina.
