'use strict';
/* HeliysStudio Mini App — vanilla JS, без сборки. */
const tg = window.Telegram && window.Telegram.WebApp;
const $ = (s, r = document) => r.querySelector(s);
const root = $('#root');
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const QS = new URLSearchParams(location.search);
const DEV_USER = QS.get('dev');

/* ---------- иконки (Lucide-style) ---------- */
const P = {
  home: '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88"/><path d="M14.47 14.48 20 20"/><path d="M8.12 8.12 12 12"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"/>',
  crown: '<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7z"/><path d="M3 20h18"/>',
  star: '<path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  back: '<path d="m15 18-6-6 6-6"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  wallet: '<path d="M20 12V8H6a2 2 0 0 1 0-4h12v4"/><path d="M4 6v12a2 2 0 0 0 2 2h14v-4"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/>',
  megaphone: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  chart: '<path d="M3 3v18h18"/><path d="M18 17V9M13 17V5M8 17v-3"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  zap: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  play: '<path d="m6 3 14 9-14 9z"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/>',
};
const ic = (n, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[n]}</svg>`;
const starIc = ic('star', 'fill');

/* ---------- утилиты ---------- */
const fmtDate = (ts) => new Date(ts * 1000).toLocaleString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
const fmtShort = (ts) => new Date(ts * 1000).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
const hap = (t) => { try { t === 'light' ? tg.HapticFeedback.impactOccurred('light') : tg.HapticFeedback.notificationOccurred(t); } catch (_) {} };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 320); }, 2800);
  if (type === 'err') hap('error');
}

async function api(path, { method, json, form } = {}) {
  const headers = { 'X-Init-Data': (tg && tg.initData) || '' };
  if (DEV_USER) { headers['X-Dev-User'] = DEV_USER; if (QS.get('name')) headers['X-Dev-Name'] = encodeURIComponent(QS.get('name')); }
  let body;
  if (json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  else if (form) body = form;
  try {
    const r = await fetch(path, { method: method || (body ? 'POST' : 'GET'), headers, body });
    return await r.json();
  } catch (_) {
    return { ok: false, error: 'network' };
  }
}

async function fetchBlobUrl(path) {
  const headers = { 'X-Init-Data': (tg && tg.initData) || '' };
  if (DEV_USER) headers['X-Dev-User'] = DEV_USER;
  const r = await fetch(path, { headers });
  if (!r.ok) throw new Error('fetch');
  return URL.createObjectURL(await r.blob());
}

function pickFile() {
  return new Promise((resolve) => {
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = 'image/*';
    inp.onchange = () => resolve(inp.files[0] || null);
    inp.click();
  });
}

/* уменьшаем слишком тяжёлые фото перед загрузкой */
async function shrink(file, maxSide, minBytes = 0) {
  if (file.size < minBytes) return file;
  try {
    const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const k = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
    if (k === 1 && file.size < 12e6) return file;
    const c = document.createElement('canvas');
    c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    return await new Promise((res) => c.toBlob((b) => res(b || file), 'image/jpeg', 0.92));
  } catch (_) { return file; }
}

async function copyText(t) {
  try { await navigator.clipboard.writeText(t); }
  catch (_) { const a = document.createElement('textarea'); a.value = t; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); } catch (__) {} a.remove(); }
  hap('light'); toast('Скопировано', 'good');
}

/* безопасный рендер Telegram-HTML для предпросмотра приветствия */
function renderTgHtml(html) {
  const allowed = new Set(['B', 'STRONG', 'I', 'EM', 'U', 'INS', 'S', 'STRIKE', 'DEL', 'CODE', 'PRE', 'A', 'TG-EMOJI', 'TG-SPOILER', 'BLOCKQUOTE']);
  const doc = new DOMParser().parseFromString('<div>' + html.replace(/\{name\}/g, S.me ? S.me.first_name || 'друг' : 'друг') + '</div>', 'text/html');
  const walk = (node) => {
    let out = '';
    node.childNodes.forEach((n) => {
      if (n.nodeType === 3) out += esc(n.textContent);
      else if (n.nodeType === 1) {
        const t = n.tagName;
        if (t === 'TG-EMOJI') out += `<span class="pemoji" title="Премиум-эмодзи">${esc(n.textContent)}</span>`;
        else if (allowed.has(t)) {
          const tag = t.toLowerCase().replace('tg-spoiler', 'span');
          out += `<${tag}${t === 'A' ? ' href="#"' : ''}>${walk(n)}</${tag}>`;
        } else out += walk(n);
      }
    });
    return out;
  };
  return walk(doc.body.firstChild);
}

/* ---------- состояние ---------- */
const S = {
  me: null, missing: [], tab: 'home', tool: 'slice',
  slice: { src: null, url: '', parts: 3, mode: 'fill', asFile: true, busy: false },
  frame: { has: false, loading: false, refreshing: false, palettes: [], previews: [], cats: [], cat: 'all', hq: null, palette: 0, style: 'neon', busy: false },
  admin: { view: null },
};
const canGen = () => S.me.premium || S.me.free_left + S.me.balance > 0;

/* ---------- каркас ---------- */
function mount(html, anim = false) {
  const v = $('#view');
  const prev = v.firstElementChild;
  const top = prev ? prev.scrollTop : 0;
  v.innerHTML = `<div class="view ${anim ? '' : 'noanim'}">${html}</div>`;
  if (!anim) v.firstElementChild.scrollTop = top;
}

function shell() {
  const tabs = [['home', 'home', 'Главная'], ['profile', 'user', 'Профиль']];
  if (S.me.is_admin) tabs.push(['admin', 'shield', 'Админ']);
  root.innerHTML = `<div id="view"></div>
    <nav class="tabbar" aria-label="Разделы">
      <i class="pill" style="width:calc((100% - 12px)/${tabs.length})"></i>
      ${tabs.map(([id, i, l]) => `<button data-act="goto" data-v="${id}" data-tab="${id}" aria-label="${l}">${ic(i)}<span>${l}</span></button>`).join('')}
    </nav>`;
  S._tabs = tabs.map((t) => t[0]);
}

function go(tab, anim = true) {
  S.tab = tab;
  const idx = S._tabs.indexOf(tab);
  const pill = $('.tabbar .pill');
  pill.style.transform = `translateX(${idx * 100}%)`;
  document.querySelectorAll('.tabbar button').forEach((b) => b.classList.toggle('on', b.dataset.tab === tab));
  if (tab === 'home') mount(homeHTML(), anim);
  else if (tab === 'profile') mount(profileHTML(), anim);
  else renderAdmin(anim);
}
const refresh = () => go(S.tab, false);

/* ---------- старт ---------- */
async function boot() {
  try {
    if (tg) {
      tg.ready(); tg.expand();
      tg.setHeaderColor && tg.setHeaderColor('#05050a');
      tg.setBackgroundColor && tg.setBackgroundColor('#05050a');
      tg.setBottomBarColor && tg.setBottomBarColor('#05050a');
      tg.disableVerticalSwipes && tg.disableVerticalSwipes();
    }
  } catch (_) {}
  root.innerHTML = splash('Загрузка…');
  const r = await api('/api/me');
  if (!r.ok) {
    if (r.error === 'banned') return (root.innerHTML = splash('Доступ ограничен', 'Ваш аккаунт заблокирован администратором.', false));
    return (root.innerHTML = splash('Не удалось подключиться', r.error === 'unauthorized' ? 'Откройте приложение через бота в Telegram.' : 'Проверьте интернет и попробуйте ещё раз.', false, true));
  }
  S.me = r.me; S.missing = r.missing;
  if (S.missing.length) return showGate();
  startApp();
}

function logo() {
  return `<svg class="logo" viewBox="0 0 100 100"><circle class="ring" cx="50" cy="50" r="42" fill="none" stroke="url(#lg)" stroke-width="7" stroke-linecap="round"/><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8b5cf6"/><stop offset="1" stop-color="#f0529c"/></linearGradient></defs><g fill="none" stroke="#f5f5f7" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" transform="translate(30 30) scale(1.67)"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88"/><path d="M14.47 14.48 20 20"/><path d="M8.12 8.12 12 12"/></g></svg>`;
}
function splash(title, sub = '', spinner = true, retry = false) {
  return `<div class="splash">${logo()}<div class="h1">${esc(title)}</div>${sub ? `<div class="muted">${esc(sub)}</div>` : ''}${spinner ? '<span class="spin"></span>' : ''}${retry ? '<button class="btn primary" data-act="reload">Повторить</button>' : ''}</div>`;
}

