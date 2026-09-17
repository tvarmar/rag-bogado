// RAG-Bogado Client-Side Logic
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("ask-form");
  const questionInput = document.getElementById("question-input");
  const documentSelect = document.getElementById("document-select");
  const modeSelect = document.getElementById("mode-select");
  const searchCountSelect = document.getElementById("search-count-select");
  const maxPassagesInput = document.getElementById("max-passages-input");
  const submitBtn = document.getElementById("submit-btn");

  const healthBadge = document.getElementById("health-badge");
  const loadingState = document.getElementById("loading-state");
  const errorState = document.getElementById("error-state");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");

  const resultsContainer = document.getElementById("results-container");
  const overallStatusBadge = document.getElementById("overall-status-badge");
  const responseTimeSpan = document.getElementById("response-time");
  const subquestionsCountSpan = document.getElementById("subquestions-count");
  const answersList = document.getElementById("answers-list");
  const sourcesCountSpan = document.getElementById("sources-count");
  const sourcesList = document.getElementById("sources-list");

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

  let currentSourcesMap = new Map();

  // 1. Health check & document list initialization
  async function checkHealth() {
    try {
      const response = await fetch("/health");
      if (!response.ok) throw new Error("Servicio no disponible");
      const data = await response.json();

      if (data.status === "ok" && data.catalog_ready) {
        healthBadge.className = "badge badge-ok";
        healthBadge.textContent = `En línea (${data.active_documents.length} norma${data.active_documents.length === 1 ? "" : "s"})`;

        // Populate document select
        if (data.active_documents && data.active_documents.length > 0) {
          documentSelect.innerHTML = "";
          data.active_documents.forEach((docId) => {
            const opt = document.createElement("option");
            opt.value = docId;
            opt.textContent = docId === "eu_ai_act" ? "Reglamento de IA (eu_ai_act)" : docId;
            documentSelect.appendChild(opt);
          });
        }
      } else {
        healthBadge.className = "badge badge-warn";
        healthBadge.textContent = "Catálogo degradado";
      }
    } catch (err) {
      healthBadge.className = "badge badge-error";
      healthBadge.textContent = "Desconectado";
    }
  }

  // 2. Form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    // Reset UI states
    errorState.classList.add("hidden");
    resultsContainer.classList.add("hidden");
    loadingState.classList.remove("hidden");
    submitBtn.disabled = true;
    submitBtn.classList.add("loading");

    const payload = {
      question: question,
      document_id: documentSelect.value,
      answer_mode: modeSelect.value,
      search_count: parseInt(searchCountSelect.value, 10),
      max_passages: parseInt(maxPassagesInput.value, 10) || 5,
    };

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        const errorDetail = data.detail || "Error desconocido al procesar la consulta";
        showError(`Error ${res.status}`, errorDetail);
        return;
      }

      renderResults(data);
    } catch (err) {
      showError("Fallo de conexión", err.message || "No se pudo comunicar con el servidor.");
    } finally {
      loadingState.classList.add("hidden");
      submitBtn.disabled = false;
      submitBtn.classList.remove("loading");
    }
  });

  // 3. Render Results
  function renderResults(data) {
    currentSourcesMap.clear();

    // Top-level status
    renderStatusBadge(overallStatusBadge, data.status);
    responseTimeSpan.textContent = data.wall_seconds ? `${data.wall_seconds.toFixed(2)} s` : "—";
    subquestionsCountSpan.textContent = data.answers ? data.answers.length : 0;

    // Render Answers
    answersList.innerHTML = "";
    if (data.answers && data.answers.length > 0) {
      data.answers.forEach((ans) => {
        // Collect sources into map
        if (ans.sources) {
          ans.sources.forEach((s) => currentSourcesMap.set(s.id, s));
        }

        const card = document.createElement("div");
        card.className = "answer-card";

        const header = document.createElement("div");
        header.className = "answer-header";

        const title = document.createElement("h3");
        title.className = "question-title";
        title.textContent = `${ans.question_id}: ${ans.question}`;

        const statusBadge = document.createElement("span");
        renderStatusBadge(statusBadge, ans.status);

        header.appendChild(title);
        header.appendChild(statusBadge);
        card.appendChild(header);

        // Display message if abstained or rejected
        if (ans.display_message) {
          const msgEl = document.createElement("p");
          msgEl.className = "claim-item";
          msgEl.style.borderLeftColor = ans.status === "answered" ? "var(--primary)" : "#d97706";
          msgEl.textContent = ans.display_message;
          card.appendChild(msgEl);
        }

        // Claims or extracted passages
        if (ans.claims && ans.claims.length > 0) {
          const claimsContainer = document.createElement("div");
          claimsContainer.className = "claims-container";

          ans.claims.forEach((claim) => {
            const claimEl = document.createElement("div");
            claimEl.className = "claim-item";

            // Format claim text with clickable citation pills
            claimEl.innerHTML = formatClaimWithCitations(claim.text, claim.citations);
            claimsContainer.appendChild(claimEl);
          });
          card.appendChild(claimsContainer);
        }

        answersList.appendChild(card);
      });
    }

    // Render Sources Grid
    sourcesList.innerHTML = "";
    const allSources = Array.from(currentSourcesMap.values());
    sourcesCountSpan.textContent = `${allSources.length} fuente${allSources.length === 1 ? "" : "s"}`;

    allSources.forEach((src) => {
      const srcCard = document.createElement("div");
      srcCard.className = "source-item";
      srcCard.id = `source-${src.id}`;

      const srcHeader = document.createElement("div");
      srcHeader.className = "source-item-header";

      const idBadge = document.createElement("span");
      idBadge.className = "badge badge-primary";
      idBadge.textContent = src.id;

      const artName = document.createElement("span");
      artName.className = "source-article-name";
      artName.textContent = src.article || "Fragmento normativo";

      srcHeader.appendChild(idBadge);
      srcHeader.appendChild(artName);
      srcCard.appendChild(srcHeader);

      const preview = document.createElement("p");
      preview.className = "source-text-preview";
      preview.textContent = src.text;
      srcCard.appendChild(preview);

      const actions = document.createElement("div");
      actions.className = "source-actions";

      const viewBtn = document.createElement("button");
      viewBtn.className = "btn btn-secondary btn-sm";
      viewBtn.textContent = "Ver pasaje original";
      viewBtn.onclick = () => openSourceModal(src);

      actions.appendChild(viewBtn);
      srcCard.appendChild(actions);

      sourcesList.appendChild(srcCard);
    });

    resultsContainer.classList.remove("hidden");
    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Format citations inside claim text as clickable elements
  function formatClaimWithCitations(text, citations) {
    let html = escapeHtml(text);
    if (citations && citations.length > 0) {
      const citationsHtml = citations
        .map(
          (cid) =>
            `<button type="button" class="citation-pill" data-citation="${escapeHtml(cid)}">${escapeHtml(cid)}</button>`
        )
        .join(" ");
      html += ` <span class="citations-block">${citationsHtml}</span>`;
    }
    return html;
  }

  // Citation click handler (event delegation)
  document.addEventListener("click", (e) => {
    const pill = e.target.closest(".citation-pill");
    if (!pill) return;

    const citationId = pill.getAttribute("data-citation");
    if (!citationId) return;

    const sourceEl = document.getElementById(`source-${citationId}`);
    if (sourceEl) {
      sourceEl.scrollIntoView({ behavior: "smooth", block: "center" });
      sourceEl.classList.remove("highlighted");
      void sourceEl.offsetWidth; // trigger reflow
      sourceEl.classList.add("highlighted");
    } else if (currentSourcesMap.has(citationId)) {
      openSourceModal(currentSourcesMap.get(citationId));
    }
  });

  // Modal open & close
  function openSourceModal(source) {
    modalSourceId.textContent = source.id;
    modalArticleTitle.textContent = source.article || "Fragmento normativo";
    modalDocument.textContent = source.document || "—";
    modalPage.textContent = source.page !== undefined ? `Pág. ${source.page}` : "Pág. 0 (XML)";
    modalUnit.textContent = source.unit_type || "article";
    modalChunkId.textContent = source.chunk_id !== undefined ? `#${source.chunk_id}` : "—";
    modalSourceText.textContent = source.text || "";

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

  // Helper: Status Badges
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
        element.textContent = "Error de procesamiento";
        break;
      default:
        element.classList.add("badge-neutral");
        element.textContent = status || "Desconocido";
    }
  }

  function showError(title, message) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorState.classList.remove("hidden");
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

  // Initial check
  checkHealth();
});
