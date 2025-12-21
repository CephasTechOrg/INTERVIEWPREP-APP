function renderRubricBars(rubric) {
  const wrap = qs("#rubric_wrap");
  if (!wrap) return;
  wrap.innerHTML = "";

  const keys = Object.keys(rubric || {});
  if (!keys.length) {
    wrap.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No rubric data yet.</div>`;
    return;
  }

  keys.forEach((k) => {
    const val = Number(rubric[k] ?? 0);
    const pct = Math.max(0, Math.min(100, (val / 10) * 100));

    const row = document.createElement("div");
    row.className = "rubric-item";
    const label = escapeHtml(String(k || "").replaceAll("_", " "));
    row.innerHTML = `
      <div class="rubric-header">
        <span class="rubric-label">${label}</span>
        <span class="rubric-score">${val}/10</span>
      </div>
      <div class="rubric-bar"><div class="rubric-fill" style="width:0%"></div></div>
    `;
    wrap.appendChild(row);

    const bar = row.querySelector(".rubric-fill");
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (bar) bar.style.width = `${pct}%`;
      });
    });
  });
}

function renderList(selector, items) {
  const el = qs(selector);
  if (!el) return;
  el.innerHTML = "";

  if (!items || !items.length) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">Nothing here yet.</div>`;
    return;
  }

  const ul = document.createElement("ul");
  ul.style.margin = "0";
  ul.style.paddingLeft = "18px";
  ul.style.color = "rgba(255,255,255,0.85)";
  items.forEach((it) => {
    const li = document.createElement("li");
    li.style.marginBottom = "8px";
    li.textContent = it;
    ul.appendChild(li);
  });
  el.appendChild(ul);
}

function renderPills(selector, items, variant = "info") {
  const el = qs(selector);
  if (!el) return;
  el.innerHTML = "";

  if (!items || !items.length) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">Nothing here yet.</div>`;
    return;
  }

  items.forEach((it) => {
    const pill = document.createElement("span");
    pill.className = `pill pill-${variant}`;
    pill.innerHTML =
      variant === "good"
        ? `<i class="fas fa-check-circle"></i> ${escapeHtml(it)}`
        : variant === "warn"
          ? `<i class="fas fa-triangle-exclamation"></i> ${escapeHtml(it)}`
          : `<i class="fas fa-circle"></i> ${escapeHtml(it)}`;
    el.appendChild(pill);
  });
}

function renderSteps(selector, items) {
  const el = qs(selector);
  if (!el) return;
  el.innerHTML = "";

  if (!items || !items.length) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">Nothing here yet.</div>`;
    return;
  }

  const ol = document.createElement("ol");
  ol.className = "ordered";
  items.forEach((it) => {
    const li = document.createElement("li");
    li.textContent = it;
    ol.appendChild(li);
  });
  el.appendChild(ol);
}

function _rating(score) {
  const s = Number(score) || 0;
  if (s >= 90) return { label: "Excellent", cls: "great" };
  if (s >= 80) return { label: "Great", cls: "great" };
  if (s >= 70) return { label: "Good", cls: "good" };
  if (s >= 55) return { label: "Fair", cls: "warn" };
  return { label: "Needs focus", cls: "danger" };
}

function renderGauge(selector, score) {
  const el = typeof selector === "string" ? qs(selector) : selector;
  if (!el) return;
  const val = Math.max(0, Math.min(100, Number(score) || 0));
  const deg = (val / 100) * 360;
  const rating = _rating(val);

  el.innerHTML = `
    <div class="gauge-arc"></div>
    <div class="gauge-center">
      <div class="gauge-score">${Math.round(val)}</div>
      <div class="gauge-label">${rating.label}</div>
    </div>
  `;
  el.className = `gauge ${rating.cls}`;
  const arc = el.querySelector(".gauge-arc");
  if (arc) {
    arc.style.background = `conic-gradient(var(--brand2) ${deg}deg, rgba(255,255,255,0.08) ${deg}deg 360deg)`;
  }
}

function renderRadar(selector, rubric) {
  const el = typeof selector === "string" ? qs(selector) : selector;
  if (!el) return;
  el.innerHTML = "";

  const keys = ["communication", "problem_solving", "correctness_reasoning", "complexity", "edge_cases"];
  const hasAny = keys.some((k) => rubric && rubric[k] !== undefined);
  if (!hasAny) {
    el.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No rubric data yet.</div>`;
    return;
  }

  const size = 320;
  const center = size / 2;
  const radius = size / 2 - 28;
  const levels = 4;
  const angleStep = (Math.PI * 2) / keys.length;

  const points = keys.map((k, i) => {
    const raw = rubric?.[k] ?? 0;
    const norm = Math.max(0, Math.min(10, Number(raw) || 0)) / 10;
    const angle = -Math.PI / 2 + i * angleStep;
    const r = norm * radius;
    return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) };
  });

  const poly = points.map((p) => `${p.x},${p.y}`).join(" ");

  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
  svg.classList.add("radar-svg");

  // grid
  for (let l = 1; l <= levels; l++) {
    const r = (radius / levels) * l;
    const ring = document.createElementNS(svgNS, "polygon");
    const ringPoints = keys
      .map((_, i) => {
        const angle = -Math.PI / 2 + i * angleStep;
        return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
      })
      .join(" ");
    ring.setAttribute("points", ringPoints);
    ring.setAttribute("class", "radar-grid");
    svg.appendChild(ring);
  }

  // axes + labels
  keys.forEach((k, i) => {
    const angle = -Math.PI / 2 + i * angleStep;
    const x = center + radius * Math.cos(angle);
    const y = center + radius * Math.sin(angle);

    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", center);
    line.setAttribute("y1", center);
    line.setAttribute("x2", x);
    line.setAttribute("y2", y);
    line.setAttribute("class", "radar-axis");
    svg.appendChild(line);

    const label = document.createElementNS(svgNS, "text");
    label.setAttribute("x", center + (radius + 14) * Math.cos(angle));
    label.setAttribute("y", center + (radius + 14) * Math.sin(angle));
    label.setAttribute("class", "radar-label");
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("dominant-baseline", "middle");
    label.textContent = k.replaceAll("_", " ");
    svg.appendChild(label);
  });

  const shape = document.createElementNS(svgNS, "polygon");
  shape.setAttribute("points", poly);
  shape.setAttribute("class", "radar-shape");
  svg.appendChild(shape);

  el.appendChild(svg);
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