function showGate() {
  root.innerHTML = `<div class="splash">
    <div class="big-ico">${ic('link')}</div>
    <div class="h1">Подпишись, чтобы продолжить</div>
    <div class="muted">Для доступа к приложению нужна подписка на каналы:</div>
    <div style="width:100%" class="stack">${S.missing.map((m) => `<button class="btn ghost block" data-act="open-link" data-v="${esc(m.link)}">${ic('send')}${esc(m.title)}</button>`).join('')}</div>
    <button class="btn primary block" data-act="recheck" id="recheck">Я подписался</button></div>`;
}

function startApp() {
  shell();
  go('home');
  if (!S.me.tutorial_seen) showOnboarding(true);
}

/* ---------- главная ---------- */
function creditChip() {
  const me = S.me;
  return me.premium
    ? `<button class="credit prem" data-act="goto" data-v="profile" aria-label="Premium активен">${ic('crown')}<b>∞</b><small>Premium</small></button>`
    : `<button class="credit" data-act="paywall" aria-label="Остаток генераций">${ic('zap')}<b>${me.free_left + me.balance}</b><small>ген.</small></button>`;
}

function homeHTML() {
  const me = S.me;
  return `<div class="topbar"><div class="hello"><small>Привет,</small><div class="h1">${esc(me.first_name || 'друг')}</div></div>${creditChip()}</div>
    <div class="tools" role="tablist" aria-label="Инструмент">
      <button class="tool ${S.tool === 'slice' ? 'on' : ''}" role="tab" aria-selected="${S.tool === 'slice'}" data-act="tool" data-v="slice"><span class="ico">${ic('scissors')}</span><b>Сториз</b><span class="sub">нарезка на 1–6 частей</span></button>
      <button class="tool ${S.tool === 'frame' ? 'on' : ''}" role="tab" aria-selected="${S.tool === 'frame'}" data-act="tool" data-v="frame"><span class="ico">${ic('image')}</span><b>Рамка</b><span class="sub">37 стилей для аватарки</span></button></div>
    <div class="gap"></div>
    ${S.tool === 'slice' ? sliceHTML() : frameHTML()}`;
}

function sliceHTML() {
  const s = S.slice, me = S.me;
  if (!s.src) {
    return `<button class="drop" data-act="slice-pick"><span class="ico">${ic('upload')}</span>
      <b>Загрузи фото для сториз</b>
      <span class="muted small">Нарежем на части 1080×1920 — выкладывай по порядку</span></button>
      <div class="facts"><div class="fact"><b class="grad-text">1080×1920</b><span>размер каждой части</span></div><div class="fact"><b class="grad-text">без сжатия</b><span>файлами в чат</span></div></div>
      ${me.has_pending ? `<div class="src-grid"><button class="btn ghost" data-act="slice-pending">${ic('image')}Использовать фото из чата</button></div>` : ''}`;
  }
  const ratio = (s.parts * 9) / 16;
  const cost = me.premium ? 'Premium · без лимита' : '−1 генерация';
  return `<div class="card">
    <div class="stage ${s.mode === 'fit' ? 'fit' : ''}" style="aspect-ratio:${s.parts * 9}/16;width:min(100%, calc(46vh * ${ratio.toFixed(3)}))">
      <img class="bgimg" src="${s.url}" alt=""><img class="fgimg" src="${s.url}" alt="Фото для нарезки">
      <div class="cuts">${Array.from({ length: s.parts }, (_, i) => `<span><b>${i + 1}</b></span>`).join('')}</div>
    </div>
    <div class="field-label">Количество частей</div>
    <div class="nums">${[1, 2, 3, 4, 5, 6].map((n) => `<button class="${n === s.parts ? 'on' : ''}" data-act="parts" data-v="${n}" aria-label="${n} частей">${n}</button>`).join('')}</div>
    <div class="field-label">Как вписать фото</div>
    <div class="seg"><i class="pill" style="transform:translateX(${s.mode === 'fit' ? 100 : 0}%)"></i>
      <button class="${s.mode === 'fill' ? 'on' : ''}" data-act="mode" data-v="fill">Заполнить</button>
      <button class="${s.mode === 'fit' ? 'on' : ''}" data-act="mode" data-v="fit">Вписать</button></div>
    <button class="switch ${s.asFile ? 'on' : ''}" data-act="asfile" role="switch" aria-checked="${s.asFile}"><span>Отправить файлами (без сжатия)</span><i></i></button>
    <div class="gap"></div>
    <button class="btn primary block" data-act="do-slice" ${s.busy ? 'disabled' : ''}>${s.busy ? '<span class="spin"></span>Нарезаю…' : `${ic('scissors')}Нарезать · ${cost}`}</button>
    <button class="btn ghost block" style="margin-top:10px" data-act="slice-reset" ${s.busy ? 'disabled' : ''}>Другое фото</button>
  </div>`;
}

