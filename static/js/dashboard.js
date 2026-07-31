(() => {
  const listEl   = document.getElementById("jobs-list");
  const metaEl   = document.getElementById("jobs-meta");
  const scrapeBtn= document.getElementById("scrape-btn");
  const qEl      = document.getElementById("filter-q");
  const compEl   = document.getElementById("filter-company");
  const remoteEl = document.getElementById("filter-remote");
  const expEl    = document.getElementById("filter-experience");
  const catEl    = document.getElementById("filter-category");
  const daysEl   = document.getElementById("filter-days");

  const REMOTE_BADGE = {
    remote:  { label: "Remote",  cls: "bg-emerald-100 text-emerald-800" },
    onsite:  { label: "Onsite",  cls: "bg-orange-100  text-orange-800" },
    hybrid:  { label: "Hybrid",  cls: "bg-purple-100  text-purple-800" },
    unknown: { label: "Unknown", cls: "bg-slate-200   text-slate-600" },
  };
  const EXP_BADGE = {
    fresher: { label: "Fresher", cls: "bg-sky-100    text-sky-800" },
    mid:     { label: "Mid",     cls: "bg-indigo-100 text-indigo-800" },
    senior:  { label: "Senior",  cls: "bg-rose-100   text-rose-800" },
    unknown: { label: "",        cls: "" },
  };
  const CAT_BADGE = {
    technical: { label: "Technical", cls: "bg-slate-800    text-white" },
    design:    { label: "Design",    cls: "bg-fuchsia-100  text-fuchsia-800" },
    product:   { label: "Product",   cls: "bg-cyan-100     text-cyan-800" },
    business:  { label: "Business",  cls: "bg-amber-100    text-amber-800" },
    other:     { label: "",          cls: "" },
  };

  let debounceTimer = null;

  function debounce(fn, ms) {
    return (...args) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => fn(...args), ms);
    };
  }

  async function loadJobs() {
    const params = new URLSearchParams();
    if (qEl.value.trim())    params.set("q", qEl.value.trim());
    if (compEl.value.trim()) params.set("company", compEl.value.trim());
    if (daysEl.value)        params.set("days", daysEl.value);
    if (remoteEl.value)      params.set("remote_type", remoteEl.value);
    if (expEl.value)         params.set("experience_level", expEl.value);
    if (catEl.value)         params.set("category", catEl.value);
    params.set("limit", "100");

    listEl.innerHTML = `<div class="text-slate-500 text-center py-8">Loading…</div>`;
    try {
      const data = await api.get(`/api/jobs?${params.toString()}`);
      renderJobs(data.jobs || []);
      metaEl.textContent = `Showing ${data.count} of ${data.total} scraped jobs.`;
    } catch (err) {
      listEl.innerHTML = `<div class="text-rose-600 text-center py-8">Failed to load jobs.</div>`;
    }
  }

  function renderJobs(jobs) {
    if (!jobs.length) {
      listEl.innerHTML = `<div class="text-slate-500 text-center py-12 bg-white rounded-lg shadow-sm">
        No jobs yet. Click <span class="font-semibold">Scrape Now</span> to fetch fresh remote listings.
      </div>`;
      return;
    }
    listEl.innerHTML = jobs.map(cardHtml).join("");
    listEl.querySelectorAll("[data-track-id]").forEach(btn => {
      btn.addEventListener("click", () => quickSave(parseInt(btn.dataset.trackId, 10), btn));
    });
  }

  function cardHtml(job) {
    const score = job.match_score;
    const scoreHtml = (score != null)
      ? `<span class="text-xs font-semibold px-2 py-1 rounded ${matchBadgeClass(score)}">
           Match ${score}%
         </span>`
      : `<span class="text-xs px-2 py-1 rounded bg-slate-200 text-slate-600">
           Set profile for match score
         </span>`;

    const rt = REMOTE_BADGE[job.remote_type] || REMOTE_BADGE.unknown;
    const remoteBadge = `<span class="text-xs font-semibold px-2 py-1 rounded ${rt.cls}">${rt.label}</span>`;

    const exp = EXP_BADGE[job.experience_level] || EXP_BADGE.unknown;
    const expBadge = exp.label
      ? `<span class="text-xs font-semibold px-2 py-1 rounded ${exp.cls}">${exp.label}</span>`
      : "";

    const cat = CAT_BADGE[job.category] || CAT_BADGE.other;
    const catBadge = cat.label
      ? `<span class="text-xs font-semibold px-2 py-1 rounded ${cat.cls}">${cat.label}</span>`
      : "";

    const tags = (job.tags || []).slice(0, 6).map(t =>
      `<span class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">${escapeHtml(t)}</span>`
    ).join("");

    return `
      <article class="bg-white dark:bg-slate-800 rounded-lg shadow-sm p-4 hover:shadow-md transition">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <h3 class="font-semibold text-slate-900 dark:text-slate-100">${escapeHtml(job.title)}</h3>
              ${catBadge}
              ${remoteBadge}
              ${expBadge}
              ${scoreHtml}
            </div>
            <p class="text-sm text-slate-600 dark:text-slate-300 mt-0.5">
              <span class="font-medium">${escapeHtml(job.company)}</span>
              ${job.location ? ` · ${escapeHtml(job.location)}` : ""}
              ${job.salary ? ` · <span class="text-emerald-600 dark:text-emerald-400">${escapeHtml(job.salary)}</span>` : ""}
            </p>
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              ${escapeHtml(job.source)} · Posted ${fmtDate(job.posted_at) || fmtDate(job.scraped_at)}
            </p>
            ${job.description ? `<p class="text-sm text-slate-700 dark:text-slate-300 mt-2 line-clamp-3">${escapeHtml(job.description)}</p>` : ""}
            ${tags ? `<div class="mt-2 flex gap-1 flex-wrap">${tags}</div>` : ""}
          </div>
          <div class="flex flex-col gap-2 shrink-0">
            <a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer"
               class="text-xs text-center px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 dark:text-slate-200">
              View →
            </a>
            <button data-track-id="${job.id}"
              class="text-xs px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-medium">
              Track This Job
            </button>
          </div>
        </div>
      </article>
    `;
  }

  async function quickSave(scrapedId, btn) {
    btn.disabled = true;
    btn.textContent = "Saving…";
    try {
      const result = await api.post(`/api/tracker/from-scraped/${scrapedId}`);
      if (result.already_tracked) {
        toast("Already in your Kanban.", "info");
      } else {
        toast("Added to Kanban → To Apply", "ok");
      }
      btn.textContent = "Tracked ✓";
      btn.classList.remove("bg-emerald-600", "hover:bg-emerald-700");
      btn.classList.add("bg-slate-400");
    } catch {
      btn.disabled = false;
      btn.textContent = "Track This Job";
    }
  }

  async function runScrape() {
    scrapeBtn.disabled = true;
    const original = scrapeBtn.textContent;
    scrapeBtn.textContent = "Scraping…";
    setStatus("Fetching sources…");
    try {
      const res = await api.post("/api/scrape");
      const s = res.summary || {};
      toast(`Scrape done: +${s.total_new || 0} new, ${s.total_updated || 0} updated`, "ok");
      setStatus(`Last scrape: +${s.total_new || 0} new`);
      await loadJobs();
    } catch (err) {
      setStatus("Scrape failed.");
    } finally {
      scrapeBtn.disabled = false;
      scrapeBtn.textContent = original;
    }
  }

  scrapeBtn.addEventListener("click", runScrape);
  qEl.addEventListener("input",       debounce(loadJobs, 300));
  compEl.addEventListener("input",    debounce(loadJobs, 300));
  remoteEl.addEventListener("change", loadJobs);
  expEl.addEventListener("change",    loadJobs);
  catEl.addEventListener("change",    loadJobs);
  daysEl.addEventListener("change",   loadJobs);

  loadJobs();
})();
