// ----------------------------------------------------
// LANGUAGE BUDDY - PWA CLIENT CONTROLLER (OFFLINE-READY)
// ----------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initPWA();
  initNetworkMonitor();
  initNavigation();
  initTeacher();
  initCaderno();
  initPractice();
  initDocs();
  initConfig();
});

// Toast Helper
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast show";
  setTimeout(() => {
    toast.className = "toast";
  }, 2500);
}

// ----------------------------------------------------
// 1. MONITOR DE CONEXÃO (ONLINE / OFFLINE) & PWA
// ----------------------------------------------------
function initNetworkMonitor() {
  const statusBadge = document.querySelector(".header-status");

  function atualizarStatus() {
    if (navigator.onLine) {
      statusBadge.innerHTML = `<span class="status-dot"></span><span>Online</span>`;
      statusBadge.style.color = "var(--accent-green)";
      statusBadge.style.background = "var(--accent-green-bg)";
      // Sincroniza dados que foram criados offline
      sincronizarFilaOffline();
    } else {
      statusBadge.innerHTML = `<span>✈️ Modo Offline</span>`;
      statusBadge.style.color = "#f59e0b";
      statusBadge.style.background = "rgba(245, 158, 11, 0.15)";
      showToast("✈️ Você está offline. Recursos locais ativados!");
    }
  }

  window.addEventListener("online", atualizarStatus);
  window.addEventListener("offline", atualizarStatus);
  atualizarStatus();
}

function initPWA() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js")
      .then(() => console.log("[PWA] Service Worker ativo com suporte offline."))
      .catch((err) => console.log("[PWA] Falha no Service Worker:", err));
  }
}

// ----------------------------------------------------
// 2. NAVEGAÇÃO POR ABAS (BOTTOM NAVIGATION BAR)
// ----------------------------------------------------
function initNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  const tabViews = document.querySelectorAll(".tab-view");

  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTabId = btn.getAttribute("data-tab");

      navButtons.forEach((b) => b.classList.remove("active"));
      tabViews.forEach((t) => t.classList.remove("active"));

      btn.classList.add("active");
      const targetView = document.getElementById(targetTabId);
      if (targetView) targetView.classList.add("active");

      if (targetTabId === "tab-caderno") carregarCaderno();
      if (targetTabId === "tab-docs") carregarDocs();
    });
  });
}

// ----------------------------------------------------
// 3. SÍNTESE E REPRODUÇÃO DE ÁUDIO COM FALLBACK OFFLINE
// ----------------------------------------------------
const audioPlayer = document.getElementById("global-audio-player");

function tocarAudio(texto, lang = "pt", voz = null) {
  if (!texto || !texto.trim()) return;

  // Se estiver sem conexão, aciona o sintetizador nativo do celular
  if (!navigator.onLine) {
    tocarAudioNativoOffline(texto, lang);
    return;
  }

  // Se online, tenta a voz neural de alta fidelidade do backend
  let url = `/api/audio/tts?texto=${encodeURIComponent(texto)}&lang=${lang}`;
  if (voz) url += `&voz=${encodeURIComponent(voz)}`;

  audioPlayer.src = url;
  audioPlayer.play().catch((err) => {
    console.log("[Áudio] Streaming online bloqueado ou indisponível. Acionando voz nativa:", err);
    tocarAudioNativoOffline(texto, lang);
  });
}

function tocarAudioNativoOffline(texto, lang = "pt") {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(texto);
    utterance.lang = lang === "en" ? "en-US" : "pt-BR";
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  } else {
    showToast("Sintetizador de voz não suportado.");
  }
}