function frameHTML() {
  const f = S.frame, me = S.me;
  if (!f.has && !f.loading) {
    return `<div class="card"><div class="h2">Рамка под цвет аватарки</div>
      <div class="muted small">Загрузи аватарку — подберём палитру из фото и покажем 8 стилей.</div>
      <div class="src-grid">
        <button class="btn ghost" data-act="frame-file">${ic('upload')}Загрузить фото</button>
        <button class="btn ghost" data-act="frame-avatar">${ic('user')}Моя аватарка</button>
        ${me.has_pending ? `<button class="btn ghost" data-act="frame-pending">${ic('image')}Фото из чата</button>` : ''}
      </div></div>`;
  }
  if (f.loading && !f.has) {
    return `<div class="card"><div class="preview-big"><div class="skel" style="width:100%;height:100%;border-radius:50%"></div></div>
      <div class="styles">${Array.from({ length: 8 }, () => '<div class="skel" style="aspect-ratio:1"></div>').join('')}</div></div>`;
  }
  const cur = f.previews.find((p) => p.id === f.style) || f.previews[0];
  const pal = f.palettes[f.palette];
  const cost = me.premium ? 'Premium · без лимита' : '−1 генерация';
  const big = f.hq && f.hq.key === `${f.style}|${f.palette}` ? f.hq.img : cur.img;
  const list = f.previews.filter((p) => f.cat === 'all' || p.cat === f.cat);
  const count = (id) => (id === 'all' ? f.previews.length : f.previews.filter((p) => p.cat === id).length);
  return `<div class="card">
    <div class="preview-sticky"><div class="preview-big"><img src="${big}" alt="Рамка ${esc(cur.name)}" id="bigprev"></div>
      <div class="center small muted">${esc(cur.name)} · ${cur.themed ? 'свои цвета' : esc(pal.name)}</div></div>
    <div class="field-label">Цвет рамки — подобран под твоё фото</div>
    <div class="swatches ${cur.themed ? 'dim' : ''}">${f.palettes.map((p, i) => `<button class="sw ${i === f.palette ? 'on' : ''}" data-act="palette" data-v="${i}" aria-label="${esc(p.name)}"><i style="background:linear-gradient(135deg,${p.c1},${p.c2})"></i></button>`).join('')}</div>
    ${cur.themed ? '<div class="note">У этой рамки свои цвета — палитра на неё не влияет.</div>' : ''}
    <div class="field-label">Стиль рамки</div>
    <div class="cats">${f.cats.map(([id, l]) => `<button class="cat ${id === f.cat ? 'on' : ''}" data-act="cat" data-v="${id}">${l}<em>${count(id)}</em></button>`).join('')}</div>
    <div class="styles" style="${f.refreshing ? 'opacity:.5;transition:opacity .2s' : ''}">${list.map((p) => `<div class="cell ${p.id === f.style ? 'on' : ''}"><button class="sty ${p.id === f.style ? 'on' : ''}" data-act="style" data-v="${p.id}" aria-label="${esc(p.name)}"><img src="${p.img}" alt="" loading="lazy" decoding="async"></button><div class="sty-name">${esc(p.name)}</div></div>`).join('')}</div>
    <div class="gap"></div>
    <button class="btn primary block" data-act="do-frame" ${f.busy ? 'disabled' : ''}>${f.busy ? '<span class="spin"></span>Рисую…' : `${ic('image')}Получить рамку · ${cost}`}</button>
    <button class="btn ghost block" style="margin-top:10px" data-act="frame-reset" ${f.busy ? 'disabled' : ''}>Другое фото</button>
  </div>`;
}

let hqToken = 0;
async function loadHQ() {
  const f = S.frame, key = `${f.style}|${f.palette}`;
  if (f.hq && f.hq.key === key) return;
  const t = ++hqToken;
  const r = await api('/api/frames/hq', { json: { style: f.style, palette: f.palette } });
  if (t !== hqToken || !r.ok) return;
  f.hq = { key, img: r.img };
  const el = $('#bigprev');
  if (el && `${f.style}|${f.palette}` === key) el.src = r.img;
}

async function frameLoad(source, file) {
  const f = S.frame;
  f.loading = true; f.has = false; refresh();
  const fd = new FormData();
  fd.append('source', source);
  if (file) fd.append('file', await shrink(file, 1600), 'avatar.jpg');
  const r = await api('/api/frames/upload', { form: fd });
  f.loading = false;
  if (!r.ok) {
    refresh();
    return toast({ no_avatar: 'У тебя нет доступной аватарки — загрузи фото', bad_image: 'Не удалось прочитать изображение', too_big: 'Файл слишком большой', no_pending: 'Фото из чата не найдено' }[r.error] || 'Ошибка загрузки', 'err');
  }
  Object.assign(f, { has: true, palettes: r.palettes, previews: r.previews, cats: r.cats, cat: 'all', palette: 0, style: 'neon', hq: null });
  hap('light'); refresh(); loadHQ();
}

/* результат генерации */
async function afterGen(r, kind) {
  if (r.ok) {
    S.me = r.me; hap('success');
    const left = S.me.premium ? 'Premium: без лимита' : `Осталось генераций: ${S.me.free_left + S.me.balance}`;
    openSheet(`<div class="center"><div class="big-ico okk">${ic('check')}</div>
      <div class="h2">Готово!</div>
      <div class="muted">${kind === 'slice' ? 'Части сториз отправлены' : 'Рамка отправлена'} в чат с ботом.<br>${left}</div>
      <div class="gap"></div>
      <button class="btn primary block" data-act="close-app">${ic('send')}Открыть чат</button>
      <button class="btn ghost block" style="margin-top:10px" data-act="close-sheet">Ещё</button></div>`);
    refresh();
    return;
  }
  const e = r.error;
  if (e === 'no_credits') return paywall();
  if (e === 'not_subscribed') { S.missing = r.missing; return showGate(); }
  if (e === 'start_bot') return openSheet(`<div class="center"><div class="big-ico">${ic('send')}</div><div class="h2">Сначала запусти бота</div><div class="muted">Нажми /start в чате с ботом — тогда он сможет присылать результат.</div><div class="gap"></div><button class="btn primary block" data-act="close-app">Открыть чат</button></div>`);
  toast({ bad_image: 'Не удалось прочитать изображение', too_big: 'Файл слишком большой (макс. 25 МБ)', no_source: 'Фото устарело — загрузи заново', send_failed: 'Не удалось отправить в чат', network: 'Нет соединения' }[e] || 'Ошибка, попробуй ещё раз', 'err');
}

/* ---------- профиль ---------- */
function profileHTML() {
  const me = S.me, p = me.prices;
  const initials = (me.first_name || me.username || '?').trim().slice(0, 1).toUpperCase();
  const face = me.photo_url ? `<div class="face" style="background-image:url('${esc(me.photo_url)}')" role="img" aria-label="Аватарка"></div>` : `<div class="face">${esc(initials)}</div>`;
  return `<div class="hero"><div class="ava">${face}${me.premium ? `<span class="crown">${ic('crown', 'fill')}</span>` : ''}</div>
      <div class="h1" style="margin-top:16px">${esc([me.first_name, me.last_name].filter(Boolean).join(' ') || 'Без имени')}</div>
      <div class="muted">${me.username ? '@' + esc(me.username) : 'username не указан'}</div>
      ${me.premium ? `<span class="chip prem" style="margin-top:10px">${ic('crown')}Premium активен</span>` : ''}</div>
    <div class="bento">
      <div class="metric hot"><b>${me.premium ? '∞' : me.free_left}</b><span>бесплатных осталось</span></div>
      <div class="metric"><b>${me.balance}</b><span>купленных генераций</span></div>
      <div class="metric w2" style="grid-column:1/-1"><div class="row between"><div><b>${me.gens_total}</b><span>всего сделано рамок и нарезок</span></div><span class="chip gold">${ic('zap')}в студии</span></div></div>
      <div class="card w2" style="padding:4px 16px">
        <button class="kv" style="width:100%" data-act="copy" data-v="${me.id}"><span>Telegram ID</span><b class="mono">${me.id} ${ic('copy')}</b></button>
        <div class="kv"><span>Впервые запустил бота</span><b>${fmtDate(me.joined_at)}</b></div>
      </div>
    </div>
    <div class="gap"></div>
    <div class="h2" style="margin-bottom:10px">Магазин</div>
    <div class="shop">
      <button class="offer" data-act="buy" data-v="pack"><span class="ico">${ic('zap')}</span><span class="grow"><b>${p.pack_size} генераций</b><br><span class="muted small">Для нарезки и рамок</span></span><span class="price">${p.pack_price}${starIc}</span></button>
      ${me.premium
        ? `<div class="offer prem"><span class="ico">${ic('crown')}</span><span class="grow"><b>Premium активен</b><br><span class="muted small">Безлимитные рамки и нарезка</span></span>${ic('check')}</div>`
        : `<button class="offer prem" data-act="buy" data-v="premium"><span class="ico">${ic('crown')}</span><span class="grow"><b>Premium навсегда</b><br><span class="muted small">Рамки и нарезка без ограничений</span></span><span class="price">${p.premium_price}${starIc}</span></button>`}
    </div>
    <div class="gap"></div>
    <button class="btn ghost block" data-act="tutorial">${ic('play')}Показать обучение</button>`;
}

