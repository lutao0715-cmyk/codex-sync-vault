/* 自动剪辑台 · 前端逻辑
   无框架、无外部依赖，全部逻辑跑在浏览器本地。 */

'use strict';

// ── 全局状态 ────────────────────────────────────────────────
const S = {
  mode: 'silence',
  media: null,
  analysis: null,
  plan: null,
  duration: 0,
  view: { start: 0, end: 1 },
  disabled: new Set(),
  preview: false,
  job: null,
  jobTimer: null,
  silenceMode: 'cut',
  aspect: 'src',
  audioPreset: 'off',
  stale: true,
};

const $ = (id) => document.getElementById(id);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// ── 工具 ────────────────────────────────────────────────────
function fmtTime(t) {
  if (!isFinite(t) || t < 0) t = 0;
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  const ms = Math.floor((t % 1) * 1000);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}
function fmtDur(t) {
  if (!isFinite(t)) return '—';
  if (t >= 60) return `${Math.floor(t / 60)}分${(t % 60).toFixed(1)}秒`;
  return `${t.toFixed(1)}秒`;
}
function fmtSize(n) {
  if (!n) return '—';
  const u = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)}${u[i]}`;
}

let toastTimer = null;
function toast(msg, kind = '') {
  const el = $('toast');
  el.textContent = msg;
  el.className = 'toast on ' + kind;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = 'toast ' + kind; }, kind === 'err' ? 6000 : 3200);
}
function status(msg, right = '') {
  $('statusMsg').textContent = msg;
  if (right !== undefined) $('statusRight').textContent = right;
}
function progress(p) {
  const wrap = $('progressWrap');
  if (p === null) { wrap.hidden = true; return; }
  wrap.hidden = false;
  $('progressBar').style.width = clamp(p, 0, 100) + '%';
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (_) { /* 非 JSON */ }
  if (!res.ok || (data && data.ok === false)) {
    throw new Error((data && data.error) || `请求失败 ${res.status}`);
  }
  return data;
}
const postJSON = (path, body) => api(path, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body || {}),
});

// ── 参数绑定 ────────────────────────────────────────────────
// 滑杆 id -> 数值回显元素 id
const NUMERIC_LABELS = {
  noise_db: 'vNoise', min_silence: 'vMinSil', silence_speed: 'vSilSpeed',
  min_keep: 'vMinKeep', threshold: 'vThr', min_scene: 'vMinScene',
  drop_shorter_than: 'vDrop', sensitivity: 'vSens', beats_per_cut: 'vBpc',
  stride: 'vStride', lead_in: 'vLead', crf: 'vCrf', fade_in: 'vFi', fade_out: 'vFo',
};
const LABEL_FMT = {
  min_silence: (v) => (+v).toFixed(2),
  threshold: (v) => (+v).toFixed(2),
  min_scene: (v) => (+v).toFixed(1),
  drop_shorter_than: (v) => (+v).toFixed(1),
  sensitivity: (v) => (+v).toFixed(1),
  stride: (v) => (+v).toFixed(2),
  lead_in: (v) => (+v).toFixed(1),
  fade_in: (v) => (+v).toFixed(1),
  fade_out: (v) => (+v).toFixed(1),
};

function initParams() {
  for (const [id, labelId] of Object.entries(NUMERIC_LABELS)) {
    const input = $(id);
    const labelEl = $(labelId);
    if (!input || !labelEl) continue;
    const sync = () => {
      labelEl.textContent = (LABEL_FMT[id] || ((v) => v))(input.value);
      S.stale = true;
      if (S.plan) markStale();
      if (id === 'min_silence' || id === 'noise_db') drawTimelineSafe();
    };
    input.addEventListener('input', sync);
    sync();
  }
}

function markStale() {
  status('参数已改动，记得重新「生成方案」');
  $('btnPlan').classList.add('primary');
  $('btnPlan').classList.remove('ghost');
}

function readParams() {
  const num = (id) => parseFloat($(id).value);
  const base = {
    mode: S.mode,
    noise_db: num('noise_db'),
    min_silence: num('min_silence'),
    silence_mode: S.silenceMode,
    silence_speed: num('silence_speed'),
    min_keep: num('min_keep'),
    threshold: num('threshold'),
    min_scene: num('min_scene'),
    drop_shorter_than: num('drop_shorter_than'),
    sensitivity: num('sensitivity'),
    beats_per_cut: parseInt($('beats_per_cut').value, 10),
    stride: num('stride'),
    lead_in: num('lead_in'),
  };
  const out = {
    crf: num('crf'),
    preset: 'veryfast',
    normalize_loudness: $('loudnorm').checked,
    fade_in: num('fade_in'),
    fade_out: num('fade_out'),
  };
  if (S.aspect === '9:16') { out.width = 1080; out.height = 1920; }
  else if (S.aspect === '1:1') { out.width = 1080; out.height = 1080; }
  base.output = out;
  base.audio = readAudio();
  return base;
}

// ── 顶栏 / 模式 ─────────────────────────────────────────────
function syncModeUI() {
  document.querySelectorAll('.params[data-for]').forEach((p) => {
    p.hidden = p.dataset.for !== S.mode;
  });
  $('musicField').style.display = S.mode === 'beat' ? '' : 'none';
  [...$('modes').children].forEach((b) => {
    b.classList.toggle('active', b.dataset.mode === S.mode);
  });
}

const MODES = ['silence', 'scene', 'beat'];

function initModes() {
  $('modes').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-mode]');
    if (!btn) return;
    S.mode = btn.dataset.mode;
    syncModeUI();
    S.stale = true;
    if (S.media) { autoplan(); }
  });

  $('silenceMode').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-v]');
    if (!btn) return;
    S.silenceMode = btn.dataset.v;
    [...$('silenceMode').children].forEach((b) => b.classList.toggle('active', b === btn));
    document.querySelector('.field[data-when="speed"]').style.display =
      S.silenceMode === 'speed' ? '' : 'none';
    S.stale = true;
  });

  $('aspect').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-v]');
    if (!btn) return;
    S.aspect = btn.dataset.v;
    [...$('aspect').children].forEach((b) => b.classList.toggle('active', b === btn));
    S.stale = true;
  });

  // 初始状态
  syncModeUI();
  document.querySelector('.field[data-when="speed"]').style.display = 'none';
}

// ── 素材导入 ────────────────────────────────────────────────
function blankMeta(name, path, size) {
  return {
    name: name || '已载入素材', path: path || '', duration: 0,
    width: 0, height: 0, fps: 0, size: size || 0,
    video_codec: '', audio_codec: '', has_video: true, has_audio: true,
  };
}

// 把素材挂到界面上，但不触发分析
function mountMedia(meta) {
  S.media = meta;
  S.disabled.clear();
  S.plan = null;
  S.analysis = null;
  S.duration = meta.duration || 0;
  S.view = { start: 0, end: S.duration || 1 };

  const chip = $('fileChip');
  chip.classList.add('on');
  chip.querySelector('.name').textContent = meta.name;
  chip.title = meta.path || '';

  const v = $('video');
  v.src = '/api/media?t=' + Date.now();
  v.classList.add('on');
  $('viewerEmpty').style.display = 'none';
  v.load();
  $('timeTotal').textContent = fmtTime(meta.duration);

  renderMediaInfo(meta);
  $('btnAnalyze').disabled = false;
  $('btnPlan').disabled = false;
  $('btnRender').disabled = true;
  $('btnPreview').disabled = true;
  if ($('btnAudition')) $('btnAudition').disabled = false;
  if ($('btnSuggest')) $('btnSuggest').disabled = false;
  status('素材已载入，正在分析…');
  syncTransport();
  drawTimelineSafe();
}

// 挂载 + 分析 + 出方案
async function loadMedia(meta) {
  mountMedia(meta);
  await analyze();
}

function renderMediaInfo(m) {
  const rows = [
    ['时长', m.duration ? fmtDur(m.duration) : '分析中…', ''],
    ['分辨率', m.width ? `${m.width}×${m.height}` : (m.duration ? '纯音频' : '—'), ''],
    ['帧率', m.fps ? m.fps.toFixed(2) + ' fps' : '—', ''],
    ['体积', m.size ? fmtSize(m.size) : '—', ''],
    ['编码', [m.video_codec, m.audio_codec].filter(Boolean).join(' / ') || '—', ''],
  ];
  $('mediaInfo').innerHTML = rows
    .map(([k, v, c]) => `<div><dt>${k}</dt><dd class="${c}">${v}</dd></div>`).join('');
}

function initDrop() {
  const dz = $('dropzone');
  const viewer = $('viewer');

  dz.addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', (e) => {
    if (e.target.files[0]) upload(e.target.files[0]);
  });

  const stop = (e) => { e.preventDefault(); e.stopPropagation(); };
  ['dragenter', 'dragover'].forEach((ev) => {
    dz.addEventListener(ev, (e) => { stop(e); dz.classList.add('hot'); });
    viewer.addEventListener(ev, (e) => { stop(e); viewer.classList.add('dragging'); });
  });
  ['dragleave', 'drop'].forEach((ev) => {
    dz.addEventListener(ev, (e) => { stop(e); dz.classList.remove('hot'); });
    viewer.addEventListener(ev, (e) => { stop(e); viewer.classList.remove('dragging'); });
  });
  dz.addEventListener('drop', (e) => { if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); });
  viewer.addEventListener('drop', (e) => { if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); });

  $('btnAttach').addEventListener('click', async () => {
    const p = $('pathInput').value.trim();
    if (!p) return toast('先填一个路径', 'err');
    await attach(p);
  });
  $('pathInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('btnAttach').click(); });

  $('btnAttachMusic').addEventListener('click', async () => {
    const p = $('musicInput').value.trim();
    if (!p) return toast('先填音乐路径', 'err');
    try {
      const r = await postJSON('/api/attach', { path: $('pathInput').value.trim(), music: p });
      $('fileChip').classList.add('on');
      toast('音乐已载入', 'ok');
      S.stale = true;
      if (S.media) autoplan();
    } catch (err) { toast(err.message, 'err'); }
  });
}

async function upload(file) {
  status(`正在导入 ${file.name}…`);
  try {
    const r = await api('/api/upload?name=' + encodeURIComponent(file.name), {
      method: 'POST', body: file,
      headers: { 'Content-Type': 'application/octet-stream' },
    });
    toast('导入完成', 'ok');
    await loadMedia(blankMeta(file.name, r.attached, file.size));
  } catch (e) { toast('导入失败：' + e.message, 'err'); }
}

async function attach(path, music) {
  try {
    const r = await postJSON('/api/attach', { path, music });
    toast('素材已载入', 'ok');
    const full = r.attached || path;
    await loadMedia(blankMeta(full.split(/[\\/]/).pop(), full, 0));
  } catch (e) { toast(e.message, 'err'); }
}

// ── 分析 ────────────────────────────────────────────────────
async function analyze() {
  if (!S.media) return;
  $('btnAnalyze').classList.add('busy');
  status('分析中：静音段 / 镜头切换 / 节拍点…');
  progress(30);
  try {
    const r = await postJSON('/api/analyze', {
      silence: true, scenes: true, beats: true,
      noise_db: parseFloat($('noise_db').value),
      min_silence: parseFloat($('min_silence').value),
      threshold: parseFloat($('threshold').value),
      min_scene: parseFloat($('min_scene').value),
      sensitivity: parseFloat($('sensitivity').value),
      wave_buckets: Math.max(600, Math.floor($('tlWrap').clientWidth)),
    });
    S.analysis = r.analysis;
    const m = S.analysis.media;
    S.duration = m.duration || S.duration;
    S.view = { start: 0, end: S.duration || 1 };
    // 把真实元信息并进 S.media。否则下面重置 video.src 触发 loadedmetadata 时，
    // 回调里那段「补全缺失字段」的逻辑会拿占位数据把左栏的帧率/编码/体积覆盖回空值。
    S.media = { ...(S.media || {}), ...m, name: (S.media && S.media.name) || m.name };
    renderMediaInfo(S.media);
    $('video').src = '/api/media?t=' + Date.now();
    $('timeTotal').textContent = fmtTime(S.duration);

    const bits = [];
    if (S.analysis.silence) bits.push(`${S.analysis.silence.count} 段静音`);
    if (S.analysis.scenes) bits.push(`${S.analysis.scenes.count} 个镜头切点`);
    if (S.analysis.beats && !S.analysis.beats.error) bits.push(`${S.analysis.beats.count} 个节拍 (${S.analysis.beats.bpm || '?'} BPM)`);
    status('分析完成：' + (bits.join(' · ') || '无可用特征'));
    progress(null);
    await autoplan();
  } catch (e) {
    progress(null);
    status('分析失败');
    toast('分析失败：' + e.message, 'err');
  } finally {
    $('btnAnalyze').classList.remove('busy');
  }
}

// ── 生成方案 ────────────────────────────────────────────────
async function autoplan() {
  try {
    const r = await postJSON('/api/plan', readParams());
    applyPlan(r.plan);
  } catch (e) { toast('生成方案失败：' + e.message, 'err'); }
}

function applyPlan(plan) {
  S.plan = plan;
  S.disabled.clear();
  S.stale = false;
  $('btnPlan').classList.remove('primary');
  $('btnPlan').classList.add('ghost');
  $('btnRender').disabled = false;
  $('btnPreview').disabled = false;
  renderPlanStats(plan);
  drawTimelineSafe();
  if (plan.warnings && plan.warnings.length) {
    status(plan.warnings[0]);
  }
}

function renderPlanStats(plan) {
  const s = plan.stats;
  const rows = [
    ['片段数', s.segment_count, ''],
    ['原始时长', fmtDur(s.source_duration), ''],
    ['成片时长', fmtDur(s.output_duration), 'good'],
    ['砍掉', `${fmtDur(s.removed_duration)}  (${(s.removed_ratio * 100).toFixed(1)}%)`,
      s.removed_ratio > 0.05 ? 'warn' : ''],
  ];
  if (S.disabled.size) {
    const kept = plan.segments.filter((_, i) => !S.disabled.has(i));
    const dur = kept.reduce((a, s2) => a + (s2.end - s2.start) / (s2.speed || 1), 0);
    rows.push(['手动保留', `${kept.length} 段 / ${fmtDur(dur)}`, 'warn']);
  }
  if (plan.meta && plan.meta.bpm) rows.push(['估算 BPM', plan.meta.bpm, '']);
  if (plan.meta && plan.meta.beat_count) rows.push(['节拍点数', plan.meta.beat_count, '']);
  $('planStats').innerHTML = rows
    .map(([k, v, c]) => `<div><dt>${k}</dt><dd class="${c}">${v}</dd></div>`).join('');
}

// ── 时间线绘制 ──────────────────────────────────────────────
const TL = { ruler: 22, waveTop: 28, waveH: 64, segTop: 100, segH: 54 };

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function drawTimelineSafe() {
  const cv = $('tl');
  const wrap = $('tlWrap');
  const dpr = window.devicePixelRatio || 1;
  const w = wrap.clientWidth, h = wrap.clientHeight;
  if (!w || !h) return;
  if (cv.width !== w * dpr || cv.height !== h * dpr) {
    cv.width = w * dpr; cv.height = h * dpr;
  }
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawTimeline(ctx, w, h);
}

function t2x(t, w) {
  const { start, end } = S.view;
  return ((t - start) / Math.max(1e-6, end - start)) * w;
}
function x2t(x, w) {
  const { start, end } = S.view;
  return start + (x / w) * (end - start);
}

function niceStep(span, width) {
  const target = span / Math.max(2, width / 90);
  const steps = [0.04, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800];
  for (const s of steps) if (s >= target) return s;
  return 3600;
}

function drawTimeline(ctx, w, h) {
  const C = {
    bg: cssVar('--bg-0'), line: cssVar('--line'), line2: cssVar('--line-2'),
    fg3: cssVar('--fg-3'), fg2: cssVar('--fg-2'),
    accent: cssVar('--accent'), red: cssVar('--red'), blue: cssVar('--blue'),
    amber: cssVar('--amber'), bg2: cssVar('--bg-2'), bg3: cssVar('--bg-3'),
  };
  ctx.clearRect(0, 0, w, h);

  const dur = S.duration || 1;
  const { start: vs, end: ve } = S.view;
  const span = Math.max(1e-6, ve - vs);
  const pxPerSec = w / span;

  // ── 标尺 ──
  ctx.fillStyle = C.bg2;
  ctx.fillRect(0, 0, w, TL.ruler);
  ctx.strokeStyle = C.line;
  ctx.beginPath(); ctx.moveTo(0, TL.ruler + .5); ctx.lineTo(w, TL.ruler + .5); ctx.stroke();

  const step = niceStep(span, w);
  ctx.font = '10px ui-monospace, monospace';
  ctx.textBaseline = 'middle';
  const t0 = Math.floor(vs / step) * step;
  for (let t = t0; t <= ve + step; t += step) {
    const x = t2x(t, w);
    if (x < -40 || x > w + 40) continue;
    ctx.strokeStyle = C.line2;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, TL.ruler); ctx.stroke();
    ctx.fillStyle = C.fg3;
    ctx.textAlign = 'left';
    ctx.fillText(fmtTime(t).slice(0, -4), x + 4, TL.ruler / 2);
  }

  // ── 波形 ──
  const wf = S.analysis && S.analysis.waveform;
  if (wf && wf.peaks && wf.peaks.length) {
    const mid = TL.waveTop + TL.waveH / 2;
    const half = TL.waveH / 2 - 4;
    const n = wf.peaks.length;
    const durW = wf.duration || dur;

    ctx.fillStyle = 'rgba(76,147,247,.10)';
    ctx.fillRect(0, TL.waveTop, w, TL.waveH);

    ctx.beginPath();
    ctx.strokeStyle = 'rgba(155,166,180,.55)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x++) {
      const ta = x2t(x, w), tb = x2t(x + 1, w);
      const ia = clamp(Math.floor((ta / durW) * n), 0, n - 1);
      const ib = clamp(Math.ceil((tb / durW) * n), 1, n);
      let amp = 0;
      for (let i = ia; i < ib; i++) amp = Math.max(amp, wf.peaks[i][0]);
      const y = amp * half;
      ctx.moveTo(x + .5, mid - y);
      ctx.lineTo(x + .5, mid + y);
    }
    ctx.stroke();

    ctx.strokeStyle = 'rgba(155,166,180,.22)';
    ctx.beginPath(); ctx.moveTo(0, mid + .5); ctx.lineTo(w, mid + .5); ctx.stroke();
  } else {
    ctx.fillStyle = C.bg2;
    ctx.fillRect(0, TL.waveTop, w, TL.waveH);
    ctx.fillStyle = C.fg3;
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('无音轨 / 尚未分析', w / 2, TL.waveTop + TL.waveH / 2);
  }

  // ── 静音区域（红色阴影，跨波形与片段轨）──
  const sil = (S.analysis && S.analysis.silence && S.analysis.silence.regions) || [];
  ctx.fillStyle = 'rgba(240,90,90,.18)';
  for (const r of sil) {
    const x1 = t2x(r.start, w), x2 = t2x(r.end, w);
    if (x2 < 0 || x1 > w) continue;
    ctx.fillRect(x1, TL.waveTop, Math.max(1, x2 - x1), TL.segTop + TL.segH - TL.waveTop);
  }

  // ── 片段轨 ──
  ctx.fillStyle = C.bg2;
  ctx.fillRect(0, TL.segTop, w, TL.segH);
  ctx.strokeStyle = C.line;
  ctx.beginPath();
  ctx.moveTo(0, TL.segTop + .5); ctx.lineTo(w, TL.segTop + .5);
  ctx.moveTo(0, TL.segTop + TL.segH + .5); ctx.lineTo(w, TL.segTop + TL.segH + .5);
  ctx.stroke();

  const segs = (S.plan && S.plan.segments) || [];
  const COLOR = {
    keep: C.accent, scene: '#4C93F7', beat: C.amber,
    silence: C.red, broll: '#A78BFA',
  };
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i];
    const off = s.label === 'beat' ? C.amber : (COLOR[s.label] || C.accent);
    const x1 = t2x(s.start, w), x2 = t2x(s.end, w);
    if (x2 < -2 || x1 > w + 2) continue;
    const bw = Math.max(1.5, x2 - x1);
    const off_ = S.disabled.has(i);
    ctx.fillStyle = off_ ? 'rgba(255,255,255,.07)' : off;
    ctx.globalAlpha = off_ ? 1 : 0.82;
    roundRect(ctx, x1, TL.segTop + 6, bw, TL.segH - 12, 3);
    ctx.fill();
    ctx.globalAlpha = 1;

    if (!off_ && bw > 42) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(x1, TL.segTop + 6, bw, TL.segH - 12);
      ctx.clip();
      ctx.fillStyle = 'rgba(10,13,17,.82)';
      ctx.font = '10px ui-monospace, monospace';
      ctx.textAlign = 'left';
      const txt = s.label === 'silence' ? '静音' :
        (s.speed && s.speed !== 1 ? `${s.speed}×` : `#${i + 1}`);
      ctx.fillText(txt, x1 + 5, TL.segTop + TL.segH / 2);
      ctx.restore();
    } else if (off_) {
      ctx.strokeStyle = 'rgba(255,255,255,.28)';
      ctx.beginPath();
      ctx.moveTo(x1 + 3, TL.segTop + TL.segH / 2 + 3);
      ctx.lineTo(x2 - 3, TL.segTop + TL.segH / 2 - 3);
      ctx.stroke();
    }
  }

  // ── 镜头切点 / 节拍标记 ──
  const cuts = (S.analysis && S.analysis.scenes && S.analysis.scenes.cuts) || [];
  ctx.strokeStyle = 'rgba(76,147,247,.75)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const c of cuts) {
    const x = t2x(c.time, w);
    if (x < 0 || x > w) continue;
    ctx.moveTo(x + .5, TL.segTop + 2);
    ctx.lineTo(x + .5, TL.ruler);
  }
  ctx.stroke();

  const beats = (S.analysis && S.analysis.beats && S.analysis.beats.times) || [];
  if (beats.length && pxPerSec > 3) {
    ctx.strokeStyle = 'rgba(240,169,59,.8)';
    ctx.beginPath();
    for (const b of beats) {
      const x = t2x(b, w);
      if (x < 0 || x > w) continue;
      ctx.moveTo(x + .5, TL.ruler);
      ctx.lineTo(x + .5, TL.ruler + 7);
    }
    ctx.stroke();
  }

  // ── 播放头 ──
  const v = $('video');
  if (v && v.duration && !isNaN(v.currentTime)) {
    const x = t2x(v.currentTime, w);
    if (x >= 0 && x <= w) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + .5, 0); ctx.lineTo(x + .5, h);
      ctx.stroke();
      ctx.fillStyle = '#FFFFFF';
      ctx.beginPath();
      ctx.moveTo(x - 5, 0); ctx.lineTo(x + 5, 0); ctx.lineTo(x, 8);
      ctx.closePath(); ctx.fill();
    }
  }

  // ── 视野之外的暗角提示 ──
  if (vs > 0.01) {
    const g = ctx.createLinearGradient(0, TL.ruler, 26, TL.ruler);
    g.addColorStop(0, 'rgba(10,13,17,.85)'); g.addColorStop(1, 'rgba(10,13,17,0)');
    ctx.fillStyle = g; ctx.fillRect(0, TL.ruler, 26, h);
  }
  if (ve < dur - 0.01) {
    const x0 = w - 26;
    const g = ctx.createLinearGradient(w, TL.ruler, x0, TL.ruler);
    g.addColorStop(0, 'rgba(10,13,17,.85)'); g.addColorStop(1, 'rgba(10,13,17,0)');
    ctx.fillStyle = g; ctx.fillRect(x0, TL.ruler, 26, h - TL.ruler);
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// ── 时间线交互 ──────────────────────────────────────────────
function initTimeline() {
  const wrap = $('tlWrap');
  const cv = $('tl');
  let drag = null;

  cv.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = cv.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const w = rect.width;
    const at = x2t(mx, w);
    const factor = e.deltaY > 0 ? 1.18 : 1 / 1.18;
    const dur = S.duration || 1;
    let span = clamp((S.view.end - S.view.start) * factor, 0.15, dur);
    let s = at - (at - S.view.start) * (span / (S.view.end - S.view.start));
    let en = s + span;
    if (s < 0) { s = 0; en = span; }
    if (en > dur) { en = dur; s = Math.max(0, dur - span); }
    S.view = { start: s, end: en };
    drawTimelineSafe();
  }, { passive: false });

  cv.addEventListener('mousedown', (e) => {
    const rect = cv.getBoundingClientRect();
    drag = { x: e.clientX, y: e.clientY, moved: false, sx: e.clientX, view: { ...S.view } };
  });

  window.addEventListener('mousemove', (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.sx;
    if (Math.abs(dx) > 3 || Math.abs(e.clientY - drag.y) > 3) drag.moved = true;
    if (!drag.moved) return;
    const rect = cv.getBoundingClientRect();
    const w = rect.width;
    const span = drag.view.end - drag.view.start;
    const dur = S.duration || 1;
    let shift = -(dx / w) * span;
    let s = clamp(drag.view.start + shift, 0, Math.max(0, dur - span));
    S.view = { start: s, end: s + span };
    drawTimelineSafe();
  });

  window.addEventListener('mouseup', (e) => {
    if (!drag) return;
    const d = drag; drag = null;
    if (d.moved) return;
    const rect = cv.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (x < 0 || x > rect.width || y < 0 || y > rect.height) return;
    const t = clamp(x2t(x, rect.width), 0, S.duration);

    // 片段轨上点击 → 停用/启用该片段；标尺/波形上点击 → 定位
    if (y >= TL.segTop && S.plan) {
      const idx = S.plan.segments.findIndex((s) => t >= s.start && t < s.end);
      if (idx >= 0) {
        if (S.disabled.has(idx)) S.disabled.delete(idx); else S.disabled.add(idx);
        renderPlanStats(S.plan);
        drawTimelineSafe();
        status(S.disabled.has(idx)
          ? `已停用第 ${idx + 1} 段（导出时跳过）`
          : `已恢复第 ${idx + 1} 段`);
        return;
      }
    }
    seekTo(t);
  });

  $('btnTlFit').addEventListener('click', () => {
    S.view = { start: 0, end: S.duration || 1 };
    drawTimelineSafe();
  });
  $('btnTlReset').addEventListener('click', () => {
    S.disabled.clear();
    if (S.plan) renderPlanStats(S.plan);
    drawTimelineSafe();
    status('已还原全部片段');
  });

  new ResizeObserver(() => drawTimelineSafe()).observe(wrap);
}

