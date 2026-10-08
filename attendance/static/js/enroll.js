/* Face enrolment: capture from the webcam or upload photos → POST /api/students/<id>/faces */
(() => {
  const cfg = window.ENROLL;
  const $ = (id) => document.getElementById(id);
  const msg = (t, err) => { const m = $("enroll-msg"); if (m) { m.textContent = t; m.style.color = err ? "var(--err)" : "var(--ok)"; } };
  let stream = null;

  async function send(dataUrl) {
    const r = await fetch(`/api/students/${cfg.student}/faces`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": window.csrf },
      body: JSON.stringify({ image: dataUrl }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || "Could not add this photo");
    const div = document.createElement("div");
    div.className = "face"; div.dataset.id = body.id;
    div.innerHTML = `<img src="${body.thumbnail}" alt="Face sample"><button title="Delete sample" data-del="${body.id}">✕</button>`;
    $("faces").appendChild(div);
    cfg.count = body.count;
    $("face-count").innerHTML = `<b>${cfg.count}</b> / ${cfg.max} samples`;
    return body;
  }

  function frame(video) {
    const c = document.createElement("canvas");
    c.width = video.videoWidth; c.height = video.videoHeight;
    c.getContext("2d").drawImage(video, 0, 0);
    return c.toDataURL("image/jpeg", 0.92);
  }

  $("cam-start")?.addEventListener("click", async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720, facingMode: "user" } });
      $("cam").srcObject = stream;
      $("cam-box").hidden = false; $("cam-snap").hidden = false; $("cam-start").hidden = true;
      msg("Look at the camera and press Capture. Turn your head a little between shots.");
    } catch (e) { msg("Camera unavailable: " + e.message + ". You can upload photos instead.", true); }
  });

  $("cam-snap")?.addEventListener("click", async () => {
    const btn = $("cam-snap"); btn.disabled = true;
    try { await send(frame($("cam"))); msg(`✓ Saved. ${cfg.count >= 3 ? "That's enough for reliable recognition." : "Take another from a slightly different angle."}`); }
    catch (e) { msg(e.message, true); }
    finally { btn.disabled = false; }
  });

  $("upload")?.addEventListener("change", async (e) => {
    for (const file of e.target.files) {
      const url = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(file); });
      try { await send(url); msg(`✓ Added ${file.name}`); } catch (err) { msg(`${file.name}: ${err.message}`, true); }
    }
    e.target.value = "";
  });

  document.addEventListener("click", async (e) => {
    const id = e.target.dataset?.del;
    if (!id || !confirm("Delete this face sample?")) return;
    const r = await fetch(`/api/students/${cfg.student}/faces/${id}`, { method: "DELETE", headers: { "X-CSRFToken": window.csrf } });
    if (r.ok) { e.target.closest(".face").remove(); cfg.count--; $("face-count").innerHTML = `<b>${cfg.count}</b> / ${cfg.max} samples`; }
  });
  window.addEventListener("beforeunload", () => stream?.getTracks().forEach((t) => t.stop()));
})();
