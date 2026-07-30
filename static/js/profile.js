(() => {
  const resumeEl = document.getElementById("resume-text");
  const kwEl     = document.getElementById("keywords");
  const saveBtn  = document.getElementById("save-btn");
  const savedEl  = document.getElementById("last-saved");

  async function load() {
    try {
      const p = await api.get("/api/profile");
      resumeEl.value = p.resume_text || "";
      kwEl.value     = p.keywords || "";
      if (p.updated_at) savedEl.textContent = `Last saved ${fmtDate(p.updated_at)}`;
    } catch {}
  }

  async function save() {
    saveBtn.disabled = true;
    const original = saveBtn.textContent;
    saveBtn.textContent = "Saving…";
    try {
      const p = await api.put("/api/profile", {
        resume_text: resumeEl.value,
        keywords:    kwEl.value,
      });
      savedEl.textContent = `Last saved ${fmtDate(p.updated_at)}`;
      toast("Profile saved. Dashboard will show match scores.", "ok");
    } catch {} finally {
      saveBtn.disabled = false;
      saveBtn.textContent = original;
    }
  }

  saveBtn.addEventListener("click", save);
  load();
})();
