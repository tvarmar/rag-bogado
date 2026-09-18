// RAG-Bogado Conversational Chat Engine
document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const typingIndicator = document.getElementById("typing-indicator");

  const resetChatBtn = document.getElementById("reset-chat-btn");
  const toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");
  const closeSidebarBtn = document.getElementById("close-sidebar-btn");
  const referencesSidebar = document.getElementById("references-sidebar");
  const referencesList = document.getElementById("references-list");
  const referencesCountBadge = document.getElementById("references-count");
  const sidebarBadgeCount = document.getElementById("sidebar-badge-count");

  const docsDropdownBtn = document.getElementById("docs-dropdown-btn");
  const docsDropdownMenu = document.getElementById("docs-dropdown-menu");
  const syncDocsBtn = document.getElementById("sync-docs-btn");
  const docsSelectedLabel = document.getElementById("docs-selected-label");
  const docsOptionsList = document.getElementById("docs-options-list");

  // Current selected document state (defaults to whole corpus)
  let currentDocumentId = "all";
  let availableDocuments = [];

  // Modal elements
  const sourceModal = document.getElementById("source-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalDismissBtn = document.getElementById("modal-dismiss-btn");
  const modalSourceId = document.getElementById("modal-source-id");
  const modalArticleTitle = document.getElementById("modal-article-title");
  const modalDocument = document.getElementById("modal-document");
  const modalPage = document.getElementById("modal-page");
  const modalUnit = document.getElementById("modal-unit");
  const modalChunkId = document.getElementById("modal-chunk-id");
  const modalSourceText = document.getElementById("modal-source-text");

  // Accumulated sources in the conversation session
  const conversationSources = new Map();

  const SUGGESTED_QUESTIONS = [
    {
      label: "Supervisión humana (IA)",
      query: "¿Cómo deben diseñarse los sistemas de IA de alto riesgo para garantizar la supervisión humana?",
      doc_id: "eu_ai_act"
    },
    {
      label: "Multas y sanciones (IA)",
      query: "¿A cuánto pueden ascender las multas administrativas por utilizar prácticas de IA prohibidas?",
      doc_id: "eu_ai_act"
    },
    {
      label: "Derechos digitales (RGPD)",
      query: "¿Qué derechos digitales reconoce la ley respecto al ámbito laboral y desconexión digital?",
      doc_id: "rgpd"
    },
    {
      label: "Plataformas en línea (DSA)",
      query: "¿Qué obligaciones de diligencia debida tienen las plataformas en línea respecto a contenidos ilícitos?",
      doc_id: "dsa"
    },
    {
      label: "Entidades esenciales (NIS2)",
      query: "¿Qué criterios definen a las entidades esenciales en materia de ciberseguridad?",
      doc_id: "nis2"
    },
    {
      label: "Prueba de abstención (materia ajena)",
      query: "¿Qué requisitos de etiquetado nutricional se exigen a los alimentos ecológicos?",
      doc_id: "eu_ai_act"
    }
  ];

  // 1. Initialize Conversation
  function initConversation() {
    conversationSources.clear();
    messagesContainer.innerHTML = "";
    updateReferencesSidebar();
    renderWelcomeMessage();
    setupDropdownControls();
    checkHealth();
  }

  // 2. Dropdown & Document Selection Setup
  function setupDropdownControls() {
    if (!docsDropdownBtn || !docsDropdownMenu) return;

    docsDropdownBtn.onclick = (e) => {
      e.stopPropagation();
      docsDropdownMenu.classList.toggle("hidden");
    };

    document.addEventListener("click", (e) => {
      if (!docsDropdownMenu.classList.contains("hidden") && !docsDropdownMenu.contains(e.target)) {
        docsDropdownMenu.classList.add("hidden");
      }
    });

    if (syncDocsBtn) {
      syncDocsBtn.onclick = (e) => {
        e.stopPropagation();
        handleSyncCorpus();
      };
    }

    fetchCorpusDocuments();
  }

  async function fetchCorpusDocuments() {
    try {
      const res = await fetch("/api/documents");
      if (!res.ok) return;
      const data = await res.json();
      availableDocuments = data.documents || [];
      renderDropdownOptions();
      updateSelectedDocDisplay();
    } catch (err) {
      console.warn("No se pudo cargar la lista de documentos:", err);
    }
  }

  function renderDropdownOptions() {
    if (!docsOptionsList || !availableDocuments.length) return;
    docsOptionsList.innerHTML = "";

    // 1. All documents option
    const allLabel = document.createElement("label");
    allLabel.className = "doc-checkbox-item";
    const isAllChecked = currentDocumentId === "all";
    allLabel.innerHTML = `
      <input type="radio" name="selected-doc" value="all" ${isAllChecked ? "checked" : ""}>
      <div class="doc-checkbox-info">
        <div class="doc-checkbox-title">📚 Todo el corpus oficial (4 normas)</div>
        <div class="doc-checkbox-meta">
          <span class="badge-mini badge-mini-active">Activo en catálogo</span>
          <span>Búsqueda simultánea en IA, RGPD, DSA y NIS2</span>
        </div>
      </div>
    `;
    const allRadio = allLabel.querySelector('input[type="radio"]');
    allRadio.onchange = () => {
      if (allRadio.checked) {
        currentDocumentId = "all";
        updateSelectedDocDisplay();
      }
    };
    docsOptionsList.appendChild(allLabel);

    // 2. Individual documents
    availableDocuments.forEach((doc) => {
      const label = document.createElement("label");
      label.className = "doc-checkbox-item";
      const isChecked = doc.id === currentDocumentId;
      const badgeClass = doc.active ? "badge-mini-active" : "badge-mini-planned";
      const badgeText = doc.active
        ? "Activo en catálogo"
        : (doc.sync_status === "failed" ? "Fallo sincro" : "Pendiente BOE");

      label.innerHTML = `
        <input type="radio" name="selected-doc" value="${escapeHtml(doc.id)}" ${isChecked ? "checked" : ""}>
        <div class="doc-checkbox-info">
          <div class="doc-checkbox-title">${escapeHtml(doc.short_name)} (${escapeHtml(doc.official_id)})</div>
          <div class="doc-checkbox-meta">
            <span class="badge-mini ${badgeClass}">${badgeText}</span>
            <span>${escapeHtml(doc.scope_description || doc.title)}</span>
          </div>
        </div>
      `;

      const radio = label.querySelector('input[type="radio"]');
      radio.onchange = () => {
        if (radio.checked) {
          currentDocumentId = doc.id;
          updateSelectedDocDisplay();
        }
      };

      docsOptionsList.appendChild(label);
    });
  }

  function updateSelectedDocDisplay() {
    if (currentDocumentId === "all") {
      if (docsSelectedLabel) {
        const activeCount = availableDocuments.filter((d) => d.active).length || 4;
        docsSelectedLabel.textContent = `Todo el corpus (${activeCount} normas activas)`;
      }
      if (userInput) {
        userInput.placeholder = "Haz una pregunta sobre el corpus normativo (IA, RGPD, DSA, NIS2)...";
      }
      return;
    }
    const doc = availableDocuments.find((d) => d.id === currentDocumentId);
    if (doc) {
      if (docsSelectedLabel) {
        docsSelectedLabel.textContent = `${doc.short_name} (${doc.active ? "Activo" : "Sin indexar"})`;
      }
      if (userInput) {
        userInput.placeholder = `Haz una pregunta sobre ${doc.short_name}...`;
      }
    }
  }

  async function handleSyncCorpus() {
    if (!syncDocsBtn) return;
    const origText = syncDocsBtn.innerHTML;
    syncDocsBtn.innerHTML = "⏳ Sincronizando...";
    syncDocsBtn.disabled = true;

    try {
      const res = await fetch("/api/documents/sync", { method: "POST" });
      await fetchCorpusDocuments();
      syncDocsBtn.innerHTML = "✅ Sincronizado";
      setTimeout(() => {
        syncDocsBtn.innerHTML = origText;
        syncDocsBtn.disabled = false;
      }, 2500);
    } catch (err) {
      syncDocsBtn.innerHTML = "❌ Error sincro";
      setTimeout(() => {
        syncDocsBtn.innerHTML = origText;
        syncDocsBtn.disabled = false;
      }, 2500);
    }
  }

  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) return;
      const data = await res.json();
      if (data.ollama_ready === false) {
        console.warn("Ollama daemon is not running on 127.0.0.1:11434");
      }
    } catch (err) {
      console.warn("Health check unreachable:", err);
    }
  }

  // 3. Render Welcome Card
  function renderWelcomeMessage() {
    const welcomeRow = document.createElement("div");
    welcomeRow.className = "message-row bot";

    welcomeRow.innerHTML = `
      <div class="msg-avatar">⚖️</div>
      <div class="msg-content-wrapper">
        <div class="welcome-card">
          <div class="welcome-header">
            <span class="welcome-icon">🏛️</span>
            <div>
              <h2 class="welcome-title">Bienvenida a RAG-Bogado</h2>
              <p class="brand-meta">Asistente conversacional para consultas jurídicas y regulatorias</p>
            </div>
          </div>
          <div class="welcome-body">
            <p>
              Hola, soy tu asistente para la consulta y análisis de normativa tecnológica.
              Mis respuestas se generan con <strong>trazabilidad estricta</strong>: cada afirmación se contrasta
              contra las fuentes y, si la evidencia no existe en el texto legal, declaro explícitamente la
              abstención en lugar de inventar.
            </p>
            <div class="official-doc-box">
              <div class="official-doc-title">Corpus normativo integrado con el BOE:</div>
              <ul style="margin: 0.4rem 0 0.6rem 1.2rem; padding: 0; font-size: 0.85rem; line-height: 1.5; color: #cbd5e1;">
                <li><strong>Reglamento de IA</strong> (DOUE-L-2024-81079) &bull; Inteligencia artificial en la UE</li>
                <li><strong>RGPD / LOPDGDD</strong> (BOE-A-2018-16673) &bull; Protección de datos personales</li>
                <li><strong>Servicios Digitales (DSA)</strong> (DOUE-L-2022-81573) &bull; Mercado único digital</li>
                <li><strong>Ciberseguridad (NIS 2)</strong> (DOUE-L-2022-81963) &bull; Ciberresiliencia europea</li>
              </ul>
              <div class="official-doc-meta" style="margin-bottom: 0.2rem;">
                <span><strong>Sincronización:</strong> Verificación automática contra el BOE en el arranque o acceso</span>
              </div>
            </div>
            <div class="suggested-questions-title">Consultas de ejemplo sugeridas:</div>
            <div class="suggestion-chips" id="welcome-suggestion-chips"></div>
          </div>
        </div>
        <span class="msg-time">${getCurrentTime()}</span>
      </div>
    `;

    messagesContainer.appendChild(welcomeRow);

    // Populate chips
    const chipsContainer = welcomeRow.querySelector("#welcome-suggestion-chips");
    SUGGESTED_QUESTIONS.forEach((item) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = item.label;
      chip.title = item.query;
      chip.onclick = () => {
        currentDocumentId = item.doc_id;
        updateSelectedDocDisplay();
        const radio = document.querySelector(`input[name="selected-doc"][value="${item.doc_id}"]`);
        if (radio) radio.checked = true;
        userInput.value = item.query;
        handleFormSubmit();
      };
      chipsContainer.appendChild(chip);
    });

    scrollToBottom();
  }

  // 4. Handle Form Submission
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleFormSubmit();
  });

  // Auto-resize textarea & Enter key support (Shift+Enter for new line)
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleFormSubmit();
    }
  });

  async function handleFormSubmit() {
    const text = userInput.value.trim();
    if (!text) return;

    // Append User Message
    appendUserMessage(text);
    userInput.value = "";
    adjustTextareaHeight(userInput);

    // Show Typing Indicator & disable button
    typingIndicator.classList.remove("hidden");
    sendBtn.disabled = true;
    scrollToBottom();

    const payload = {
      question: text,
      document_id: currentDocumentId,
      answer_mode: "evidence",
      search_count: 2,
      max_passages: 5
    };

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 503 && (data.detail || "").includes("Ollama")) {
          appendOllamaOfflineMessage(data.detail);
          return;
        }
        appendBotErrorMessage(
          `Error ${res.status}`,
          data.detail || "Error desconocido al procesar la consulta en el servidor."
        );
        return;
      }

      appendBotAnswerMessage(data);
    } catch (err) {
      appendBotErrorMessage(
        "Fallo de comunicación",
        err.message || "No se pudo conectar con el servidor local."
      );
    } finally {
      typingIndicator.classList.add("hidden");
      sendBtn.disabled = false;
      scrollToBottom();
    }
  }

  function appendOllamaOfflineMessage(detail) {
    const row = document.createElement("div");
    row.className = "message-row bot";
    row.innerHTML = `
      <div class="msg-avatar">⚠️</div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble alert-callout-warning" style="max-width: 650px;">
          <h4 style="margin: 0 0 0.4rem 0; color: #fbbf24; font-size: 0.95rem; display: flex; align-items: center; gap: 0.4rem;">
            <span>⚠️</span> Servicio LLM (Ollama) no disponible
          </h4>
          <p style="margin: 0 0 0.5rem 0; font-size: 0.85rem; line-height: 1.45; color: #fef3c7;">
            ${escapeHtml(detail || "El servicio local de generación no está activo en 127.0.0.1:11434.")}
          </p>
          <p style="margin: 0 0 0.25rem 0; font-size: 0.8rem; color: #94a3b8;">
            Para iniciar el motor LLM local, abre una terminal en la raíz del proyecto y ejecuta:
          </p>
          <pre style="background: #0f172a; padding: 0.5rem 0.75rem; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1); margin: 0; font-family: monospace; color: #38bdf8;">bash scripts/serve_ollama.sh</pre>
        </div>
        <span class="msg-time">${getCurrentTime()}</span>
      </div>
    `;
    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  // 5. Append User Message
  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";

    row.innerHTML = `
      <div class="msg-content-wrapper">
        <div class="msg-bubble">${escapeHtml(text)}</div>
        <span class="msg-time">${getCurrentTime()}</span>
      </div>
      <div class="msg-avatar">👤</div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  // 6. Append Bot Answer Message
  function appendBotAnswerMessage(data) {
    const row = document.createElement("div");
    row.className = "message-row bot";

    const contentWrapper = document.createElement("div");
    contentWrapper.className = "msg-content-wrapper";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    // Header with status
    const header = document.createElement("div");
    header.className = "bot-answer-header";

    const title = document.createElement("span");
    title.className = "bot-answer-title";
    title.textContent =
      data.answers && data.answers.length > 1
        ? `Consulta descompuesta en ${data.answers.length} aspectos`
        : "Respuesta regulatoria fundamentada";

    const statusBadge = document.createElement("span");
    renderStatusBadge(statusBadge, data.status);

    header.appendChild(title);
    header.appendChild(statusBadge);
    bubble.appendChild(header);

    // Answers per subquestion
    if (data.answers && data.answers.length > 0) {
      data.answers.forEach((ans) => {
        // Ingest sources into conversation storage
        if (ans.sources) {
          ans.sources.forEach((s) => conversationSources.set(s.id, s));
        }

        const subContainer = document.createElement("div");
        subContainer.style.marginBottom = "0.75rem";

        if (data.answers.length > 1) {
          const subTitle = document.createElement("div");
          subTitle.style.fontWeight = "700";
          subTitle.style.fontSize = "0.85rem";
          subTitle.style.color = "#93c5fd";
          subTitle.style.margin = "0.4rem 0";
          subTitle.textContent = `${ans.question_id}: ${ans.question}`;
          subContainer.appendChild(subTitle);
        }

        // Display message if abstained or rejected
        if (ans.display_message) {
          const msgP = document.createElement("p");
          msgP.className = `claim-p ${ans.status === "insufficient_evidence" ? "abstention" : "rejected"}`;
          msgP.textContent = `ℹ️ ${ans.display_message}`;
          subContainer.appendChild(msgP);
        }

        // Claims / evidence passages
        if (ans.claims && ans.claims.length > 0) {
          const claimsBlock = document.createElement("div");
          claimsBlock.className = "claims-block";

          ans.claims.forEach((claim) => {
            const block = document.createElement("div");
            block.innerHTML = formatLegalEvidenceHtml(claim.text, claim.citations);
            claimsBlock.appendChild(block);
          });
          subContainer.appendChild(claimsBlock);
        }

        bubble.appendChild(subContainer);
      });
    }

    // Meta Footer
    const footer = document.createElement("div");
    footer.className = "bot-meta-footer";
    footer.innerHTML = `
      <span>⏱️ ${data.wall_seconds ? data.wall_seconds.toFixed(2) + "s" : "—"}</span>
      <span>📜 DOUE-L-2024-81079</span>
    `;
    bubble.appendChild(footer);

    contentWrapper.appendChild(bubble);

    const timeSpan = document.createElement("span");
    timeSpan.className = "msg-time";
    timeSpan.textContent = getCurrentTime();
    contentWrapper.appendChild(timeSpan);

    row.innerHTML = `<div class="msg-avatar">⚖️</div>`;
    row.appendChild(contentWrapper);

    messagesContainer.appendChild(row);

    // Update references drawer
    updateReferencesSidebar();
    scrollToBottom();
  }

  // 7. Append Error Message
  function appendBotErrorMessage(title, details) {
    const row = document.createElement("div");
    row.className = "message-row bot";

    row.innerHTML = `
      <div class="msg-avatar">⚠️</div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble" style="border-left: 3px solid #ef4444;">
          <strong style="color: #f87171;">${escapeHtml(title)}</strong>
          <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 0.35rem;">
            ${escapeHtml(details)}
          </p>
        </div>
        <span class="msg-time">${getCurrentTime()}</span>
      </div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  // 8. Update References Sidebar
  function updateReferencesSidebar() {
    const sources = Array.from(conversationSources.values());
    sidebarBadgeCount.textContent = sources.length;
    referencesCountBadge.textContent = `${sources.length} fuente${sources.length === 1 ? "" : "s"}`;

    if (sources.length === 0) {
      referencesList.innerHTML = `
        <div class="empty-references">
          <span class="empty-icon">📖</span>
          <p>Aún no hay referencias en la conversación.</p>
          <small>Las citas normativas que respalden cada respuesta se irán acumulando en este panel.</small>
        </div>
      `;
      return;
    }

    referencesList.innerHTML = "";
    sources.forEach((src) => {
      const card = document.createElement("div");
      card.className = "reference-card";
      card.id = `ref-card-${src.id}`;

      const cleanPreview = (src.text || "")
        .replace(/[\s;,]+(?:[a-z]|\d+|(?:i{1,3}|iv|v|vi{0,3}|ix|x))\)\s*$/, "")
        .trim();

      card.innerHTML = `
        <div class="ref-card-header">
          <span class="badge badge-primary">${escapeHtml(src.id)}</span>
          <span class="ref-article-name">${escapeHtml(src.article || "Fragmento normativo")}</span>
        </div>
        <p class="ref-text-preview">${escapeHtml(cleanPreview)}</p>
        <div class="ref-actions">
          <button type="button" class="btn-ref-view" data-src-id="${escapeHtml(src.id)}">
            Ver pasaje completo
          </button>
        </div>
      `;

      card.querySelector(".btn-ref-view").onclick = () => openSourceModal(src);
      referencesList.appendChild(card);
    });
  }

  // 9. Format Legal Evidence with structured clauses, lists, and citations
  function formatLegalEvidenceHtml(rawText, citations) {
    if (!rawText) return "";

    // 1. Clean trailing orphaned markers (e.g. "; b)" cut at chunk boundaries)
    let text = rawText
      .replace(/[\s;,]+(?:[a-z]|\d+|(?:i{1,3}|iv|v|vi{0,3}|ix|x))\)\s*$/, "")
      .trim();

    // 2. Extract article / recital header ONLY when separated by newline
    let header = "";
    const lines = text.split("\n");
    if (
      lines.length > 1 &&
      /^(Artículo\s+\d+|Considerando\s+\(\d+\)|ANEXO\s+[IVXLCDM]+)/i.test(lines[0])
    ) {
      header = lines[0].trim();
      text = lines.slice(1).join("\n").trim();
    }

    // Safety fallback: if text became empty, keep everything in text
    if (!text) {
      text = header || rawText;
      header = "";
    }

    // 3. Break before numbered clauses (" 1. ", " 2. ") and lists ONLY when preceded by punctuation or newline
    text = text.replace(/(?<=[.:;])\s+(?=\d+\.\s+)/g, "\n\n");
    text = text.replace(/(?<=[.:;,])\s+(?=[a-z]\)\s+)/g, "\n\n");
    text = text.replace(/(?<=[.:;,])\s+(?=(?:i{1,3}|iv|v|vi{0,3}|ix|x)\)\s+)/gi, "\n\n");

    const segments = text.split(/\n{2,}/).map((s) => s.trim()).filter(Boolean);

    let html = `<div class="legal-claim-block">`;
    if (header) {
      html += `<div class="legal-article-title">${escapeHtml(header)}</div>`;
    }

    segments.forEach((seg) => {
      const letterMatch = seg.match(/^([a-z]\))\s*(.*)$/is);
      const romanMatch = seg.match(/^((?:i{1,3}|iv|v|vi{0,3}|ix|x)\))\s*(.*)$/is);
      const numberMatch = seg.match(/^(\d+\.)\s*(.*)$/is);

      if (letterMatch) {
        html += `
          <div class="legal-list-item letter-item">
            <span class="list-marker">${escapeHtml(letterMatch[1])}</span>
            <div class="list-text">${escapeHtml(letterMatch[2])}</div>
          </div>
        `;
      } else if (romanMatch) {
        html += `
          <div class="legal-list-item roman-item">
            <span class="list-marker roman">${escapeHtml(romanMatch[1])}</span>
            <div class="list-text">${escapeHtml(romanMatch[2])}</div>
          </div>
        `;
      } else if (numberMatch) {
        html += `
          <div class="legal-clause">
            <span class="clause-marker">${escapeHtml(numberMatch[1])}</span>
            <div class="clause-text">${escapeHtml(numberMatch[2])}</div>
          </div>
        `;
      } else {
        html += `<p class="legal-para">${escapeHtml(seg)}</p>`;
      }
    });

    // Clean citation tags placed directly at the end of the passage
    if (citations && citations.length > 0) {
      const tags = citations
        .map(
          (cid) =>
            `<button type="button" class="citation-tag" data-citation="${escapeHtml(cid)}" title="Ver pasaje en referencias">${escapeHtml(cid)}</button>`
        )
        .join(" ");
      html += `<div class="claim-citations">${tags}</div>`;
    }

    html += `</div>`;
    return html;
  }

  // 10. Handle Citation Tag Clicks
  document.addEventListener("click", (e) => {
    const tag = e.target.closest(".citation-tag");
    if (!tag) return;

    const citationId = tag.getAttribute("data-citation");
    if (!citationId) return;

    // Ensure sidebar is open on smaller viewports
    if (window.innerWidth <= 900) {
      referencesSidebar.classList.add("open");
    }

    const refCard = document.getElementById(`ref-card-${citationId}`);
    if (refCard) {
      refCard.scrollIntoView({ behavior: "smooth", block: "center" });
      refCard.classList.remove("highlighted");
      void refCard.offsetWidth; // force reflow
      refCard.classList.add("highlighted");
    } else if (conversationSources.has(citationId)) {
      openSourceModal(conversationSources.get(citationId));
    }
  });

  // 11. Modal Logic
  function openSourceModal(source) {
    modalSourceId.textContent = source.id;
    const matchingDoc = availableDocuments.find(
      (d) => d.id === source.document || (source.document && source.document.includes(d.id)) || d.id === currentDocumentId
    );
    modalDocument.textContent = matchingDoc ? matchingDoc.title : (source.document || "Documento oficial BOE");
    modalPage.textContent = source.page !== undefined ? `Pág. ${source.page} (XML estructurado)` : "Pág. 0";
    modalUnit.textContent = source.unit_type || "article";
    modalChunkId.textContent = source.chunk_id !== undefined ? `#${source.chunk_id}` : "—";
    modalSourceText.innerHTML = formatLegalEvidenceHtml(source.text || "", []);

    sourceModal.classList.remove("hidden");
  }

  function closeModal() {
    sourceModal.classList.add("hidden");
  }

  modalCloseBtn.addEventListener("click", closeModal);
  modalDismissBtn.addEventListener("click", closeModal);
  sourceModal.addEventListener("click", (e) => {
    if (e.target === sourceModal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !sourceModal.classList.contains("hidden")) {
      closeModal();
    }
  });

  // 12. Reset Conversation
  resetChatBtn.addEventListener("click", () => {
    if (confirm("¿Deseas reiniciar la conversación y limpiar el historial de preguntas y referencias?")) {
      initConversation();
    }
  });

  // 13. Sidebar Toggle (Mobile / Drawer)
  toggleSidebarBtn.addEventListener("click", () => {
    referencesSidebar.classList.toggle("open");
  });

  closeSidebarBtn.addEventListener("click", () => {
    referencesSidebar.classList.remove("open");
  });

  // Helpers
  function renderStatusBadge(element, status) {
    element.className = "badge";
    switch (status) {
      case "answered":
        element.classList.add("badge-ok");
        element.textContent = "Respondida con evidencia";
        break;
      case "partial":
        element.classList.add("badge-warn");
        element.textContent = "Parcialmente respondida";
        break;
      case "insufficient_evidence":
        element.classList.add("badge-warn");
        element.textContent = "Abstención (falta de evidencia)";
        break;
      case "review_rejected":
        element.classList.add("badge-error");
        element.textContent = "Rechazada (soporte insuficiente)";
        break;
      case "error":
        element.classList.add("badge-error");
        element.textContent = "Error";
        break;
      default:
        element.classList.add("badge-neutral");
        element.textContent = status || "Desconocido";
    }
  }

  function scrollToBottom() {
    setTimeout(() => {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 50);
  }

  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function adjustTextareaHeight(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Kick off initial state
  initConversation();
});