// ----------------------------------------------------
// 4. MÓDULO DO PROFESSOR ALEX (CHAT & VOZ)
// ----------------------------------------------------
function initTeacher() {
  const chatMessages = document.getElementById("chat-messages");
  const textInput = document.getElementById("teacher-text-input");
  const btnSend = document.getElementById("btn-teacher-send");
  const btnMic = document.getElementById("btn-teacher-mic");
  const micText = document.getElementById("mic-text");

  // Inicia a primeira saudação pedagógica
  fetch("/api/teacher/start")
    .then((res) => res.json())
    .then((data) => {
      // Salva em cache para abertura offline
      localStorage.setItem("cached_teacher_start", JSON.stringify(data));
      renderizarMensagemProfessor(data);
      if (data.fala_audio_pt) {
        tocarAudio(data.fala_audio_pt);
      }
    })
    .catch(() => {
      // Fallback offline a partir do cache
      const cached = localStorage.getItem("cached_teacher_start");
      if (cached) {
        const data = JSON.parse(cached);
        renderizarMensagemProfessor(data);
      } else {
        renderizarMensagemProfessor({
          fala_audio_pt: "Fala Dev! Estamos no modo offline. Você pode consultar seu Caderno e treinar Pronúncia!",
          texto_chat: "### ✈️ Modo Offline Ativo\n\nVocê está sem conexão com a internet. O seu **Caderno de Estudos**, as **Lições de Pronúncia** e os **PDFs** continuam 100% disponíveis!",
          termo_en: "Practice makes perfect!",
          traducao_pt: "A prática leva à perfeição!",
          pronuncia_abrasileirada: "PRÉK-tiss MÊIKS PÉR-fekt"
        });
      }
    });

  btnSend.addEventListener("click", () => enviarMensagemAluno());
  textInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") enviarMensagemAluno();
  });

  function enviarMensagemAluno(textoCustom = null) {
    const texto = (textoCustom || textInput.value).trim();
    if (!texto) return;

    if (!navigator.onLine) {
      showToast("Conecte-se à internet para novas respostas da IA.");
      return;
    }

    const userMsg = document.createElement("div");
    userMsg.className = "message-card user-msg";
    userMsg.innerHTML = `<div style="font-weight: 500;">${escapeHtml(texto)}</div>`;
    chatMessages.appendChild(userMsg);
    textInput.value = "";
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const loadingCard = document.createElement("div");
    loadingCard.className = "message-card assistant-msg";
    loadingCard.id = "loading-card";
    loadingCard.innerHTML = `<div style="color: #a1a1aa; font-style: italic;">⏳ Professor Alex está formulando sua lição...</div>`;
    chatMessages.appendChild(loadingCard);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    fetch("/api/teacher/interact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem: texto })
    })
      .then((res) => res.json())
      .then((data) => {
        const loading = document.getElementById("loading-card");
        if (loading) loading.remove();

        renderizarMensagemProfessor(data);
        if (data.fala_audio_pt) {
          tocarAudio(data.fala_audio_pt);
        }
      })
      .catch(() => {
        const loading = document.getElementById("loading-card");
        if (loading) loading.remove();
        showToast("Erro ao conectar com a IA. Verifique sua conexão.");
      });
  }

  function renderizarMensagemProfessor(data) {
    const card = document.createElement("div");
    card.className = "message-card assistant-msg";

    let termoBlock = "";
    if (data.termo_en) {
      termoBlock = `
        <div class="card-focus-block">
          <div class="termo-en">
            <span>${escapeHtml(data.termo_en)}</span>
            <button class="btn-audio-play" onclick="tocarAudio('${escapeHtml(data.termo_en)}', 'en')">🔊 Ouvir Inglês</button>
          </div>
          ${data.pronuncia_abrasileirada ? `<div class="pronuncia-fonetica">🗣️ ${escapeHtml(data.pronuncia_abrasileirada)}</div>` : ''}
          ${data.traducao_pt ? `<div class="traducao-pt">🇧🇷 <strong>Tradução:</strong> ${escapeHtml(data.traducao_pt)}</div>` : ''}
          ${data.dica_articulacao ? `<div class="dica-boca">${escapeHtml(data.dica_articulacao)}</div>` : ''}
          <div style="margin-top: 6px;">
            <button class="btn-action-sec" style="padding: 6px 12px; font-size: 12px;" onclick="salvarNoCaderno('${escapeHtml(data.termo_en)}', '${escapeHtml(data.traducao_pt || '')}', '${escapeHtml(data.pronuncia_abrasileirada || '')}')">
              📖 Salvar no Meu Caderno
            </button>
          </div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="teacher-header-badge">
        <span>🎓 Professor Alex</span>
        ${data.fala_audio_pt ? `<button class="btn-audio-play" onclick="tocarAudio('${escapeHtml(data.fala_audio_pt)}')">🔊 Repetir Explicação</button>` : ''}
      </div>
      ${termoBlock}
      <div class="chat-markdown-text">${escapeHtml(data.texto_chat || data.fala_audio_pt || '')}</div>
      ${data.instrucao_aluno ? `<div style="font-size: 12px; color: #60a5fa; font-weight: 500;">👉 ${escapeHtml(data.instrucao_aluno)}</div>` : ''}
    `;

    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Microfone (Web Speech API)
  let recognition = null;
  if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechAPI();
    recognition.lang = "pt-BR";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      btnMic.classList.add("recording");
      micText.textContent = "Ouvindo você...";
    };

    recognition.onresult = (event) => {
      const transcricao = event.results[0][0].transcript;
      enviarMensagemAluno(transcricao);
    };

    recognition.onerror = () => {
      btnMic.classList.remove("recording");
      micText.textContent = "Falar no Microfone";
      showToast("Não consegui ouvir. Tente novamente.");
    };

    recognition.onend = () => {
      btnMic.classList.remove("recording");
      micText.textContent = "Falar no Microfone";
    };
  }

  btnMic.addEventListener("click", () => {
    if (recognition) {
      try {
        recognition.start();
      } catch (e) {
        recognition.stop();
      }
    } else {
      showToast("Microfone não disponível neste navegador. Digite sua mensagem.");
    }
  });
}