/* ---------- оплата ---------- */
function paywall() {
  const p = S.me.prices;
  openSheet(`<div class="center"><div class="big-ico">${ic('zap')}</div>
    <div class="h2">Генерации закончились</div>
    <div class="muted">Выбери, как продолжить. Оплата Telegram Stars — только здесь, в приложении.</div></div>
    <div class="gap"></div>
    <div class="shop">
      <button class="offer" data-act="buy" data-v="pack"><span class="ico">${ic('zap')}</span><span class="grow"><b>${p.pack_size} генераций</b></span><span class="price">${p.pack_price}${starIc}</span></button>
      <button class="offer prem" data-act="buy" data-v="premium"><span class="ico">${ic('crown')}</span><span class="grow"><b>Premium</b><br><span class="muted small">Безлимит навсегда</span></span><span class="price">${p.premium_price}${starIc}</span></button>
    </div>`);
}

async function buy(kind) {
  const r = await api('/api/buy', { json: { kind } });
  if (!r.ok) return toast(r.error === 'already_premium' ? 'Premium уже активен' : 'Не удалось создать счёт', 'err');
  if (!tg || !tg.openInvoice) return toast('Оплата доступна только внутри Telegram', 'err');
  tg.openInvoice(r.link, async (status) => {
    if (status !== 'paid') return status === 'failed' ? toast('Оплата не прошла', 'err') : null;
    closeSheet();
    const before = S.me.balance + (S.me.premium ? 1000 : 0);
    for (let i = 0; i < 10; i++) {
      await wait(900);
      const m = await api('/api/me');
      if (m.ok) {
        S.me = m.me;
        if (S.me.balance + (S.me.premium ? 1000 : 0) !== before) break;
      }
    }
    hap('success'); toast('Оплата прошла — спасибо!', 'good'); refresh();
  });
}

/* ---------- листы ---------- */
function openSheet(html) {
  closeSheet();
  const w = document.createElement('div');
  w.className = 'sheet-wrap';
  w.innerHTML = `<div class="sheet" role="dialog" aria-modal="true"><div class="grab"></div>${html}</div>`;
  w.addEventListener('click', (e) => { if (e.target === w) closeSheet(); });
  document.body.appendChild(w);
}
function closeSheet() { document.querySelectorAll('.sheet-wrap').forEach((e) => e.remove()); }

/* ---------- обучение ---------- */
const plural = (n, f) => (n % 10 === 1 && n % 100 !== 11 ? f[0] : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? f[1] : f[2]);

function startFx(canvas, getAcc) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return () => {};
  const ctx = canvas.getContext('2d');
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  let w = 0, h = 0, raf = 0, t0 = performance.now();
  let cur = [167, 139, 250];
  const parts = [];
  const resize = () => { w = canvas.clientWidth; h = canvas.clientHeight; canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
  resize();
  for (let i = 0; i < 54; i++) parts.push({ x: Math.random() * w, y: Math.random() * h, r: 0.6 + Math.random() * 2, v: 0.12 + Math.random() * 0.5, a: 0.25 + Math.random() * 0.6, p: Math.random() * 6.28, s: 0.6 + Math.random() * 1.6 });
  const loop = (t) => {
    raf = requestAnimationFrame(loop);
    const tgt = getAcc();
    cur = cur.map((c, i) => c + (tgt[i] - c) * 0.04);
    ctx.clearRect(0, 0, w, h);
    const col = cur.map(Math.round).join(',');
    const s = (t - t0) / 1000;
    for (const p of parts) {
      p.y -= p.v; p.x += Math.sin(s * 0.5 + p.p) * 0.15;
      if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
      const a = p.a * (0.5 + 0.5 * Math.sin(s * p.s + p.p));
      ctx.fillStyle = `rgba(${col},${a * 0.25})`; ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 3.2, 0, 6.28); ctx.fill();
      ctx.fillStyle = `rgba(${col},${a})`; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.28); ctx.fill();
    }
  };
  raf = requestAnimationFrame(loop);
  window.addEventListener('resize', resize);
  return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
}

