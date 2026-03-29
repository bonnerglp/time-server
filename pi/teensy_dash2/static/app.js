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
const ppsCompareCanvas = document.getElementById("ppsCompareChart");
const histCanvas = document.getElementById("histChart");
const allanCanvas = document.getElementById("allanChart");

function makeCard(label, value, cls = "") {
  return `<div class="card"><div class="label">${label}</div><div class="value ${cls}">${value ?? ""}</div></div>`;
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "number" && isFinite(value)) return value.toFixed(digits);
  return value;
}

function fmtSci(value, digits = 3) {
  if (value === null || value === undefined || value === "") return "";
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
  if (!vals.length) return items.map(() => null);
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  return items.map(x => {
    const v = x[key];
    return (v !== null && isFinite(v)) ? (v - mean) : null;
  });
}

function drawSeries(canvas, seriesList, labels = null) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const padL = 55, padR = 20, padT = 20, padB = 40;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0, 0, w, h);
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
  if (ymin === ymax) {
    ymin -= 1;
    ymax += 1;
  }

  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  ctx.strokeStyle = "#555";
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  ctx.fillStyle = "#aaa";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(ymax.toFixed(2), 5, padT - 2);
  ctx.textBaseline = "bottom";
  ctx.fillText(ymin.toFixed(2), 5, h - padB + 2);

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

  const colors = ["#4ea1ff", "#6ee7a8", "#ffb86b", "#ff7b7b", "#d19cff", "#72e3d2"];

  seriesList.forEach((s, idx) => {
    const c = colors[idx % colors.length];
    ctx.strokeStyle = c;
    ctx.beginPath();
    let started = false;

    s.values.forEach((v, i) => {
      if (v === null || !isFinite(v)) return;
      const x = padL + i * plotW / Math.max(s.values.length - 1, 1);
      const y = padT + (ymax - v) * plotH / (ymax - ymin);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
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

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0, 0, w, h);

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
  ctx.lineTo(pad, h - pad);
  ctx.lineTo(w - 15, h - pad);
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
  const padL = 70, padR = 25, padT = 20, padB = 55;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0, 0, w, h);
  ctx.font = "12px sans-serif";

  if (!rows.length) {
    ctx.fillStyle = "#aaa";
    ctx.fillText("No Allan data yet", 20, 20);
    return;
  }

  const clean = rows.filter(r => r && r.tau_s > 0 && r.adev > 0 && isFinite(r.tau_s) && isFinite(r.adev));
  if (!clean.length) {
    ctx.fillStyle = "#aaa";
    ctx.fillText("No Allan data yet", 20, 20);
    return;
  }

  const xs = clean.map(r => Math.log10(r.tau_s));
  const ys = clean.map(r => Math.log10(r.adev));
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);

  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const xAt = v => padL + (Math.log10(v) - xmin) * plotW / Math.max(xmax - xmin, 1e-9);
  const yAt = v => padT + (ymax - Math.log10(v)) * plotH / Math.max(ymax - ymin, 1e-9);

  ctx.strokeStyle = "#555";
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  const tauTicks = clean.map(r => r.tau_s);
  ctx.strokeStyle = "#333";
  ctx.fillStyle = "#aaa";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";

  tauTicks.forEach(tau => {
    const x = xAt(tau);
    ctx.beginPath();
    ctx.moveTo(x, h - padB);
    ctx.lineTo(x, h - padB + 5);
    ctx.stroke();
    ctx.save();
    ctx.translate(x, h - padB + 8);
    ctx.rotate(-Math.PI / 6);
    ctx.fillText(String(tau), 0, 0);
    ctx.restore();
  });

  const yTickExponents = [];
  for (let e = Math.floor(ymin); e <= Math.ceil(ymax); e++) {
    yTickExponents.push(e);
  }

  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  yTickExponents.forEach(e => {
    const val = Math.pow(10, e);
    const y = yAt(val);

    ctx.save();
    ctx.strokeStyle = "#2f2f2f";
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.restore();

    ctx.strokeStyle = "#555";
    ctx.beginPath();
    ctx.moveTo(padL - 5, y);
    ctx.lineTo(padL, y);
    ctx.stroke();

    ctx.fillText(`1e${e}`, padL - 8, y);
  });

  ctx.strokeStyle = "#6ee7a8";
  ctx.beginPath();
  clean.forEach((r, i) => {
    const x = xAt(r.tau_s);
    const y = yAt(r.adev);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  clean.forEach(r => {
    const x = xAt(r.tau_s);
    const y = yAt(r.adev);
    ctx.fillStyle = "#6ee7a8";
    ctx.beginPath();
    ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
    ctx.fill();
  });

  ctx.fillStyle = "#aaa";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText("Tau (s)", w / 2, h - 18);

  ctx.save();
  ctx.translate(18, h / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.fillText("ADEV", 0, 0);
  ctx.restore();
}


function drawGnssDual(canvas, history) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const padL = 55, padR = 55, padT = 20, padB = 40;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#1b1b1b";
  ctx.fillRect(0, 0, w, h);
  ctx.font = "12px sans-serif";

  const labels = history.map(x => x.timestamp_utc);
  const sats = history.map(x => x.sats);
  const vis = history.map(x => x.sats_visible);
  const pdop = history.map(x => x.pdop);

  const satVals = [...sats, ...vis].filter(v => v !== null && isFinite(v));
  const pdopVals = pdop.filter(v => v !== null && isFinite(v));

  if (!satVals.length && !pdopVals.length) {
    ctx.fillStyle = "#aaa";
    ctx.fillText("No GNSS data", 20, 20);
    return;
  }

  let satMin = satVals.length ? Math.min(...satVals) : 0;
  let satMax = satVals.length ? Math.max(...satVals) : 1;
  let pdopMin = pdopVals.length ? Math.min(...pdopVals) : 0;
  let pdopMax = pdopVals.length ? Math.max(...pdopVals) : 1;

  if (satMin === satMax) { satMin -= 1; satMax += 1; }
  if (pdopMin === pdopMax) { pdopMin -= 0.1; pdopMax += 0.1; }

  satMin = Math.floor(satMin - 1);
  satMax = Math.ceil(satMax + 1);
  pdopMin = Math.max(0, pdopMin - 0.1);
  pdopMax = pdopMax + 0.1;

  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  ctx.strokeStyle = "#555";
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.lineTo(w - padR, padT);
  ctx.stroke();

  ctx.fillStyle = "#aaa";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(String(satMax), 5, padT - 2);
  ctx.textBaseline = "bottom";
  ctx.fillText(String(satMin), 5, h - padB + 2);

  ctx.textAlign = "right";
  ctx.textBaseline = "top";
  ctx.fillText(pdopMax.toFixed(2), w - 5, padT - 2);
  ctx.textBaseline = "bottom";
  ctx.fillText(pdopMin.toFixed(2), w - 5, h - padB + 2);

  if (labels.length > 1) {
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

  function xAt(i, n) {
    return padL + i * plotW / Math.max(n - 1, 1);
  }
  function ySat(v) {
    return padT + (satMax - v) * plotH / Math.max(satMax - satMin, 1e-9);
  }
  function yPdop(v) {
    return padT + (pdopMax - v) * plotH / Math.max(pdopMax - pdopMin, 1e-9);
  }

  function drawLine(values, yfn, color, dashed=false) {
    ctx.save();
    ctx.strokeStyle = color;
    if (dashed) ctx.setLineDash([6, 4]);
    ctx.beginPath();
    let started = false;
    values.forEach((v, i) => {
      if (v === null || !isFinite(v)) return;
      const x = xAt(i, values.length);
      const y = yfn(v);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.restore();
  }

  drawLine(sats, ySat, "#4ea1ff");
  drawLine(vis, ySat, "#6ee7a8");
  drawLine(pdop, yPdop, "#ffb86b", true);

  ctx.fillStyle = "#4ea1ff";
  ctx.fillText("sats_used", padL + 10, 4);
  ctx.fillStyle = "#6ee7a8";
  ctx.fillText("sats_visible", padL + 120, 4);
  ctx.fillStyle = "#ffb86b";
  ctx.fillText("pdop", padL + 260, 4);
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
  const autoCalClass = live.auto_cal_valid ? "ok" : (live.auto_cal_state === "LEARNING" ? "" : "bad");

  cardsEl.innerHTML =
    makeCard("Online", latest.online ? "YES" : "NO", statusClass) +
    makeCard("State", latest.state) +
    makeCard("UTC", latest.utc) +
    makeCard("UTC ns", latest.utc_ns) +
    makeCard("UTC flags", latest.utc_flags) +

    makeCard("PPS", latest.pps) +
    makeCard("PPS OK", latest.pps_ok) +
    makeCard("Calibrated phase err ns", fmt((live.auto_calibrated_phase_ns ?? live.phase_residual_ns), 0), live.auto_cal_valid ? "ok" : "bad") +
    makeCard("10m RMS jitter ns", fmt(live.rms_10m_ns, 2)) +
    makeCard("Raw phase err ns", fmt(live.current_phase_err_ns, 0)) +
    makeCard("Phase bias ns", fmt((live.phase_bias_ns ?? live.auto_cal_ns), 0), (live.phase_bias_valid || live.auto_cal_valid) ? "ok" : "bad") +
    makeCard("Auto-cal state", live.auto_cal_state, autoCalClass) +
    makeCard("Piksi-ZED RMS ns", fmt(latest.piksi_minus_zed_rms_ns, 2)) +
    makeCard("Bias RMS ns", fmt((live.phase_bias_rms_ns ?? live.auto_cal_rms_ns), 2)) +
    makeCard("Auto-cal samples", live.auto_cal_samples) +
    makeCard("ZED OK", latest.zed_ok) +
    makeCard("TCP OK", latest.tcp_ok) +
    makeCard("UTC OK", latest.utc_ok) +
    makeCard("GPS OK", latest.gps_ok) +
    makeCard("Tracking", latest.tracking) +
    makeCard("GPS week", latest.gps_week) +
    makeCard("GPS TOW ms", latest.gps_tow_ms) +
    makeCard("GPS ns residual", latest.gps_ns_res) +



    makeCard("60s RMS jitter ns", fmt(live.rms_60s_ns, 2)) +
    makeCard("60s peak-peak ns", fmt(live.p2p_60s_ns, 2)) +
    makeCard("ADEV @ 1s", fmtSci(live.adev_1s, 3)) +
    makeCard("Period ns", fmt(latest.period_ns, 0)) +
    makeCard("Err ns", fmt(latest.err_ns, 0)) +
    makeCard("RMS ns", fmt(latest.rms_ns, 2)) +
    makeCard("Min err ns", fmt(latest.min_err_ns, 0)) +
    makeCard("Max err ns", fmt(latest.max_err_ns, 0)) +

    makeCard("Piksi-ZED ns", fmt(latest.piksi_minus_zed_ns, 0)) +
    makeCard("Piksi-ZED min ns", fmt(latest.piksi_minus_zed_min_ns, 0)) +
    makeCard("Piksi-ZED max ns", fmt(latest.piksi_minus_zed_max_ns, 0)) +
    makeCard("Valid PPS samples", latest.piksi_minus_zed_valid) +
    makeCard("Rejected PPS", latest.piksi_minus_zed_rejected) +

    makeCard("Sats Used", latest.sats) +
    makeCard("Sats Visible", latest.sats_visible) +
    makeCard("Fix Type", latest.fix_type) +
    makeCard("PDOP", fmt(latest.pdop, 2)) +
    makeCard("HDOP", fmt(latest.hdop, 2)) +
    makeCard("VDOP", fmt(latest.vdop, 2)) +
    makeCard("C/N0 avg", fmt(latest.cn0_avg, 2)) +
    makeCard("C/N0 max", fmt(latest.cn0_max, 2)) +
    makeCard("GPS", latest.gps_count) +
    makeCard("GAL", latest.gal_count) +
    makeCard("GLO", latest.glo_count) +
    makeCard("BDS", latest.bds_count) +
    makeCard("QZSS", latest.qzss_count) +
    makeCard("ZED status", latest.zed_status) +

    makeCard("TCP bytes", latest.tcp_bytes) +
    makeCard("SBP frames", latest.sbp_frames) +
    makeCard("CRC err", latest.crc_err) +

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
    { name: "err_ns", values: history.map(x => x.err_ns) },
    { name: "period_ns", values: history.map(x => x.period_ns) }
  ], history.map(x => x.timestamp_utc));

  drawSeries(phaseTrendCanvas, [
    { name: "phase_err_ns", values: histFiltered.map(x => x.err_ns) }
  ], histFiltered.map(x => x.timestamp_utc));

  drawSeries(jitter60Canvas, [
    { name: "60s_jitter_ns", values: demeanSeries(err60Hist, "err_ns") }
  ], err60Hist.map(x => x.timestamp_utc));

  drawSeries(jitter600Canvas, [
    { name: "10m_jitter_ns", values: demeanSeries(err600Hist, "err_ns") }
  ], err600Hist.map(x => x.timestamp_utc));

  drawSeries(ppsNoiseCanvas, [
    { name: "gps_pps_noise_ns", values: histFiltered.map(x => x.err_ns) }
  ], histFiltered.map(x => x.timestamp_utc));

  drawSeries(freqCanvas, [
    { name: "freq_ppb", values: freq }
  ]);

  drawSeries(trafficCanvas, [
    { name: "tcp_bytes", values: history.map(x => x.tcp_bytes) },
    { name: "sbp_frames", values: history.map(x => x.sbp_frames) },
    { name: "crc_err", values: history.map(x => x.crc_err) }
  ], history.map(x => x.timestamp_utc));

  drawSeries(ppsCompareCanvas, [
    { name: "piksi_minus_zed_ns", values: history.map(x => x.piksi_minus_zed_ns) }
  ], history.map(x => x.timestamp_utc));

  drawGnssDual(gnssCanvas, history);

  drawBars(histCanvas, hist.centers || [], hist.counts || [], "err_ns");
  drawAllan(allanCanvas, allan);
}

refresh();
setInterval(refresh, 2000);