// ----------------------------------------------------
// 5. MÓDULO DO CADERNO COM SINCRONIZAÇÃO OFFLINE
// ----------------------------------------------------
function initCaderno() {
  const searchInput = document.getElementById("caderno-search-input");
  const btnExport = document.getElementById("btn-export-csv");

  searchInput.addEventListener("input", (e) => carregarCaderno(e.target.value));
  btnExport.addEventListener("click", () => {
    window.location.href = "/api/caderno/exportar-csv";
  });
}

function carregarCaderno(busca = "") {
  const listContainer = document.getElementById("caderno-list");
  const statsLabel = document.getElementById("caderno-stats");

  // Se estiver offline ou falhar a rede, carrega do localStorage local
  function renderizarDoCache() {
    const cached = JSON.parse(localStorage.getItem("cached_caderno_termos") || "[]");
    let termosFiltrados = cached;
    if (busca.trim()) {
      const b = busca.toLowerCase();
      termosFiltrados = cached.filter(t => 
        (t.termo_ingles && t.termo_ingles.toLowerCase().includes(b)) ||
        (t.traducao && t.traducao.toLowerCase().includes(b))
      );
    }
    statsLabel.textContent = `Total: ${cached.length} termo(s) (Cache Local)`;
    renderizarTermosCards(termosFiltrados, listContainer);
  }

  fetch(`/api/caderno/listar?busca=${encodeURIComponent(busca)}`)
    .then((res) => res.json())
    .then((data) => {
      if (!busca.trim()) {
        localStorage.setItem("cached_caderno_termos", JSON.stringify(data.termos || []));
      }
      statsLabel.textContent = `Total: ${data.estatisticas.total_termos || 0} termo(s) salvos`;
      renderizarTermosCards(data.termos || [], listContainer);
    })
    .catch(() => {
      renderizarDoCache();
    });
}

