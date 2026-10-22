/* ระบบแปลภาษาของหน้าเว็บ พจนานุกรมอยู่ใน /static/locales/<lang>.json (ฝั่ง Python ใช้ไฟล์เดียวกัน)
   - t(key, vars): ข้อความตามภาษาปัจจุบัน แทนที่ {ชื่อ} ด้วยค่าใน vars (vars.n === 1 ใช้คีย์ "<key>.one" ถ้ามี)
   - applyLang(): เติมข้อความให้ element ที่มี data-i18n, data-i18n-title, data-i18n-placeholder, data-i18n-aria-label
   - onLangChange(fn): ให้โมดูลที่สร้างเนื้อหาด้วย JS วาดใหม่เมื่อเปลี่ยนภาษา */

const LANGS = ["th", "en"];
const DEFAULT_LANG = "th";
const STORAGE_KEY = "storagecheck.lang";

/* ข้อความที่ต้องแสดงได้แม้โหลดพจนานุกรมไม่ได้ (เช่น เปิดหน้าโดยไม่ผ่าน gui.py) */
const BUILTIN = {
  th: {
    "err.connect": "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
    "err.not_json": "ได้รับคำตอบที่ไม่ใช่ JSON (สถานะ {status})",
    "err.hint": "ต้องเปิดผ่าน gui.py ที่ http://127.0.0.1:8765 (ไม่ใช่ Live Server หรือไฟล์ที่เปิดตรง ๆ)",
    "err.generic": "เกิดข้อผิดพลาด",
  },
  en: {
    "err.connect": "Cannot connect to the server",
    "err.not_json": "Received a non-JSON response (status {status})",
    "err.hint": "Open the page through gui.py at http://127.0.0.1:8765 (not Live Server or a file opened directly)",
    "err.generic": "Something went wrong",
  },
};

const ATTRS = [["title", "i18nTitle"], ["placeholder", "i18nPlaceholder"], ["aria-label", "i18nAriaLabel"]];

const dicts = {};
const listeners = [];
let lang = DEFAULT_LANG;

function storedLang() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return LANGS.includes(v) ? v : null;
  } catch (e) {
    return null;
  }
}

function storeLang(v) {
  try { localStorage.setItem(STORAGE_KEY, v); } catch (e) { /* ใช้ได้ตามปกติแม้จำค่าไม่ได้ */ }
}

async function loadDict(l) {
  try {
    const r = await fetch(`/static/locales/${l}.json`);
    dicts[l] = r.ok ? await r.json() : {};
  } catch (e) {
    dicts[l] = {};
  }
}

/* ภาษาที่เลือก -> ภาษาไทย (ค่าเริ่มต้น) เมื่อไม่มีคีย์ในภาษานั้น */
function lookup(key) {
  for (const l of [lang, DEFAULT_LANG]) {
    const s = dicts[l]?.[key] ?? BUILTIN[l]?.[key];
    if (s != null) return s;
  }
  return null;
}

export function t(key, vars = {}) {
  const useOne = vars.n === 1 && lookup(key + ".one") != null;
  const s = lookup(useOne ? key + ".one" : key);
  if (s == null) {
    console.warn(`i18n: missing key "${key}"`);
    return key;
  }
  return s.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? vars[name] : m));
}

export const getLang = () => lang;

/* locale สำหรับจัดรูปแบบวันที่และตัวเลข */
export const locale = () => (lang === "th" ? "th-TH" : "en-US");

export function applyLang(root = document) {
  document.documentElement.lang = lang;
  root.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  for (const [attr, key] of ATTRS) {
    root.querySelectorAll(`[data-i18n-${attr}]`).forEach(el => el.setAttribute(attr, t(el.dataset[key])));
  }
  document.querySelectorAll(".lang button").forEach(b => {
    b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
  });
}

export function onLangChange(fn) {
  listeners.push(fn);
}

export function setLang(l) {
  if (!LANGS.includes(l) || l === lang) return;
  lang = l;
  storeLang(l);
  applyLang();
  listeners.forEach(fn => fn(l));
}

/* เริ่มต้น: โหลดพจนานุกรมทุกภาษาก่อนให้โมดูลอื่นทำงาน (module นี้รอด้วย top-level await) */
lang = storedLang() ?? DEFAULT_LANG;
await Promise.all(LANGS.map(loadDict));
applyLang();
document.querySelectorAll(".lang button").forEach(b => { b.onclick = () => setLang(b.dataset.lang); });
