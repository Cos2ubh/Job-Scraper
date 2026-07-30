(() => {
  const cardsEl     = document.getElementById("metric-cards");
  const topCompEl   = document.getElementById("top-companies");
  const timelineCtx = document.getElementById("timeline-chart");
  const statusCtx   = document.getElementById("status-chart");

  const STATUS_LABELS = {
    to_apply: "To Apply", applied: "Applied", interviewing: "Interviewing",
    offer: "Offer", rejected: "Rejected",
  };
  const STATUS_COLORS = {
    to_apply: "#94a3b8", applied: "#3b82f6", interviewing: "#f59e0b",
    offer: "#10b981", rejected: "#ef4444",
  };

  let timelineChart = null;
  let statusChart = null;

  function kpiCard(label, value, sub) {
    return `
      <div class="bg-white p-4 rounded-lg shadow-sm">
        <p class="text-xs uppercase tracking-wide text-slate-500">${label}</p>
        <p class="text-2xl font-bold mt-1">${value}</p>
        ${sub ? `<p class="text-xs text-slate-500 mt-1">${sub}</p>` : ""}
      </div>
    `;
  }

  async function load() {
    let d;
    try {
      d = await api.get("/api/analytics");
    } catch {
      cardsEl.innerHTML = `<p class="col-span-full text-rose-600 text-center py-6">Failed to load analytics.</p>`;
      return;
    }

    cardsEl.innerHTML = [
      kpiCard("Total Tracked",   d.total_tracked,                  ""),
      kpiCard("Applied",         d.applied_total,                  "Total apps sent"),
      kpiCard("Interview Rate",  `${d.interview_rate_pct}%`,       `${d.interview_total} of ${d.applied_total}`),
      kpiCard("Offer Rate",      `${d.offer_rate_pct}%`,           `${d.offer_total} offers`),
    ].join("");

    topCompEl.innerHTML = (d.top_companies || []).length
      ? d.top_companies.map(c => `
          <li class="flex items-center justify-between py-2">
            <span>${escapeHtml(c.company)}</span>
            <span class="text-slate-500">${c.count}</span>
          </li>
        `).join("")
      : `<li class="text-slate-400 py-3 text-center">No applications tracked yet.</li>`;

    // Timeline (bar chart)
    const tl = d.timeline_30d || [];
    if (timelineChart) timelineChart.destroy();
    timelineChart = new Chart(timelineCtx, {
      type: "bar",
      data: {
        labels: tl.map(x => x.date.slice(5)),
        datasets: [{
          label: "Applications",
          data: tl.map(x => x.count),
          backgroundColor: "#6366f1",
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        plugins: { legend: { display: false } },
      },
    });

    // Status doughnut
    const statuses = Object.keys(STATUS_LABELS);
    const counts = statuses.map(s => (d.status_breakdown || {})[s] || 0);
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(statusCtx, {
      type: "doughnut",
      data: {
        labels: statuses.map(s => STATUS_LABELS[s]),
        datasets: [{
          data: counts,
          backgroundColor: statuses.map(s => STATUS_COLORS[s]),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  load();
})();