// ── 播放器 ──────────────────────────────────────────────────
function seekTo(t) {
  const v = $('video');
  if (!v.src) return;
  v.currentTime = clamp(t, 0, v.duration || S.duration || 0);
  syncTransport();
}

function syncTransport() {
  const v = $('video');
  const t = v.currentTime || 0;
  const d = v.duration || S.duration || 0;
  $('timeNow').textContent = fmtTime(t);
  $('timeTotal').textContent = fmtTime(d);
  const p = d ? clamp(t / d, 0, 1) : 0;
  $('seekFill').style.width = (p * 100) + '%';
  $('seekHead').style.left = (p * 100) + '%';
}

function initPlayer() {
  const v = $('video');
  const draw = () => { drawTimelineSafe(); syncTransport(); };
  v.addEventListener('timeupdate', () => { syncTransport(); drawTimelineSafe(); });
  v.addEventListener('loadedmetadata', () => {
    S.duration = v.duration || S.duration;
    if (!S.view.end || S.view.end <= 1) S.view = { start: 0, end: S.duration };
    // 用真实元信息补全左栏
    if (S.media && (!S.media.width || !S.media.duration)) {
      S.media.width = v.videoWidth; S.media.height = v.videoHeight;
      S.media.duration = v.duration; S.media.name = S.media.name || '已载入素材';
      renderMediaInfo(S.media);
    }
    draw();
  });
  v.addEventListener('play', () => {
    $('iconPlay').innerHTML = '<path d="M7 5h3.2v14H7zM13.8 5H17v14h-3.2z" fill="currentColor"/>';
  });
  v.addEventListener('pause', () => {
    $('iconPlay').innerHTML = '<path d="M8 5.5v13l10.5-6.5L8 5.5Z" fill="currentColor"/>';
  });

  $('btnPlay').addEventListener('click', () => { v.paused ? v.play() : v.pause(); });
  $('rate').addEventListener('change', (e) => { v.playbackRate = parseFloat(e.target.value); });

  const seek = $('seek');
  const doSeek = (e) => {
    const r = seek.getBoundingClientRect();
    const p = clamp((e.clientX - r.left) / r.width, 0, 1);
    seekTo(p * (v.duration || S.duration || 0));
  };
  let seeking = false;
  seek.addEventListener('mousedown', (e) => { seeking = true; doSeek(e); });
  window.addEventListener('mousemove', (e) => { if (seeking) doSeek(e); });
  window.addEventListener('mouseup', () => { seeking = false; });

  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.code === 'Space') { e.preventDefault(); v.paused ? v.play() : v.pause(); }
    if (e.code === 'ArrowLeft') { e.preventDefault(); seekTo(v.currentTime - (e.shiftKey ? 1 : 1 / 30)); }
    if (e.code === 'ArrowRight') { e.preventDefault(); seekTo(v.currentTime + (e.shiftKey ? 1 : 1 / 30)); }
    if (e.code === 'KeyJ') seekTo(v.currentTime - 5);
    if (e.code === 'KeyL') seekTo(v.currentTime + 5);
  });
}

