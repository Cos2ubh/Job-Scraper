(() => {
  const COLUMNS = [
    { key: "to_apply",     label: "To Apply",     accent: "bg-slate-100  border-slate-300" },
    { key: "applied",      label: "Applied",      accent: "bg-blue-50    border-blue-300"  },
    { key: "interviewing", label: "Interviewing", accent: "bg-amber-50   border-amber-300" },
    { key: "offer",        label: "Offer",        accent: "bg-emerald-50 border-emerald-300" },
    { key: "rejected",     label: "Rejected",     accent: "bg-rose-50    border-rose-300"  },
  ];

  const board       = document.getElementById("board");
  const modal       = document.getElementById("modal-root");
  const addBtn      = document.getElementById("add-job-btn");
  const cancelBtn   = document.getElementById("cancel-btn");
  const form        = document.getElementById("add-job-form");

  let jobs = [];

  async function loadBoard() {
    board.innerHTML = `<div class="col-span-full text-slate-500 text-center py-12">Loading…</div>`;
    try {
      const data = await api.get("/api/tracker");
      jobs = data.jobs || [];
      renderBoard();
    } catch {
      board.innerHTML = `<div class="col-span-full text-rose-600 text-center py-12">Failed to load.</div>`;
    }
  }

  function renderBoard() {
    const grouped = Object.fromEntries(COLUMNS.map(c => [c.key, []]));
    for (const j of jobs) {
      if (grouped[j.status]) grouped[j.status].push(j);
    }
    board.innerHTML = COLUMNS.map(col => columnHtml(col, grouped[col.key])).join("");
    attachDnd();
    attachCardEvents();
  }

  function columnHtml(col, colJobs) {
    return `
      <section class="kanban-col rounded-lg border ${col.accent} p-3" data-status="${col.key}">
        <header class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-slate-800">${col.label}</h3>
          <span class="text-xs font-medium bg-white text-slate-600 px-2 py-0.5 rounded-full">${colJobs.length}</span>
        </header>
        <div class="space-y-2">
          ${colJobs.map(cardHtml).join("") || `<p class="text-xs text-slate-400 text-center py-8">Drop a job here</p>`}
        </div>
      </section>
    `;
  }

  function cardHtml(job) {
    const statusOptions = COLUMNS.map(c =>
      `<option value="${c.key}" ${c.key === job.status ? "selected" : ""}>${c.label}</option>`
    ).join("");
    return `
      <article draggable="true" data-id="${job.id}"
        class="kanban-card bg-white rounded-md shadow-sm p-3 border border-slate-200">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h4 class="font-medium text-sm truncate">${escapeHtml(job.title)}</h4>
            <p class="text-xs text-slate-500 truncate">${escapeHtml(job.company)}</p>
          </div>
          <button data-delete="${job.id}" title="Delete"
            class="text-slate-400 hover:text-rose-600 text-lg leading-none">&times;</button>
        </div>
        ${job.salary ? `<p class="text-xs text-emerald-600 mt-1">${escapeHtml(job.salary)}</p>` : ""}
        ${job.date_applied ? `<p class="text-xs text-slate-400 mt-1">Applied ${fmtDate(job.date_applied)}</p>` : ""}
        ${job.notes ? `<p class="text-xs text-slate-600 mt-2 line-clamp-3">${escapeHtml(job.notes)}</p>` : ""}
        <div class="mt-2 flex items-center gap-2">
          <select data-status="${job.id}"
            class="text-xs border rounded px-1 py-0.5 flex-1 bg-slate-50">
            ${statusOptions}
          </select>
          ${job.url ? `<a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer"
            class="text-xs text-indigo-600 hover:underline">Link</a>` : ""}
        </div>
      </article>
    `;
  }

  function attachDnd() {
    board.querySelectorAll(".kanban-card").forEach(card => {
      card.addEventListener("dragstart", e => {
        card.classList.add("dragging");
        e.dataTransfer.setData("text/plain", card.dataset.id);
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", () => card.classList.remove("dragging"));
    });

    board.querySelectorAll(".kanban-col").forEach(col => {
      col.addEventListener("dragover", e => {
        e.preventDefault();
        col.classList.add("drop-target");
      });
      col.addEventListener("dragleave", () => col.classList.remove("drop-target"));
      col.addEventListener("drop", async e => {
        e.preventDefault();
        col.classList.remove("drop-target");
        const id = parseInt(e.dataTransfer.getData("text/plain"), 10);
        const newStatus = col.dataset.status;
        if (!id || !newStatus) return;
        await updateStatus(id, newStatus);
      });
    });
  }

  function attachCardEvents() {
    board.querySelectorAll("[data-status]").forEach(sel => {
      const id = parseInt(sel.dataset.status, 10);
      sel.addEventListener("change", () => updateStatus(id, sel.value));
    });
    board.querySelectorAll("[data-delete]").forEach(btn => {
      const id = parseInt(btn.dataset.delete, 10);
      btn.addEventListener("click", () => deleteJob(id));
    });
  }

  async function updateStatus(id, status) {
    try {
      await api.patch(`/api/tracker/${id}`, { status });
      const job = jobs.find(j => j.id === id);
      if (job) {
        job.status = status;
        if (status === "applied" && !job.date_applied) {
          job.date_applied = new Date().toISOString().slice(0, 10);
        }
      }
      renderBoard();
    } catch {}
  }

  async function deleteJob(id) {
    if (!confirm("Delete this tracked job?")) return;
    try {
      await api.del(`/api/tracker/${id}`);
      jobs = jobs.filter(j => j.id !== id);
      renderBoard();
      toast("Deleted.", "ok");
    } catch {}
  }

  function openModal()  { modal.classList.remove("hidden"); modal.classList.add("flex"); }
  function closeModal() { modal.classList.add("hidden");    modal.classList.remove("flex"); form.reset(); }

  addBtn.addEventListener("click", openModal);
  cancelBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    try {
      const created = await api.post("/api/tracker", payload);
      jobs.unshift(created);
      renderBoard();
      closeModal();
      toast("Job added.", "ok");
    } catch {}
  });

  loadBoard();
})();
