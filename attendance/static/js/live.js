/* Live attendance: webcam → /api/sessions/<id>/recognize → overlay + roster. */
(() => {
  const cfg = window.LIVE;
  const $ = (id) => document.getElementById(id);
  const video = $("video"), overlay = $("overlay"), ctx = overlay.getContext("2d");
  const headers = { "Content-Type": "application/json", "X-CSRFToken": window.csrf };
  const LABEL = { present: "✓ Present", late: "⏱ Late", absent: "✕ Absent" };
  let stream = null, running = false, busy = false, roster = [], lastFaces = [], frameW = 640;

  // ------------------------------------------------------------------ roster
  async function loadRoster() {
    const r = await fetch(`/api/sessions/${cfg.session}/roster`);
    if (!r.ok) return;
    const body = await r.json();
    if (!body.open) { location.reload(); return; }
    roster = body.students;
    renderSummary(body.summary);
    renderRoster();
  }

  function renderSummary(s) {
    $("pct").textContent = `${Math.round(s.percent)}%`;
    const t = s.total || 1;
    $("bar").innerHTML = [["present", "var(--ok)"], ["late", "var(--warn)"], ["absent", "var(--err)"]]
      .map(([k, c]) => `<i style="width:${(100 * s[k]) / t}%;background:${c}"></i>`).join("");
    $("counts").textContent = `${s.present} present · ${s.late} late · ${s.absent} absent · ${s.unmarked} not yet marked`;
  }

  function renderRoster(highlight) {
    const q = $("filter").value.toLowerCase();
    const order = { null: 0, absent: 1, late: 2, present: 3 };
    const rows = roster
      .filter((s) => !q || s.name.toLowerCase().includes(q) || s.roll_no.toLowerCase().includes(q))
      .sort((a, b) => order[a.status] - order[b.status] || a.roll_no.localeCompare(b.roll_no));
    $("roster").innerHTML = rows.map((s) => `
      <div class="row ${highlight === s.id ? "flash-in" : ""}" data-id="${s.id}">
        <div class="who"><b>${esc(s.name)}</b><span class="muted small mono">${esc(s.roll_no)}${s.has_face ? "" : " · no face"}${s.time ? " · " + s.time : ""}${s.method === "face" ? " · 🙂" : ""}</span></div>
        <div class="seg">${["present", "late", "absent"].map((st) =>
          `<button class="${st} ${s.status === st ? "on" : ""}" data-status="${st}" title="${LABEL[st]}">${st[0].toUpperCase()}</button>`).join("")}</div>
      </div>`).join("") || `<div class="empty">No students</div>`;
  }

  $("roster").addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-status]");
    if (!btn) return;
    const id = +btn.closest(".row").dataset.id;
    const r = await fetch(`/api/sessions/${cfg.session}/mark`, { method: "POST", headers, body: JSON.stringify({ student_id: id, status: btn.dataset.status }) });
    const body = await r.json();
    if (!r.ok) return toast(body.error || "Could not update", "error");
    const s = roster.find((x) => x.id === id);
    Object.assign(s, { status: body.status, method: "manual", time: new Date().toTimeString().slice(0, 8) });
    renderSummary(body.summary);
    renderRoster(id);
  });
  $("filter").addEventListener("input", () => renderRoster());

  // ------------------------------------------------------------------ camera
  async function listCameras() {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
    const sel = $("camera-select");
    if (devices.length > 1) {
      sel.innerHTML = devices.map((d, i) => `<option value="${d.deviceId}">${esc(d.label || "Camera " + (i + 1))}</option>`).join("");
      sel.hidden = false;
    }
  }

  async function start(deviceId) {
    try {
      stream?.getTracks().forEach((t) => t.stop());
      stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId }, width: 1280, height: 720 } : { width: 1280, height: 720, facingMode: "user" },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      $("placeholder").hidden = true;
      $("stop").hidden = false;
      $("hud-state").textContent = "● Scanning";
      running = true;
      listCameras();
      loop();
    } catch (err) {
      toast("Camera unavailable: " + err.message, "error");
    }
  }

  function stop() {
    running = false;
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    $("placeholder").hidden = false;
    $("stop").hidden = true;
    $("hud-state").textContent = "Camera paused";
  }

  async function loop() {
    while (running) {
      const t0 = performance.now();
      if (!busy && video.videoWidth) await scan();
      const dt = performance.now() - t0;
      $("hud-fps").textContent = dt > 0 ? `${Math.round(dt)} ms` : "";
      await new Promise((r) => setTimeout(r, Math.max(150, 700 - dt)));
    }
  }

  async function scan() {
    busy = true;
    try {
      const c = document.createElement("canvas");
      frameW = Math.min(800, video.videoWidth);
      c.width = frameW;
      c.height = Math.round((video.videoHeight * frameW) / video.videoWidth);
      c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
      const r = await fetch(`/api/sessions/${cfg.session}/recognize`, {
        method: "POST", headers, body: JSON.stringify({ image: c.toDataURL("image/jpeg", 0.85) }),
      });
      const body = await r.json();
      if (!r.ok) { $("tip").textContent = body.error || ""; return; }
      lastFaces = body.faces;
      draw(body.faces, body.frame);
      renderSummary(body.summary);
      for (const f of body.faces) if (f.status === "marked") onMarked(f);
      $("tip").textContent = body.faces.length ? "" : "No face in view";
      if (body.enrolled_without_face) $("tip").textContent += ` · ${body.enrolled_without_face} enrolled student(s) have no face samples`;
    } catch (e) {
      $("tip").textContent = "Connection problem: retrying…";
    } finally {
      busy = false;
    }
  }

  function draw(faces, frame) {
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    const k = video.videoWidth / frame.w;
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    ctx.lineWidth = 3;
    ctx.font = "600 20px Inter, sans-serif";
    for (const f of faces) {
      const [x, y, w, h] = f.box.map((v) => v * k);
      const color = f.status === "unknown" ? "#ef4444" : f.status === "already" ? "#6366f1" : "#10b981";
      ctx.strokeStyle = color;
      ctx.strokeRect(x, y, w, h);
      const label = f.status === "unknown" ? "Unknown" : `${f.name}${f.status === "marked" ? " ✓" : ""}`;
      // The canvas is mirrored with the video, so draw text un-mirrored.
      ctx.save();
      ctx.scale(-1, 1);
      const tw = ctx.measureText(label).width + 14;
      ctx.fillStyle = color;
      ctx.fillRect(-(x + w), y - 30, Math.max(tw, w), 28);
      ctx.fillStyle = "#fff";
      ctx.fillText(label, -(x + w) + 7, y - 9);
      ctx.restore();
    }
  }

  function onMarked(f) {
    const s = roster.find((x) => x.id === f.student_id);
    if (s) Object.assign(s, { status: f.marked_as, method: "face", time: new Date().toTimeString().slice(0, 8) });
    renderRoster(f.student_id);
    const feed = $("feed");
    if (feed.firstElementChild?.classList.contains("muted")) feed.innerHTML = "";
    const d = document.createElement("div");
    d.innerHTML = `<b>${new Date().toTimeString().slice(0, 5)}</b> · ${esc(f.name)} <span class="muted mono">${esc(f.roll_no)}</span> → <span class="badge ${f.marked_as}">${LABEL[f.marked_as]}</span> <span class="muted small">(${f.score.toFixed(2)})</span>`;
    feed.prepend(d);
    beep();
  }

  let audio;
  function beep() {
    try {
      audio = audio || new AudioContext();
      const o = audio.createOscillator(), g = audio.createGain();
      o.frequency.value = 880; g.gain.value = 0.06;
      o.connect(g).connect(audio.destination);
      o.start(); o.stop(audio.currentTime + 0.12);
    } catch (e) { /* no audio */ }
  }

  function esc(s) { return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  $("start")?.addEventListener("click", () => start());
  $("stop").addEventListener("click", stop);
  $("camera-select").addEventListener("change", (e) => start(e.target.value));
  window.addEventListener("beforeunload", stop);
  loadRoster();
  setInterval(() => { if (!busy) loadRoster(); }, 6000); // keeps several devices in sync
})();