// ── 渲染 ────────────────────────────────────────────────────
async function startRender(preview) {
  if (!S.plan) return toast('先生成方案', 'err');
  const plan = JSON.parse(JSON.stringify(S.plan));
  if (S.disabled.size) {
    plan.segments = plan.segments.filter((_, i) => !S.disabled.has(i));
  }
  if (!plan.segments.length) return toast('所有片段都被停用了', 'err');

  // 音频参数以界面上当前的值为准。
  // 方案是「生成方案」那一刻的快照，而调音是随时随地在调的；
  // 不在这里覆盖的话，用户改完音色直接点导出，出来的还是旧参数，
  // 而且没有任何提示——这种「设置没生效」最难查。
  plan.audio = readAudio();

  $('btnRender').disabled = true;
  $('btnPreview').disabled = true;
  status(preview ? '预览渲染中（低清）…' : '正在导出成片…');
  progress(0);
  try {
    const r = await postJSON('/api/render', { plan, preview });
    pollJob(r.job);
  } catch (e) {
    progress(null);
    $('btnRender').disabled = false;
    $('btnPreview').disabled = false;
    toast('渲染启动失败：' + e.message, 'err');
  }
}

function pollJob(id) {
  S.job = id;
  clearInterval(S.jobTimer);
  S.jobTimer = setInterval(async () => {
    let job;
    try { job = await api('/api/job/' + id); } catch (e) { return; }
    if (job.status === 'running') {
      progress(job.percent || 0);
      status(job.message || '渲染中…',
        job.speed ? `x${job.speed} · ${fmtDur(job.done)}/${fmtDur(job.total)}` : '');
      return;
    }
    clearInterval(S.jobTimer);
    S.job = null;
    progress(null);
    $('btnRender').disabled = false;
    $('btnPreview').disabled = false;
    if (job.status === 'done') {
      status(`完成：${job.name} · ${fmtSize(job.size)} · 用时 ${job.elapsed}s`);
      toast('渲染完成', 'ok');
      showResult(job);
    } else {
      status('渲染失败');
      toast('渲染失败：' + (job.error || '未知错误'), 'err');
    }
  }, 500);
}