function renderizarTermosCards(termos, container) {
  container.innerHTML = "";
  if (!termos || termos.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: #71717a; padding: 40px 0;">Nenhum termo encontrado.</div>`;
    return;
  }

  termos.forEach((t) => {
    const card = document.createElement("div");
    card.className = "termo-card";
    card.innerHTML = `
      <div class="termo-top">
        <span style="font-size: 16px; font-weight: 700; color: #60a5fa;">${escapeHtml(t.termo_ingles)}</span>
        <div class="termo-actions">
          <button class="btn-icon" onclick="tocarAudio('${escapeHtml(t.termo_ingles)}', 'en')">🔊</button>
          <button class="btn-icon" style="color: #ef4444;" onclick="deletarDoCaderno(${t.id})">🗑️</button>
        </div>
      </div>
      <div style="font-size: 13px; color: #f59e0b; font-family: var(--font-mono); font-weight: 600;">"${escapeHtml(t.pronuncia_abrasileirada)}"</div>
      <div style="font-size: 13px; color: #e4e4e7;"><strong>Tradução:</strong> ${escapeHtml(t.traducao)}</div>
      ${t.exemplo_contexto ? `<div style="font-size: 12px; color: #a1a1aa; font-style: italic;">Exemplo: ${escapeHtml(t.exemplo_contexto)}</div>` : ''}
    `;
    container.appendChild(card);
  });
}

function salvarNoCaderno(termo, traducao, pronuncia) {
  const novoTermo = {
    termo_ingles: termo,
    traducao: traducao,
    pronuncia_abrasileirada: pronuncia,
    exemplo_contexto: "",
    traducao_exemplo: "",
    data_cadastro: new Date().toISOString()
  };

  // Se estiver offline, salva localmente e adiciona à fila de sincronização
  if (!navigator.onLine) {
    salvarTermoLocalmente(novoTermo);
    showToast("💾 Salvo localmente (será sincronizado quando online)!");
    return;
  }

  fetch("/api/caderno/salvar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(novoTermo)
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.sucesso) {
        showToast("⭐ Termo salvo no Caderno!");
        carregarCaderno();
      }
    })
    .catch(() => {
      salvarTermoLocalmente(novoTermo);
      showToast("💾 Salvo no armazenamento local offline!");
    });
}

function salvarTermoLocalmente(termo) {
  const cached = JSON.parse(localStorage.getItem("cached_caderno_termos") || "[]");
  termo.id = Date.now();
  cached.unshift(termo);
  localStorage.setItem("cached_caderno_termos", JSON.stringify(cached));

  // Adiciona na fila de sincronização
  const fila = JSON.parse(localStorage.getItem("offline_sync_queue") || "[]");
  fila.push(termo);
  localStorage.setItem("offline_sync_queue", JSON.stringify(fila));
}

function sincronizarFilaOffline() {
  const fila = JSON.parse(localStorage.getItem("offline_sync_queue") || "[]");
  if (fila.length === 0) return;

  Promise.all(
    fila.map(termo => 
      fetch("/api/caderno/salvar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(termo)
      })
    )
  ).then(() => {
    localStorage.removeItem("offline_sync_queue");
    console.log("[Sync] Termos criados offline sincronizados com o servidor.");
    carregarCaderno();
  }).catch(() => {});
}

function deletarDoCaderno(id) {
  if (confirm("Deseja excluir este termo do caderno?")) {
    if (!navigator.onLine) {
      const cached = JSON.parse(localStorage.getItem("cached_caderno_termos") || "[]");
      const atualizado = cached.filter(t => t.id !== id);
      localStorage.setItem("cached_caderno_termos", JSON.stringify(atualizado));
      showToast("Termo removido localmente.");
      carregarCaderno();
      return;
    }

    fetch(`/api/caderno/deletar/${id}`, { method: "DELETE" })
      .then((res) => res.json())
      .then(() => {
        showToast("Termo excluído.");
        carregarCaderno();
      });
  }
}