function showOnboarding(first) {
  const p = S.me.prices;
  const n = Math.max(1, Math.min(9, p.free_gens || 5));
  const words = (s) => { let i = 0; return s.split('|').map((l) => l.trim().split(' ').map((w) => `<span style="--i:${i++}">${w}</span>`).join(' ')).join('<br>'); };
  const SCENE = `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
    <symbol id="scene" viewBox="0 0 216 128"><rect width="216" height="128" fill="#05050a"/><image href="/static/demo_story.jpg" width="216" height="128" preserveAspectRatio="xMidYMid slice"/></symbol></defs></svg>`;
  const use = (vb) => `<svg viewBox="${vb}" preserveAspectRatio="xMidYMid slice"><use href="#scene" width="216" height="128"/></svg>`;
  const fr = (id, cls = '') => `<img src="/demo/${id}.webp?v=2" alt="" ${cls}>`;
  const main = ['neon', 'mc_grass', 'sakura', 'fire', 'gold', 'galaxy'];
  const thumbs = ['cyber', 'hearts', 'snow', 'mc_end', 'king', 'retro'];
  const xy = (k, r) => `--x:${(Math.sin((k * Math.PI) / 3) * r).toFixed(1)}px;--y:${(-Math.cos((k * Math.PI) / 3) * r).toFixed(1)}px`;

  const slides = [
    { acc: '167,139,250', h: 'Добро пожаловать|в HeliysStudio', t: 'Сториз и рамки для аватарки — за пару касаний. Покажем, как тут всё устроено.',
      art: `<div class="p-halo"></div><div class="p-halo"></div><div class="orbit-line"></div>
        <div class="orbit"><span class="orb" style="--x:0px;--y:-118px;--c:#8b5cf6"><i>${ic('scissors')}</i></span><span class="orb" style="--x:102px;--y:59px;--c:#f0529c"><i>${ic('image')}</i></span><span class="orb" style="--x:-102px;--y:59px;--c:#22d3ee"><i>${ic('star', 'fill')}</i></span></div>
        <div class="hero-ring">${logo()}</div>` },
    { acc: '255,122,168', h: 'Нарезай фото|на сториз', t: 'Загрузи фото, выбери число частей — получишь готовые кадры 1080×1920 в нужном порядке.',
      art: `${SCENE}<div class="sc"><div class="sc-photo">${use('0 0 216 128')}</div>
        <div class="sc-cut" style="left:72px"></div><div class="sc-cut" style="left:144px"></div>
        <div class="sc-scis">${ic('scissors')}</div>
        <div class="sc-tiles">${[0, 1, 2].map((i) => `<div class="sc-tile">${use(`${i * 72} 0 72 128`)}${i === 0 ? '<div class="sc-prog"><i></i><i></i><i></i></div>' : ''}<b>${i + 1}</b></div>`).join('')}</div></div>` },
    { acc: '192,132,252', h: 'Рамки под цвет|твоей аватарки', t: 'Бот сам подберёт палитру из фото. Minecraft, сакура, неон, огонь и ещё 30+ стилей.',
      art: `<div class="fr-orbit">${thumbs.map((id, k) => `<span style="${xy(k, 128)}">${fr(id)}</span>`).join('')}</div>
        <div class="fr-main">${main.map((id, k) => `<img src="/demo/${id}.webp?v=2" alt="" style="--k:${k}">`).join('')}</div>
        <div class="fr-chips" style="position:absolute;bottom:-34px">${['37 стилей', 'Minecraft', 'Сакура', 'Неон'].map((c, i) => `<span class="chip gold" style="--i:${i}">${c}</span>`).join('')}</div>` },
    { acc: '76,201,240', h: 'Как пользоваться', t: 'Три простых шага — и всё готово за пару секунд.', wide: true,
      art: `<div class="steps">${[['upload', 'Загрузи фото', 'Из галереи, аватарка Telegram или просто пришли боту'], ['image', 'Выбери стиль', 'Число частей для сториз или рамку из 37'], ['send', 'Получи в чат', 'Готовые файлы придут от бота — сохраняй и публикуй']]
        .map(([i, a, b], k) => `<div class="step" style="--i:${k}"><span class="n">${ic(i)}</span><span><b>${a}</b><small>${b}</small></span><span class="ck">${ic('check')}</span></div>`).join('')}</div>` },
    { acc: '61,220,151', h: `${n} ${plural(n, ['бесплатная', 'бесплатные', 'бесплатных'])}|${plural(n, ['генерация', 'генерации', 'генераций'])}`, t: `Дальше — ${p.pack_size} генераций за ${p.pack_price} ⭐. Покупка проходит только здесь, в приложении.`, wide: true,
      art: `<div class="g-ring" style="--n:${n}"><svg viewBox="0 0 200 200"><circle class="tr" cx="100" cy="100" r="80"/><circle class="pr" cx="100" cy="100" r="80"/></svg>
        <div class="g-digits"><div class="g-col" style="--n:${n}">${Array.from({ length: n + 1 }, (_, i) => `<span>${n - i}</span>`).join('')}</div></div><span class="cap">осталось</span></div>
        <div class="g-price">${ic('zap')}<b>${p.pack_size} генераций</b><span class="price">${p.pack_price}${starIc}</span></div>` },
    { acc: '245,196,81', h: 'Premium|без лимитов', t: `Один раз ${p.premium_price} ⭐ — и рамки с нарезкой сториз безлимитны навсегда.`,
      art: `<div class="p-rays"></div><div class="p-halo"></div><div class="p-halo"></div>
        <div class="p-crown">${ic('crown', 'fill')}</div>
        ${[[-70, -40], [72, -52], [-86, 10], [84, 6], [-40, -78], [34, -84]].map(([x, y], i) => `<span class="p-spark" style="left:calc(50% + ${x}px);top:calc(50% + ${y}px);--i:${i}">${ic('star', 'fill')}</span>`).join('')}
        <div class="p-perks">${['Безлимит рамок', 'Безлимит сториз', 'Навсегда'].map((c, i) => `<span class="chip gold" style="--i:${i}">${c}</span>`).join('')}</div>` },
  ];

  const DUR = 7000;
  let idx = 0, timer = null;
  const el = document.createElement('div');
  el.className = 'onb';
  el.innerHTML = `<canvas class="onb-fx"></canvas>
    <div class="onb-top"><div class="onb-bars">${slides.map(() => '<i></i>').join('')}</div><button class="onb-skip" data-act="onb-skip">Пропустить</button></div>
    <div class="slides">${slides.map((s) => `<div class="slide" style="--acc:${s.acc};--acc-c:rgb(${s.acc})"><div class="art${s.wide ? ' wide' : ''}">${s.art}</div><h2>${words(s.h)}</h2><p>${s.t}</p></div>`).join('')}</div>
    <div class="onb-bottom"><button class="btn primary block" data-act="onb-next" id="onb-next">Далее</button></div>`;
  document.body.appendChild(el);
  const els = [...el.querySelectorAll('.slide')], bars = [...el.querySelectorAll('.onb-bars i')];
  const stopFx = startFx($('.onb-fx', el), () => slides[idx].acc.split(',').map(Number));
  const show = (i) => {
    clearTimeout(timer);
    idx = Math.max(0, Math.min(slides.length - 1, i));
    els.forEach((s, k) => { s.classList.remove('cur', 'prev'); if (k < idx) s.classList.add('prev'); });
    void el.offsetWidth;
    els[idx].classList.add('cur');
    bars.forEach((b, k) => { b.classList.remove('cur', 'done'); void b.offsetWidth; if (k < idx) b.classList.add('done'); if (k === idx) { b.style.setProperty('--dur', DUR + 'ms'); b.classList.add('cur'); } });
    $('#onb-next').textContent = idx === slides.length - 1 ? 'Начать' : 'Далее';
    hap('light');
    if (idx < slides.length - 1) timer = setTimeout(() => show(idx + 1), DUR);
    else bars[idx].classList.replace('cur', 'done');
  };
  const finish = () => {
    clearTimeout(timer); stopFx(); el.remove();
    if (first) { S.me.tutorial_seen = true; api('/api/tutorial/seen', { method: 'POST', json: {} }); }
  };
  el._next = () => (idx === slides.length - 1 ? finish() : show(idx + 1));
  el._skip = finish;
  el._show = show;
  let x0 = null;
  el.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  el.addEventListener('touchend', (e) => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (dx < -50) el._next(); else if (dx > 50) show(idx - 1); });
  show(0);
}

/* ---------- админ-панель ---------- */
const ADMIN_TILES = [
  ['stats', 'chart', 'Статистика'], ['users', 'users', 'Пользователи'], ['greeting', 'message', 'Приветствие'], ['subs', 'link', 'Подписка'],
  ['bans', 'ban', 'Баны'], ['balance', 'wallet', 'Баланс и Premium'], ['broadcast', 'megaphone', 'Рассылка'], ['prices', 'sliders', 'Цены и лимиты'],
];
const backBtn = (t) => `<button class="back" data-act="admin-back">${ic('back')}Админ-панель</button><div class="h1" style="margin-bottom:14px">${t}</div>`;
const ERR = {
  not_found: 'Пользователь не найден (он ещё не запускал бота)', bad_id: 'Введите числовой ID', cant_ban_admin: 'Нельзя банить админа', bad_text: 'Текст пустой или слишком длинный',
  start_bot: 'Сначала нажми /start в чате с ботом', chat_not_found: 'Канал не найден. Проверьте @username или ID', bot_not_admin: 'Сделайте бота администратором канала',
  need_link: 'Для приватного канала укажите ссылку-приглашение', running: 'Рассылка уже идёт', bad_value: 'Некорректное значение', network: 'Нет соединения',
};
const aerr = (r) => toast(ERR[r.error] || 'Ошибка', 'err');

function renderAdmin(anim) {
  const v = S.admin.view;
  if (!v) {
    mount(`<div class="topbar"><div class="hello"><small>Управление</small><div class="h1">Дашборд</div></div><span class="chip gold">${ic('shield')}Admin</span></div>
      <div class="dash" id="dash">${['w2', '', ''].map((c) => `<div class="kpi skel ${c}"></div>`).join('')}</div>
      <div class="tiles">${ADMIN_TILES.map(([id, i, l]) => `<button class="tile" data-act="admin-open" data-v="${id}"><span class="ico">${ic(i)}</span><b>${l}</b></button>`).join('')}</div>`, anim);
    api('/api/admin/stats').then((r) => {
      const el = $('#dash');
      if (!r.ok || !el || S.admin.view) return;
      const s = r.stats, k = (c, i, l, v, d) => `<div class="kpi ${c}"><small>${ic(i)}${l}</small><b>${v}</b>${d ? `<em>${d}</em>` : ''}</div>`;
      el.innerHTML = k('w2', 'users', 'Пользователи', s.users, `+${s.new_24h} за 24ч · ${s.active_24h} активны`) + k('', 'zap', 'Генераций', s.gens, `+${s.gens_24h} за 24ч`) + k('', 'star', 'Получено ⭐', s.stars, `+${s.stars_24h} за 24ч`);
    });
    return;
  }
  PAGES[v](anim);
}