function showResult(job) {
  const v = $('video');
  const wasAt = v.currentTime;
  const wasPlaying = !v.paused;
  v.src = '/api/result/' + job.id;
  v.load();
  v.addEventListener('loadedmetadata', function once() {
    v.removeEventListener('loadedmetadata', once);
    v.currentTime = 0;
  });
  status(`完成：${job.name}。播放器已切到成片，下载请点「导出成片」旁的链接。`);
  const right = $('statusRight');
  right.innerHTML = `<a href="/api/result/${job.id}" download style="color:var(--accent);text-decoration:none">下载 ${job.name}</a>`;
}

// ── 音频处理 ────────────────────────────────────────────────
// 服务端是这套参数的唯一权威：枚举、文案、每个预设展开后的完整值都由
// /api/audio/presets 给过来。前端只负责填表和读表，不自己维护一份默认值——
// 两边各存一份迟早会对不上。
const AUDIO_SLIDERS = {
  highpass: 'vHp', lowpass: 'vLp', gate_db: 'vGate',
  warmth: 'vWarm', presence: 'vPres', deess: 'vDeess',
  comp_db: 'vComp', comp_ratio: 'vRatio', gain_db: 'vGain',
};
const AUDIO_CHECKBOXES = ['gate', 'compress'];
const AUDIO_SELECTS = ['denoise'];
const AUDIO_NUM_KEYS = Object.keys(AUDIO_SLIDERS).concat(['comp_ratio']);
const AUDIO_CATALOG = { presets: [], defaults: {}, strong_gate_db: -38 };