// ----------------------------------------------------
// 6. MÓDULO DE PRÁTICA E ESCUTA (100% OFFLINE-READY)
// ----------------------------------------------------
function initPractice() {
  const container = document.getElementById("practice-cards-list");
  const lessons = [
    {
      titulo: "🎙️ Daily Standup: Atualização & Impedimentos",
      frases: [
        { en: "Good morning team!", pron: "GÚD MÓR-nin TÍM!", pt: "Bom dia equipe!" },
        { en: "Yesterday I finished the API tests.", pron: "IÊS-ter-dei AI FÍ-nisht dhi EI-PI-AI TÉSTS.", pt: "Ontem terminei os testes da API." },
        { en: "I have no blockers right now.", pron: "AI HÉV NÔ BLÓ-kers RUÁIT NÁU.", pt: "Não tenho impedimentos agora." }
      ]
    },
    {
      titulo: "💻 Code Review & Pull Request",
      frases: [
        { en: "I just reviewed your pull request.", pron: "AI DJÂST ri-VIÚD iór PÚL ri-KWÉST.", pt: "Acabei de revisar seu pull request." },
        { en: "Please add proper error handling.", pron: "PLÍZ ÉD PRÓ-per É-ror HÉND-ling.", pt: "Por favor adicione tratamento de erros." },
        { en: "Let's merge it into main.", pron: "LÉTS MÉRDJ it ÍN-tu MÉIN.", pt: "Vamos juntar na branch main." }
      ]
    }
  ];

  lessons.forEach((l) => {
    const card = document.createElement("div");
    card.className = "practice-card";
    
    let itemsHtml = l.frases.map(f => `
      <div class="practice-phrase-box" style="margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; color: #60a5fa;">${escapeHtml(f.en)}</span>
          <button class="btn-icon" onclick="tocarAudio('${escapeHtml(f.en)}', 'en')">🔊</button>
        </div>
        <div style="font-size: 13px; color: #f59e0b; font-family: var(--font-mono);">${escapeHtml(f.pron)}</div>
        <div style="font-size: 12px; color: #d4d4d8;">${escapeHtml(f.pt)}</div>
      </div>
    `).join('');

    card.innerHTML = `
      <div class="practice-title">${escapeHtml(l.titulo)}</div>
      <div>${itemsHtml}</div>
    `;
    container.appendChild(card);
  });
}

// ----------------------------------------------------
// 7. MÓDULO DE DECKS & PDFS
// ----------------------------------------------------
function initDocs() {
  const searchInput = document.getElementById("docs-search-input");
  const modal = document.getElementById("pdf-modal");
  const btnClose = document.getElementById("btn-close-pdf");

  btnClose.addEventListener("click", () => {
    modal.style.display = "none";
  });

  searchInput.addEventListener("input", (e) => {
    const termo = e.target.value.trim();
    if (termo.length > 2) {
      buscarDocs(termo);
    } else if (termo.length === 0) {
      carregarDocs();
    }
  });
}

function carregarDocs() {
  const container = document.getElementById("docs-list");
  fetch("/api/docs/listar")
    .then((res) => res.json())
    .then((data) => {
      localStorage.setItem("cached_docs_list", JSON.stringify(data.documentos || []));
      renderizarListaDocs(data.documentos || [], container);
    })
    .catch(() => {
      const cached = JSON.parse(localStorage.getItem("cached_docs_list") || "[]");
      renderizarListaDocs(cached, container);
    });
}

function renderizarListaDocs(docs, container) {
  container.innerHTML = "";
  if (!docs || docs.length === 0) {
    container.innerHTML = `<div style="color: #71717a; padding: 20px 0;">Nenhum documento encontrado.</div>`;
    return;
  }

  docs.forEach((d) => {
    const item = document.createElement("div");
    item.className = "doc-item";
    item.innerHTML = `
      <div>
        <div style="font-weight: 600; font-size: 14px;">📄 ${escapeHtml(d.titulo)}</div>
        <div style="font-size: 11px; color: #a1a1aa;">${escapeHtml(d.filename)}</div>
      </div>
      <button class="btn-action-sec" style="font-size: 12px;" onclick="abrirPdf('${escapeHtml(d.filepath)}', '${escapeHtml(d.titulo)}')">Abrir ➔</button>
    `;
    container.appendChild(item);
  });
}