const userCard = (u) => `<div class="card" data-user="${u.id}">
  <div class="row"><div class="mini-ava">${esc((u.name || u.username || '?').slice(0, 1).toUpperCase())}</div>
    <div class="grow"><b>${esc(u.name || 'Без имени')}</b><div class="muted small">${u.username ? '@' + esc(u.username) : 'нет username'} · <span class="mono">${u.id}</span></div></div>
    ${u.banned ? '<span class="chip red">бан</span>' : ''}${u.premium ? `<span class="chip prem">${ic('crown')}</span>` : ''}</div>
  <div class="kv"><span>Запустил бота</span><b>${fmtShort(u.joined_at)}</b></div>
  <div class="kv"><span>Бесплатных / куплено</span><b class="mono">${u.free_left} / ${u.balance}</b></div>
  <div class="kv"><span>Генераций / потрачено ⭐</span><b class="mono">${u.gens_total} / ${u.stars_spent}</b></div></div>`;

const PAGES = {
  async stats(anim) {
    mount(backBtn('Статистика') + '<div class="stats">' + Array(6).fill('<div class="skel" style="height:86px"></div>').join('') + '</div>', anim);
    const r = await api('/api/admin/stats');
    if (!r.ok || S.admin.view !== 'stats') return;
    const s = r.stats;
    const card = (v, l, d) => `<div class="stat"><b>${v}</b><span>${l}</span>${d ? `<br><em>${d}</em>` : ''}</div>`;
    mount(backBtn('Статистика') + `<div class="stats">
      ${card(s.users, 'Пользователей', `+${s.new_24h} за 24ч`)}${card(s.active_24h, 'Активны за 24ч')}
      ${card(s.gens, 'Генераций', `+${s.gens_24h} за 24ч`)}${card(s.stars, 'Получено ⭐', `+${s.stars_24h} за 24ч`)}
      ${card(s.premium, 'Premium')}${card(s.banned, 'В бане')}
      ${card(s.gens_slice, 'Нарезок сториз')}${card(s.gens_frame, 'Рамок')}</div>`);
  },

  async users() {
    const st = (S.admin.users = S.admin.users || { q: '', offset: 0, list: [], total: 0 });
    const draw = () => mount(backBtn('Пользователи') + `<div class="row" style="margin-bottom:12px"><input class="input" id="uq" placeholder="Поиск: ID, @username, имя" value="${esc(st.q)}" inputmode="search" autocomplete="off"></div>
      <div class="muted small" style="margin-bottom:8px">Всего: <span class="mono">${st.total}</span> · сначала новые</div>
      <div id="ulist">${st.list.map((u) => `<button class="urow" data-act="user-open" data-v="${u.id}"><span class="mini-ava">${esc((u.name || u.username || '?').slice(0, 1).toUpperCase())}</span>
        <span class="grow"><b>${esc(u.name || 'Без имени')}</b>${u.premium ? ` <span class="chip prem" style="padding:1px 8px">${ic('crown')}</span>` : ''}${u.banned ? ' <span class="chip red" style="padding:1px 8px">бан</span>' : ''}<br><span class="muted small">${u.username ? '@' + esc(u.username) + ' · ' : ''}<span class="mono">${u.id}</span> · ${fmtShort(u.joined_at)}</span></span></button>`).join('') || '<div class="muted center" style="padding:30px">Никого не найдено</div>'}</div>
      ${st.list.length < st.total ? '<button class="btn ghost block" style="margin-top:12px" data-act="users-more">Показать ещё</button>' : ''}`);
    const load = async (reset) => {
      if (reset) { st.offset = 0; st.list = []; }
      const r = await api(`/api/admin/users?q=${encodeURIComponent(st.q)}&offset=${st.offset}&limit=20`);
      if (!r.ok || S.admin.view !== 'users') return;
      st.list = st.list.concat(r.users); st.total = r.total; st.offset = st.list.length;
      draw(); bindSearch();
    };
    const bindSearch = () => {
      const inp = $('#uq'); if (!inp) return;
      let t; inp.oninput = () => { clearTimeout(t); t = setTimeout(() => { st.q = inp.value; load(true).then(() => { const i = $('#uq'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }); }, 380); };
    };
    S.admin.loadUsers = () => load(false);
    draw(); bindSearch(); load(true);
  },

  async greeting() {
    mount(backBtn('Приветствие') + '<div class="skel" style="height:220px"></div>');
    const r = await api('/api/admin/greeting');
    if (!r.ok || S.admin.view !== 'greeting') return;
    mount(backBtn('Приветствие в боте') + `<div class="muted small" style="margin-bottom:8px">HTML: &lt;b&gt;, &lt;i&gt;, &lt;a href&gt;, &lt;tg-emoji emoji-id="…"&gt;🙂&lt;/tg-emoji&gt;. <span class="mono">{name}</span> — имя пользователя.</div>
      <textarea class="input" id="gt" spellcheck="false">${esc(r.html)}</textarea>
      <div class="field-label">Предпросмотр</div><div class="tgprev" id="gp"></div>
      <div class="gap"></div>
      <button class="btn primary block" data-act="greeting-save">${ic('check')}Сохранить</button>
      <button class="btn ghost block" style="margin-top:10px" data-act="await-bot" data-v="greeting">${ic('crown')}Прислать боту — с премиум-эмодзи</button>
      <div class="muted small" style="margin-top:10px">Премиум-эмодзи нельзя вставить из этого окна — нажми кнопку, бот попросит прислать сообщение, и сохранит его вместе с эмодзи. Узнать ID эмодзи можно командой /emojiid.</div>`);
    const t = $('#gt'), pv = $('#gp'), up = () => (pv.innerHTML = renderTgHtml(t.value));
    t.oninput = up; up();
  },

  async subs() {
    mount(backBtn('Обязательная подписка') + '<div class="skel" style="height:120px"></div>');
    const r = await api('/api/admin/channels');
    if (!r.ok || S.admin.view !== 'subs') return;
    mount(backBtn('Обязательная подписка') + `<div class="muted small" style="margin-bottom:12px">Пользователь не сможет пользоваться ботом и Mini App, пока не подпишется. Бот должен быть <b>администратором</b> канала.</div>
      ${r.channels.map((c) => `<div class="urow" style="cursor:default"><span class="mini-ava">${ic('link')}</span><span class="grow"><b>${esc(c.title)}</b><br><span class="muted small mono">${esc(c.chat_ref)}</span></span><button class="btn danger sm" data-act="sub-del" data-v="${c.id}" aria-label="Удалить">${ic('trash')}</button></div>`).join('') || '<div class="muted center" style="padding:20px">Каналов пока нет</div>'}
      <div class="field-label">Добавить канал</div>
      <div class="stack"><input class="input" id="s-ref" placeholder="@username или -100… (ID)" autocomplete="off">
      <input class="input" id="s-title" placeholder="Название кнопки (необязательно)">
      <input class="input" id="s-link" placeholder="Ссылка-приглашение (для приватного канала)">
      <button class="btn primary block" data-act="sub-add">${ic('plus')}Добавить</button></div>`);
  },

  async bans() {
    const r = await api('/api/admin/users?banned=1&limit=50');
    if (!r.ok || S.admin.view !== 'bans') return;
    mount(backBtn('Баны') + `<div class="stack"><input class="input" id="b-id" placeholder="Telegram ID пользователя" inputmode="numeric" autocomplete="off">
      <div class="row"><button class="btn danger block" data-act="ban" data-v="1">${ic('ban')}Забанить</button><button class="btn ok block" data-act="ban" data-v="0">${ic('check')}Разбанить</button></div></div>
      <div class="field-label">В бане (${r.total})</div>
      ${r.users.map((u) => `<div class="urow" style="cursor:default"><span class="mini-ava">${esc((u.name || '?').slice(0, 1).toUpperCase())}</span><span class="grow"><b>${esc(u.name || 'Без имени')}</b><br><span class="muted small mono">${u.id}</span></span><button class="btn ok sm" data-act="ban-quick" data-v="${u.id}">Разбанить</button></div>`).join('') || '<div class="muted center" style="padding:20px">Список пуст</div>'}`);
  },

  async balance() {
    mount(backBtn('Баланс и Premium') + `<div class="muted small" style="margin-bottom:10px">Баланс — купленные генерации (бесплатные 5 не затрагиваются).</div>
      <div class="stack"><input class="input" id="l-id" placeholder="Telegram ID пользователя" inputmode="numeric" autocomplete="off">
      <input class="input" id="l-n" placeholder="Количество генераций" inputmode="numeric" autocomplete="off">
      <div class="row"><button class="btn ok block" data-act="bal" data-v="1">${ic('plus')}Выдать</button><button class="btn danger block" data-act="bal" data-v="-1">${ic('minus')}Забрать</button></div>
      <div class="row"><button class="btn ghost block" data-act="prem" data-v="1">${ic('crown')}Выдать Premium</button><button class="btn ghost block" data-act="prem" data-v="0">Снять Premium</button></div></div>
      <div id="l-res" style="margin-top:14px"></div>`);
  },

  async broadcast() {
    const r = await api('/api/admin/stats');
    const b = r.ok ? r.broadcast : {};
    mount(backBtn('Рассылка') + `<div class="muted small" style="margin-bottom:8px">Отправится всем, кроме забаненных. Поддерживается HTML.</div>
      <textarea class="input" id="bt" placeholder="Текст рассылки…" spellcheck="false"></textarea>
      <div class="field-label">Предпросмотр</div><div class="tgprev" id="bp" style="min-height:46px"></div>
      <div class="gap"></div>
      <button class="btn primary block" data-act="bc-send" ${b.running ? 'disabled' : ''}>${ic('megaphone')}Отправить всем</button>
      <button class="btn ghost block" style="margin-top:10px" data-act="await-bot" data-v="broadcast">${ic('crown')}Прислать боту — с премиум-эмодзи</button>
      <div id="bc-stat" style="margin-top:14px"></div>`);
    const t = $('#bt'); t.oninput = () => ($('#bp').innerHTML = renderTgHtml(t.value));
    if (b.running || b.total) pollBroadcast();
  },

  async prices() {
    mount(backBtn('Цены и лимиты') + '<div class="skel" style="height:260px"></div>');
    const r = await api('/api/admin/settings');
    if (!r.ok || S.admin.view !== 'prices') return;
    const s = r.settings;
    const f = (k, l, h) => `<div><div class="field-label" style="margin-top:0">${l}</div><input class="input mono" id="p-${k}" value="${s[k]}" inputmode="numeric"><div class="muted small" style="margin-top:4px">${h}</div></div>`;
    mount(backBtn('Цены и лимиты') + `<div class="stack">${f('free_gens', 'Бесплатных генераций новичку', 'Только для новых пользователей')}${f('pack_size', 'Генераций в пакете', '')}${f('pack_price', 'Цена пакета, ⭐', '')}${f('premium_price', 'Цена Premium, ⭐', 'Покупается один раз, навсегда')}
      <button class="btn primary block" data-act="prices-save">${ic('check')}Сохранить</button></div>`);
  },
};

async function pollBroadcast() {
  for (let i = 0; i < 600 && S.admin.view === 'broadcast'; i++) {
    const r = await api('/api/admin/stats');
    const el = $('#bc-stat');
    if (!r.ok || !el) return;
    const b = r.broadcast, done = b.sent + b.failed, pct = b.total ? Math.round((done / b.total) * 100) : 0;
    el.innerHTML = `<div class="card"><div class="row between"><b>${b.running ? 'Рассылка идёт…' : 'Последняя рассылка'}</b><span class="mono">${done}/${b.total}</span></div><div class="bar" style="margin:10px 0"><i style="--p:${pct / 100}"></i></div><div class="muted small">Доставлено ${b.sent} · ошибок ${b.failed}</div></div>`;
    if (!b.running) return;
    await wait(1500);
  }
}

async function openUser(id) {
  const r = await api('/api/admin/user?id=' + id);
  if (!r.ok) return aerr(r);
  const u = r.user;
  openSheet(`${userCard(u)}<div class="gap"></div>
    <div class="row"><button class="btn ok block" data-act="uact" data-id="${u.id}" data-k="bal" data-v="10">+10</button><button class="btn ok block" data-act="uact" data-id="${u.id}" data-k="bal" data-v="1">+1</button>
      <button class="btn danger block" data-act="uact" data-id="${u.id}" data-k="bal" data-v="-1">−1</button><button class="btn danger block" data-act="uact" data-id="${u.id}" data-k="bal" data-v="-10">−10</button></div>
    <div class="row" style="margin-top:10px"><button class="btn ghost block" data-act="uact" data-id="${u.id}" data-k="prem" data-v="${u.premium ? 0 : 1}">${ic('crown')}${u.premium ? 'Снять Premium' : 'Выдать Premium'}</button>
      <button class="btn ${u.banned ? 'ok' : 'danger'} block" data-act="uact" data-id="${u.id}" data-k="ban" data-v="${u.banned ? 0 : 1}">${ic('ban')}${u.banned ? 'Разбанить' : 'Забанить'}</button></div>`);
}

/* ---------- действия ---------- */
const val = (id) => ($('#' + id) ? $('#' + id).value.trim() : '');
async function userAction(kind, id, v) {
  let r;
  if (kind === 'bal') r = await api('/api/admin/balance', { json: { id, delta: v } });
  else if (kind === 'prem') r = await api('/api/admin/premium', { json: { id, on: !!v } });
  else r = await api('/api/admin/ban', { json: { id, banned: !!v } });
  return r;
}
const showRes = (u) => { const el = $('#l-res'); if (el) el.innerHTML = userCard(u); };

const ACTIONS = {
  reload: () => location.reload(),
  goto: (el) => { hap('light'); S.admin.view = null; go(el.dataset.v); },
  tool: (el) => { S.tool = el.dataset.v; hap('light'); refresh(); },
  'close-sheet': () => closeSheet(),
  'close-app': () => { closeSheet(); tg && tg.close(); },
  'open-link': (el) => { const u = el.dataset.v; tg && tg.openTelegramLink && u.startsWith('https://t.me/') ? tg.openTelegramLink(u) : window.open(u, '_blank'); },
  async recheck(el) {
    el.disabled = true;
    const r = await api('/api/check_sub');
    if (r.ok && !r.missing.length) { const m = await api('/api/me'); S.me = m.me; S.missing = []; startApp(); }
    else { el.disabled = false; S.missing = (r.missing || S.missing); toast('Подписка не найдена — подпишись и повтори', 'err'); showGate(); }
  },
  copy: (el) => copyText(el.dataset.v),
  paywall: () => paywall(),
  async buy(el) { el.disabled = true; await buy(el.dataset.v); el.disabled = false; },
  tutorial: () => showOnboarding(false),
  'onb-next': () => $('.onb')._next(),
  'onb-skip': () => $('.onb')._skip(),

  /* сториз */
  async 'slice-pick'() {
    const f = await pickFile(); if (!f) return;
    Object.assign(S.slice, { src: f, url: URL.createObjectURL(f) }); hap('light'); refresh();
  },
  async 'slice-pending'() {
    try { Object.assign(S.slice, { src: 'pending', url: await fetchBlobUrl('/api/pending') }); hap('light'); refresh(); }
    catch (_) { toast('Фото из чата не найдено', 'err'); }
  },
  'slice-reset': () => { Object.assign(S.slice, { src: null, url: '' }); refresh(); },
  parts: (el) => { S.slice.parts = +el.dataset.v; hap('light'); refresh(); },
  mode: (el) => { S.slice.mode = el.dataset.v; hap('light'); refresh(); },
  asfile: () => { S.slice.asFile = !S.slice.asFile; hap('light'); refresh(); },
  async 'do-slice'() {
    const s = S.slice;
    if (!canGen()) return paywall();
    s.busy = true; refresh();
    const fd = new FormData();
    fd.append('parts', s.parts); fd.append('mode', s.mode); fd.append('as_file', s.asFile ? '1' : '0');
    if (s.src === 'pending') fd.append('source', 'pending'); else fd.append('file', await shrink(s.src, 6500, 12e6), 'photo.jpg');
    const r = await api('/api/slice', { form: fd });
    s.busy = false; refresh(); afterGen(r, 'slice');
  },

  /* рамки */
  async 'frame-file'() { const f = await pickFile(); if (f) frameLoad('file', f); },
  'frame-avatar': () => frameLoad('avatar'),
  'frame-pending': () => frameLoad('pending'),
  'frame-reset': () => { Object.assign(S.frame, { has: false, previews: [], palettes: [] }); refresh(); },
  style: (el) => { S.frame.style = el.dataset.v; hap('light'); refresh(); loadHQ(); },
  cat: (el) => { S.frame.cat = el.dataset.v; hap('light'); refresh(); },
  async palette(el) {
    const f = S.frame; f.palette = +el.dataset.v; f.refreshing = true; hap('light'); refresh();
    const r = await api('/api/frames/previews', { json: { palette: f.palette } });
    f.refreshing = false;
    if (r.ok) f.previews = f.previews.map((p) => { const n = r.previews.find((x) => x.id === p.id); return n && n.img ? { ...p, img: n.img } : p; });
    else toast('Фото устарело — загрузи заново', 'err');
    refresh(); loadHQ();
  },
  async 'do-frame'() {
    const f = S.frame;
    if (!canGen()) return paywall();
    f.busy = true; refresh();
    const r = await api('/api/frames/render', { json: { style: f.style, palette: f.palette } });
    f.busy = false; refresh(); afterGen(r, 'frame');
  },

  /* админка */
  'admin-open': (el) => { S.admin.view = el.dataset.v; renderAdmin(true); },
  'admin-back': () => { S.admin.view = null; renderAdmin(true); },
  'user-open': (el) => openUser(+el.dataset.v),
  'users-more': () => S.admin.loadUsers(),
  async uact(el) {
    const r = await userAction(el.dataset.k, +el.dataset.id, +el.dataset.v);
    if (!r.ok) return aerr(r);
    hap('success'); toast('Готово', 'good'); openUser(+el.dataset.id);
    if (S.admin.view === 'users' && S.admin.users) { const i = S.admin.users.list.findIndex((u) => u.id === r.user.id); if (i >= 0) S.admin.users.list[i] = r.user; }
  },
  async 'greeting-save'() { const r = await api('/api/admin/greeting', { json: { html: $('#gt').value } }); r.ok ? (hap('success'), toast('Приветствие сохранено', 'good')) : aerr(r); },
  async 'await-bot'(el) {
    const r = await api('/api/admin/await', { json: { kind: el.dataset.v } });
    if (!r.ok) return aerr(r);
    toast('Открой чат с ботом и пришли сообщение', 'good'); setTimeout(() => tg && tg.close(), 900);
  },
  async 'sub-add'() {
    const r = await api('/api/admin/channels', { json: { ref: val('s-ref'), title: val('s-title'), link: val('s-link') } });
    r.ok ? (hap('success'), toast('Канал добавлен', 'good'), PAGES.subs()) : aerr(r);
  },
  async 'sub-del'(el) { const r = await api('/api/admin/channels/delete', { json: { id: +el.dataset.v } }); r.ok ? PAGES.subs() : aerr(r); },
  async ban(el) {
    const id = parseInt(val('b-id'), 10); if (!id) return toast('Введите ID', 'err');
    const r = await userAction('ban', id, +el.dataset.v);
    r.ok ? (hap('success'), toast(+el.dataset.v ? 'Забанен' : 'Разбанен', 'good'), PAGES.bans()) : aerr(r);
  },
  async 'ban-quick'(el) { const r = await userAction('ban', +el.dataset.v, 0); r.ok ? PAGES.bans() : aerr(r); },
  async bal(el) {
    const id = parseInt(val('l-id'), 10), n = parseInt(val('l-n'), 10);
    if (!id || !n || n < 1) return toast('Введите ID и количество', 'err');
    const r = await userAction('bal', id, n * +el.dataset.v);
    r.ok ? (hap('success'), toast(+el.dataset.v > 0 ? 'Баланс выдан' : 'Баланс списан', 'good'), showRes(r.user)) : aerr(r);
  },
  async prem(el) {
    const id = parseInt(val('l-id'), 10); if (!id) return toast('Введите ID', 'err');
    const r = await userAction('prem', id, +el.dataset.v);
    r.ok ? (hap('success'), toast('Готово', 'good'), showRes(r.user)) : aerr(r);
  },
  async 'bc-send'() {
    const html = $('#bt').value.trim(); if (!html) return toast('Введите текст', 'err');
    const go_ = async () => { const r = await api('/api/admin/broadcast', { json: { html } }); r.ok ? (toast('Рассылка запущена', 'good'), pollBroadcast()) : aerr(r); };
    tg && tg.showConfirm ? tg.showConfirm('Отправить рассылку всем пользователям?', (ok) => ok && go_()) : go_();
  },
  async 'prices-save'() {
    const body = {}; ['free_gens', 'pack_size', 'pack_price', 'premium_price'].forEach((k) => (body[k] = parseInt(val('p-' + k), 10)));
    const r = await api('/api/admin/settings', { json: body });
    if (!r.ok) return aerr(r);
    hap('success'); toast('Сохранено', 'good');
    const m = await api('/api/me'); if (m.ok) S.me = m.me;
  },
};

document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-act]');
  if (el && ACTIONS[el.dataset.act]) ACTIONS[el.dataset.act](el, e);
});

boot();