function audioDefaults() {
  return Object.assign({}, AUDIO_CATALOG.defaults);
}

function readAudio() {
  const spec = audioDefaults();
  for (const id of AUDIO_SELECTS) { if ($(id)) spec[id] = $(id).value; }
  for (const id of AUDIO_CHECKBOXES) { if ($(id)) spec[id] = $(id).checked; }
  for (const id of AUDIO_NUM_KEYS) {
    if ($(id)) spec[id] = parseFloat($(id).value);
  }
  const seg = $('stereo');
  if (seg) {
    const on = seg.querySelector('button.active');
    if (on) spec.stereo = on.dataset.v;
  }
  spec.preset = S.audioPreset || 'custom';
  return spec;
}

function writeAudio(spec) {
  const s = Object.assign(audioDefaults(), spec || {});
  for (const id of AUDIO_SELECTS) { if ($(id)) $(id).value = s[id]; }
  for (const id of AUDIO_CHECKBOXES) { if ($(id)) $(id).checked = !!s[id]; }
  for (const id of AUDIO_NUM_KEYS) { if ($(id)) $(id).value = s[id]; }
  const seg = $('stereo');
  if (seg) {
    [...seg.children].forEach((b) => b.classList.toggle('active', b.dataset.v === s.stereo));
  }
  syncAudioUI();
}