function abrirPdf(filepath, titulo) {
  const modal = document.getElementById("pdf-modal");
  const modalTitle = document.getElementById("pdf-modal-title");
  const modalBody = document.getElementById("pdf-modal-body");

  modalTitle.textContent = titulo;
  modalBody.textContent = "Carregando páginas do documento...";
  modal.style.display = "flex";

  const cacheKey = "cached_pdf_" + filepath;
  const cachedContent = localStorage.getItem(cacheKey);

  fetch(`/api/docs/ler?filepath=${encodeURIComponent(filepath)}`)
    .then((res) => res.json())
    .then((data) => {
      if (data.sucesso) {
        localStorage.setItem(cacheKey, data.texto_completo || "");
        modalBody.textContent = data.texto_completo || "Documento sem texto legível.";
      } else {
        modalBody.textContent = cachedContent || ("Erro ao carregar o PDF: " + data.erro);
      }
    })
    .catch(() => {
      if (cachedContent) {
        modalBody.textContent = cachedContent;
      } else {
        modalBody.textContent = "Você está offline e este documento ainda não foi baixado.";
      }
    });
}

function buscarDocs(termo) {
  const container = document.getElementById("docs-list");
  fetch(`/api/docs/buscar?termo=${encodeURIComponent(termo)}`)
    .then((res) => res.json())
    .then((data) => {
      container.innerHTML = "";
      if (!data.resultados || data.resultados.length === 0) {
        container.innerHTML = `<div style="color: #71717a; padding: 20px 0;">Nenhum trecho encontrado com '${escapeHtml(termo)}'.</div>`;
        return;
      }

      data.resultados.forEach((r) => {
        const item = document.createElement("div");
        item.className = "termo-card";
        let matchesHtml = r.matches.map(m => `
          <div style="font-size: 12px; color: #a1a1aa; margin-top: 4px; padding: 4px 8px; background: #09090b; border-radius: 6px;">
            <strong>Pág ${m.pagina}:</strong> ...${escapeHtml(m.trecho)}...
          </div>
        `).join('');

        item.innerHTML = `
          <div style="font-weight: 700; color: #60a5fa;">📄 ${escapeHtml(r.titulo)}</div>
          <div>${matchesHtml}</div>
        `;
        container.appendChild(item);
      });
    });
}

// ----------------------------------------------------
// 8. MÓDULO DE CONFIGURAÇÕES
// ----------------------------------------------------
function initConfig() {
  const keyInput = document.getElementById("cfg-api-key");
  const keyStatus = document.getElementById("cfg-key-status");
  const modelSelect = document.getElementById("cfg-model");
  const voiceSelect = document.getElementById("cfg-voice");
  const btnSave = document.getElementById("btn-save-config");

  fetch("/api/config/obter")
    .then((res) => res.json())
    .then((cfg) => {
      if (cfg.has_api_key) {
        keyStatus.textContent = "🔒 Chave protegida no cofre (" + cfg.masked_key + ")";
        keyStatus.style.color = "#22c55e";
      } else {
        keyStatus.textContent = "⚠️ Nenhuma chave cadastrada.";
        keyStatus.style.color = "#eab308";
      }

      if (cfg.model) modelSelect.value = cfg.model;
      if (cfg.voice) voiceSelect.value = cfg.voice;
    });

  btnSave.addEventListener("click", () => {
    const payload = {
      model: modelSelect.value,
      voice: voiceSelect.value
    };
    if (keyInput.value.trim()) {
      payload.api_key = keyInput.value.trim();
    }

    fetch("/api/config/salvar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.sucesso) {
          showToast("✅ Configurações salvas com sucesso!");
          keyInput.value = "";
          keyStatus.textContent = "🔒 Chave protegida no cofre!";
          keyStatus.style.color = "#22c55e";
        }
      });
  });
}

// Helper XSS
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
