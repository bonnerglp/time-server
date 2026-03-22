const cardsEl = document.getElementById("cards");
const rawEl = document.getElementById("raw");

const timingCanvas = document.getElementById("timingChart");
const phaseTrendCanvas = document.getElementById("phaseTrendChart");
const jitter60Canvas = document.getElementById("jitter60Chart");
const jitter600Canvas = document.getElementById("jitter600Chart");
const ppsNoiseCanvas = document.getElementById("ppsNoiseChart");
const freqCanvas = document.getElementById("freqChart");
const trafficCanvas = document.getElementById("trafficChart");
const gnssCanvas = document.getElementById("gnssChart");
const histCanvas = document.getElementById("histChart");
const allanCanvas = document.getElementById("allanChart");

function makeCard(label, value, cls="") {
  return `<div class="card"><div class="label">${label}</div><div class="value ${cls}">${value ?? ""}</div></div>`;
}

function fmt(value, digits=2) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && isFinite(value)) return value.toFixed(digits);
  return value;
}

function fmtSci(value, digits=3) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && isFinite(value)) return value.toExponential(digits);
  return value;
}

function fmtAxisTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "";
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${mi}`;
}


function demeanSeries(items, key) {
  const vals = items.map(x => x[key]).filter(v => v !== null && isFinite(v));
  if (!vals.length) return items.map(_ => null);
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  return items.map(x => {
    const v = x[key];
    return (v !== null && isFinite(v)) ? (v - mean) : null;
  });
}

function drawSeries(canvas, seriesList, labels=null) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const padL = 55, padR = 20, padT = 20, padB = 40;

  ctx.clearRect(0,0,w,h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0,0,w,h);
  ctx.font = "12px sans-serif";

  const vals = [];
  for (const s of seriesList) {
    for (const v of s.values) {
      if (v !== null && isFinite(v)) vals.push(v);
    }
  }
  if (!vals.length) {
    ctx.fillStyle = "#aaa";
    ctx.fillText("No data", 20, 20);
    return;
  }

  let ymin = Math.min(...vals), ymax = Math.max(...vals);
  if (ymin === ymax) { ymin -= 1; ymax += 1; }

  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  // axes
  ctx.strokeStyle = "#555";
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  // y labels
  ctx.fillStyle = "#aaa";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(ymax.toFixed(2), 5, padT - 2);
  ctx.textBaseline = "bottom";
  ctx.fillText(ymin.toFixed(2), 5, h - padB + 2);

  // x-axis date/time ticks
  if (labels && labels.length > 1) {
    const tickCount = Math.min(6, labels.length);
    ctx.strokeStyle = "#333";
    ctx.fillStyle = "#aaa";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    for (let t = 0; t < tickCount; t++) {
      const idx = Math.round(t * (labels.length - 1) / Math.max(tickCount - 1, 1));
      const x = padL + idx * plotW / Math.max(labels.length - 1, 1);

      ctx.beginPath();
      ctx.moveTo(x, h - padB);
      ctx.lineTo(x, h - padB + 5);
      ctx.stroke();

      const label = fmtAxisTime(labels[idx]);
      ctx.save();
      ctx.translate(x, h - padB + 8);
      ctx.rotate(-Math.PI / 6);
      ctx.fillText(label, 0, 0);
      ctx.restore();
    }
  }

  const colors = ["#4ea1ff","#6ee7a8","#ffb86b","#ff7b7b","#d19cff","#72e3d2"];

  seriesList.forEach((s, idx) => {
    const c = colors[idx % colors.length];
    ctx.strokeStyle = c;
    ctx.beginPath();
    let started = false;
    s.values.forEach((v, i) => {
      if (v === null || !isFinite(v)) return;
      const x = padL + i * plotW / Math.max(s.values.length - 1, 1);
      const y = padT + (ymax - v) * plotH / (ymax - ymin);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = c;
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText(s.name, padL + 10 + idx * 150, 4);
  });
}

function drawBars(canvas, centers, counts, label) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const pad = 45;
  ctx.clearRect(0,0,w,h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0,0,w,h);

  if (!centers.length || !counts.length) {
    ctx.fillStyle = "#aaa";
    ctx.fillText("No data", 20, 20);
    return;
  }

  const ymax = Math.max(...counts, 1);
  const xmin = Math.min(...centers);
  const xmax = Math.max(...centers);

  ctx.strokeStyle = "#555";
  ctx.beginPath();
  ctx.moveTo(pad, 15);
  ctx.lineTo(pad, h-pad);
  ctx.lineTo(w-15, h-pad);
  ctx.stroke();

  const bw = (w - pad - 20) / centers.length;
  ctx.fillStyle = "#6ee7a8";
  counts.forEach((c, i) => {
    const bh = c * (h - pad - 25) / ymax;
    const x = pad + i * bw;
    const y = h - pad - bh;
    ctx.fillRect(x, y, Math.max(bw - 1, 1), bh);
  });

  ctx.fillStyle = "#aaa";
  ctx.fillText(`${label} min ${xmin.toFixed(1)}`, pad, h - 10);
  ctx.fillText(`max ${xmax.toFixed(1)}`, w - 120, h - 10);
}

function drawAllan(canvas, rows) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const pad = 55;
  ctx.clearRect(0,0,w,h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0,0,w,h);

  if (!rows.length) {
    ctx.fillStyle = "#aaa";
    ctx.fillText("No Allan data yet", 20, 20);
    return;
  }

  const xs = rows.map(r => Math.log10(r.tau_s));
  const ys = rows.map(r => Math.log10(r.adev));
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);

  ctx.strokeStyle = "#555";
  ctx.beginPath();
  ctx.moveTo(pad, 20);
  ctx.lineTo(pad, h-pad);
  ctx.lineTo(w-20, h-pad);
  ctx.stroke();

  ctx.strokeStyle = "#6ee7a8";
  ctx.beginPath();
  rows.forEach((r, i) => {
    const x = pad + (Math.log10(r.tau_s) - xmin) * (w - pad - 30) / Math.max(xmax - xmin, 1e-9);
    const y = 20 + (ymax - Math.log10(r.adev)) * (h - pad - 30) / Math.max(ymax - ymin, 1e-9);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#aaa";
  ctx.fillText("Tau (log s)", w / 2 - 30, h - 10);
  ctx.save();
  ctx.translate(15, h / 2 + 20);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("ADEV (log)", 0, 0);
  ctx.restore();
}

function filteredHistory(history) {
  return history.filter(x =>
    x.err_ns !== null &&
    isFinite(x.err_ns) &&
    Math.abs(x.err_ns) <= 100000
  );
}

async function refresh() {
  const [latest, history, allan, raw, hist, freq, hold, live] = await Promise.all([
    fetch("/api/latest").then(r => r.json()),
    fetch("/api/history").then(r => r.json()),
    fetch("/api/allan").then(r => r.json()),
    fetch("/api/raw/latest").then(r => r.json()),
    fetch("/api/histogram").then(r => r.json()),
    fetch("/api/frequency").then(r => r.json()),
    fetch("/api/holdover").then(r => r.json()),
    fetch("/api/live_stats").then(r => r.json()),
  ]);

  const statusClass = latest.online ? "ok" : "bad";

  cardsEl.innerHTML =
    makeCard("Online", latest.online ? "YES" : "NO", statusClass) +
    makeCard("State", latest.state) +
    makeCard("UTC", latest.utc) +
    makeCard("UTC ns", latest.utc_ns) +
    makeCard("UTC flags", latest.utc_flags) +
    makeCard("PPS", latest.pps) +
    makeCard("PPS OK", latest.pps_ok) +
    makeCard("TCP OK", latest.tcp_ok) +
    makeCard("UTC OK", latest.utc_ok) +
    makeCard("GPS OK", latest.gps_ok) +
    makeCard("Tracking", latest.tracking) +
    makeCard("GPS week", latest.gps_week) +
    makeCard("GPS TOW ms", latest.gps_tow_ms) +
    makeCard("GPS ns residual", latest.gps_ns_res) +
    makeCard("Current phase err ns", fmt(live.current_phase_err_ns, 0)) +
    makeCard("60s RMS jitter ns", fmt(live.rms_60s_ns, 2)) +
    makeCard("10m RMS jitter ns", fmt(live.rms_10m_ns, 2)) +
    makeCard("60s peak-peak ns", fmt(live.p2p_60s_ns, 2)) +
    makeCard("ADEV @ 1s", fmtSci(live.adev_1s, 3)) +
    makeCard("Period ns", latest.period_ns) +
    makeCard("Err ns", latest.err_ns) +
    makeCard("RMS ns", latest.rms_ns) +
    makeCard("Min err ns", latest.min_err_ns) +
    makeCard("Max err ns", latest.max_err_ns) +
    makeCard("TCP bytes", latest.tcp_bytes) +
    makeCard("SBP frames", latest.sbp_frames) +
    makeCard("CRC err", latest.crc_err) +
    makeCard("Sats", latest.sats) +
    makeCard("PDOP", latest.pdop) +
    makeCard("C/N0 avg", latest.cn0_avg) +
    makeCard("Fix type", latest.fix_type) +
    makeCard("FE mode", latest.fe_mode) +
    makeCard("FE control", latest.fe_control) +
    makeCard("FE phase ns", latest.fe_phase_ns) +
    makeCard("FE holdover", latest.fe_holdover) +
    makeCard("Age s", latest.age_s?.toFixed ? latest.age_s.toFixed(1) : latest.age_s) +
    makeCard("Holdover slope ns/s", hold.slope_ns_per_s?.toFixed ? hold.slope_ns_per_s.toFixed(3) : hold.slope_ns_per_s) +
    makeCard("Predicted drift 1h ns", hold.drift_1h_ns?.toFixed ? hold.drift_1h_ns.toFixed(1) : hold.drift_1h_ns);

  rawEl.textContent = JSON.stringify(raw, null, 2);

  const histFiltered = filteredHistory(history);
  const err60Hist = histFiltered.slice(-60);
  const err600Hist = histFiltered.slice(-600);

  drawSeries(timingCanvas, [
    {name: "err_ns", values: history.map(x => x.err_ns)},
    {name: "period_ns", values: history.map(x => x.period_ns)}
  ], history.map(x => x.timestamp_utc));

  drawSeries(phaseTrendCanvas, [
    {name: "phase_err_ns", values: histFiltered.map(x => x.err_ns)}
  ], histFiltered.map(x => x.timestamp_utc));

  drawSeries(jitter60Canvas, [
    {name: "60s_jitter_ns", values: demeanSeries(err60Hist, "err_ns")}
  ], err60Hist.map(x => x.timestamp_utc));

  drawSeries(jitter600Canvas, [
    {name: "10m_jitter_ns", values: demeanSeries(err600Hist, "err_ns")}
  ], err600Hist.map(x => x.timestamp_utc));

  drawSeries(ppsNoiseCanvas, [
    {name: "gps_pps_noise_ns", values: histFiltered.map(x => x.err_ns)}
  ], histFiltered.map(x => x.timestamp_utc));

  drawSeries(freqCanvas, [
    {name: "freq_ppb", values: freq}
  ]);

  drawSeries(trafficCanvas, [
    {name: "tcp_bytes", values: history.map(x => x.tcp_bytes)},
    {name: "sbp_frames", values: history.map(x => x.sbp_frames)},
    {name: "crc_err", values: history.map(x => x.crc_err)}
  ], history.map(x => x.timestamp_utc));

  drawSeries(gnssCanvas, [
    {name: "sats", values: history.map(x => x.sats)},
    {name: "pdop", values: history.map(x => x.pdop)},
    {name: "cn0_avg", values: history.map(x => x.cn0_avg)},
    {name: "gps_ns_res", values: history.map(x => x.gps_ns_res)},
    {name: "utc_ns", values: history.map(x => x.utc_ns)}
  ], history.map(x => x.timestamp_utc));

  drawBars(histCanvas, hist.centers || [], hist.counts || [], "err_ns");
  drawAllan(allanCanvas, allan);
}

refresh();
setInterval(refresh, 2000);