// 联动显示 + 数字标签 + 生效徽标，全部集中在这里，
// 免得每个事件回调各更新一半、出现界面和状态不一致。
function syncAudioUI() {
  const gateOn = $('gate') && $('gate').checked;
  const compOn = $('compress') && $('compress').checked;
  document.querySelectorAll('#audioPanel [data-when]').forEach((el) => {
    const key = el.dataset.when;
    const on = key === 'gate' ? gateOn : key === 'compress' ? compOn : false;
    el.hidden = !on;
  });
  for (const [id, labelId] of Object.entries(AUDIO_SLIDERS)) {
    if ($(id) && $(labelId)) $(labelId).textContent = $(id).value;
  }
  refreshAudioBadge();
}

function refreshAudioBadge() {
  const badge = $('audioBadge');
  if (!badge) return;
  const a = readAudio();
  const on = [];
  if (a.denoise && a.denoise !== 'none') on.push('降噪');
  if (a.highpass > 0) on.push('低切');
  if (a.lowpass > 0) on.push('高切');
  if (a.gate) on.push('噪声门');
  if (a.warmth || a.presence || a.deess) on.push('EQ');
  if (a.compress) on.push('压缩');
  if (a.stereo && a.stereo !== 'keep') on.push('立体声');
  if (a.gain_db) on.push('增益');
  badge.textContent = on.length ? on.length + ' 项生效' : '关闭';
  badge.classList.toggle('on', on.length > 0);
}

async function initAudio() {
  try {
    const r = await api('/api/audio/presets');
    AUDIO_CATALOG.presets = r.presets || [];
    AUDIO_CATALOG.defaults = r.defaults || {};
    AUDIO_CATALOG.strong_gate_db = r.strong_gate_db;
  } catch (e) {
    return;   // 拿不到目录就保持表单静态，不影响剪辑功能
  }

  const sel = $('audioPreset');
  sel.innerHTML = '';
  for (const p of AUDIO_CATALOG.presets) {
    const o = document.createElement('option');
    o.value = p.id; o.textContent = p.label;
    sel.appendChild(o);
  }

  sel.addEventListener('change', () => {
    const p = AUDIO_CATALOG.presets.find((x) => x.id === sel.value);
    if (!p) return;
    S.audioPreset = p.id;
    // 整份重填，不合并——合并会让上一个预设独有的参数残留下来
    writeAudio(p.spec);
    $('audioHint').textContent = p.hint;
    if (S.media) auditionSoon();
  });

  for (const id of AUDIO_NUM_KEYS.concat(AUDIO_CHECKBOXES)) {
    const el = $(id);
    if (!el) continue;
    el.addEventListener('input', () => { S.audioPreset = 'custom'; syncAudioUI(); });
    el.addEventListener('change', () => { S.audioPreset = 'custom'; syncAudioUI(); });
  }
  for (const id of AUDIO_SELECTS) {
    if ($(id)) $(id).addEventListener('change', () => { S.audioPreset = 'custom'; syncAudioUI(); });
  }
  const seg = $('stereo');
  if (seg) {
    seg.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-v]');
      if (!btn) return;
      [...seg.children].forEach((b) => b.classList.toggle('active', b === btn));
      S.audioPreset = 'custom';
      syncAudioUI();
    });
  }

  $('btnSuggest').addEventListener('click', suggestAudio);
  $('btnAudition').addEventListener('click', audition);
  writeAudio(audioDefaults());
}

// 自动档：先量底噪，再按实测值给建议。量不出来就退回「口播」预设并说明。
async function suggestAudio() {
  if (!S.media) return;
  const btn = $('btnSuggest');
  btn.classList.add('busy');
  status('正在量素材底噪…');
  try {
    const outdoor = S.mode === 'outdoor';
    const r = await postJSON('/api/audio/suggest', { outdoor });
    const p = r.probe || {};
    const bits = [`底噪 ${p.noise_floor_db}dB`, `SNR ${p.snr_db}dB`];
    if (p.has_hum) bits.push(`检出工频哼声（${p.hum_db}dB）`);
    const box = $('probeOut');
    box.hidden = false;
    box.textContent = '实测：' + bits.join(' · ');
    S.audioPreset = 'custom';
    writeAudio(r.spec);
    $('audioHint').textContent = (r.why || []).join('；');
    status('已按实测底噪填好音频参数');
    if (S.plan) $('btnAudition').disabled = false;
  } catch (e) {
    toast('测量失败：' + e.message, 'err');
  } finally {
    btn.classList.remove('busy');
  }
}

let auditionTimer = null;
function auditionSoon() {
  // 连点预设时会连发请求，每个都要渲染一遍音轨，没必要
  clearTimeout(auditionTimer);
  auditionTimer = setTimeout(audition, 400);
}

async function audition() {
  if (!S.media) return toast('先导入素材', 'err');
  const btn = $('btnAudition');
  btn.classList.add('busy');
  status('正在渲染试听音轨…');
  try {
    const body = { audio: readAudio() };
    if (S.plan) body.plan = S.plan;
    const r = await postJSON('/api/audio/audition', body);
    const player = $('auditionPlayer');
    player.src = r.url;
    player.hidden = false;
    player.play().catch(() => {});   // 浏览器可能拦截自动播放，用户手动点即可
    const hint = $('auditionHint');
    hint.textContent = r.active && r.active.length
      ? '已生效：' + r.active.join(' · ')
      : '当前没有任何音频处理生效，听到的是原声。';
    if (r.warnings && r.warnings.length) hint.textContent += ' ⚠ ' + r.warnings[0];
    status('试听音轨已就绪（' + fmtSize(r.size) + '）');
  } catch (e) {
    toast('试听失败：' + e.message, 'err');
  } finally {
    btn.classList.remove('busy');
  }
}

// ── 启动 ────────────────────────────────────────────────────
async function boot() {
  initParams();
  initModes();
  initDrop();
  initTimeline();
  initPlayer();
  await initAudio();

  // 支持 ?mode=beat / ?mode=scene 直达某个模式
  const wanted = new URLSearchParams(location.search).get('mode');
  if (wanted && MODES.includes(wanted)) {
    S.mode = wanted;
    syncModeUI();
  }

  $('btnAnalyze').addEventListener('click', analyze);
  $('btnPlan').addEventListener('click', () => { autoplan(); toast('方案已更新', 'ok'); });
  $('btnPreview').addEventListener('click', () => startRender(true));
  $('btnRender').addEventListener('click', () => startRender(false));

  try {
    const st = await api('/api/state');
    if (st.media) {
      $('pathInput').value = st.media;
      if (st.music) $('musicInput').value = st.music;
      // 服务端已经预挂了素材：先挂到界面再分析，否则 analyze() 会因 S.media 为空直接返回
      await loadMedia(blankMeta(st.media_name, st.media, 0));
      await autoplan();
    } else {
      status('就绪 · 拖入素材或粘贴路径开始');
    }
    const d = await api('/api/doctor');
    if (!d.ok) {
      toast('还没找到 ffmpeg，请先运行 scripts/doctor.py --fix', 'err');
    }
  } catch (e) {
    status('初始化失败：' + e.message);
  }
  drawTimelineSafe();
}

document.addEventListener('DOMContentLoaded', boot);
