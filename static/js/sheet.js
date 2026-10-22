/* หน้าต่างรายการ: เปิด/ปิด ค้นหา กรองตามประเภทและอายุ เลือก และปุ่มเปิดใน Finder */

import { $, esc, fmt, shortPath } from "./dom.js";
import { revealInFinder } from "./api.js";
import { state } from "./state.js";
import { exportCsv } from "./export.js";
import { kindLabel } from "./labels.js";
import { t, onLangChange } from "./i18n.js";

const selected = new Set();                // การเลือกคงอยู่แม้เปลี่ยนตัวกรอง
let filter = { kind: null, old: false };   // ตัวกรองที่ใช้อยู่ตอนนี้

/* title, sub และ action ของหน้าต่างเป็นสตริงหรือฟังก์ชัน (ฟังก์ชันถูกเรียกใหม่เมื่อเปลี่ยนภาษา) */
const text = (v) => (typeof v === "function" ? v() : v);

function renderSheetHeader() {
  const cfg = state.sheet;
  $("sheet-title").textContent = text(cfg.title);
  $("sheet-sub").textContent = text(cfg.sub) || "";
  $("sheet-action").textContent = text(cfg.action) || "";
}

export function openSheet(cfg) {
  state.sheet = cfg;
  selected.clear();
  filter = { kind: null, old: false };
  renderSheetHeader();
  $("sheet-text").hidden = cfg.mode !== "text";
  $("sheet-list").hidden = cfg.mode !== "list";
  $("sheet-toolbar").hidden = cfg.mode !== "list";
  $("sheet-chips").hidden = cfg.mode !== "list";
  $("sheet-action").hidden = !cfg.action;
  $("sheet-action").disabled = false;      // โหมดรายการจะปิดเองใน updateSheetSum จนกว่าจะเลือกรายการ
  $("sheet-search").value = "";
  $("overlay").hidden = false;
  if (cfg.mode === "list") renderList();
  if (cfg.mode === "text") cfg.load();
}

export function closeSheet() {
  $("overlay").hidden = true;
  state.sheet = null;
}

/* รายการที่เลือกไว้และยังอยู่ในรายการ (รายการที่ถูกย้ายไปแล้วจะหลุดออกเอง) */
export function selectedPaths() {
  const live = new Set(state.sheet.items().map(x => x.path));
  return [...selected].filter(p => live.has(p));
}

function isOld(x) {
  if (x.last_access == null) return false;
  return Date.now() / 1000 - x.last_access > state.settings.old_months * 30.44 * 86400;
}

function visibleItems() {
  const q = $("sheet-search").value.trim().toLowerCase();
  return state.sheet.items().filter(x =>
    (!q || x.path.toLowerCase().includes(q)) &&
    (!filter.kind || x.kind === filter.kind) &&
    (!filter.old || isOld(x)));
}

function renderChips() {
  const items = state.sheet.items();
  const kinds = [...new Set(items.map(x => x.kind))].sort((a, b) => kindLabel(a) < kindLabel(b) ? -1 : 1);
  const chips = [`<button class="chip${filter.kind ? "" : " on"}" data-kind="">${esc(t("chips.all", { n: items.length }))}</button>`];
  for (const k of kinds) {
    const n = items.filter(x => x.kind === k).length;
    chips.push(`<button class="chip${filter.kind === k ? " on" : ""}" data-kind="${esc(k)}">${esc(kindLabel(k))} ${n}</button>`);
  }
  if (items.some(x => x.last_access != null)) {
    chips.push(`<button class="chip${filter.old ? " on" : ""}" data-old="1">${esc(t("chips.old", { n: state.settings.old_months }))}</button>`);
  }
  $("sheet-chips").innerHTML = chips.join("");
}

export function renderList() {
  const rows = visibleItems();
  $("sheet-list").innerHTML = rows.length ? rows.map(x => `
    <div class="item">
      <label class="pick">
        <input type="checkbox" data-path="${esc(x.path)}" ${x.keep ? "disabled" : ""} ${selected.has(x.path) ? "checked" : ""}>
        <span class="sz">${fmt(x.size)}</span>
        <span class="name">${esc(shortPath(x.path).split("/").pop())}${x.keep ? ` <span class="badge">${esc(t("sheet.keep"))}</span>` : ""}<small>${esc(shortPath(x.path))}</small></span>
      </label>
      <button class="btn quiet reveal" data-path="${esc(x.path)}" title="${esc(t("sheet.reveal_title"))}">${esc(t("common.finder_open"))}</button>
    </div>`).join("") : `<div class="empty">${esc(t("sheet.empty"))}</div>`;
  renderChips();
  updateSheetSum();
}

export function updateSheetSum() {
  const picked = selectedPaths();
  const size = state.sheet.items().filter(x => picked.includes(x.path)).reduce((a, x) => a + x.size, 0);
  $("sheet-sum").textContent = picked.length
    ? t("sheet.selected", { n: picked.length, size: fmt(size) })
    : t("sheet.count", { n: state.sheet.items().length });
  $("sheet-action").disabled = picked.length === 0;
}

/* ผูกอีเวนต์ของหน้าต่างครั้งเดียวตอนเริ่มโปรแกรม */
export function initSheet() {
  $("sheet-close").onclick = closeSheet;
  $("overlay").onclick = (e) => { if (e.target.id === "overlay") closeSheet(); };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.sheet) closeSheet(); });

  $("sheet-list").addEventListener("change", (e) => {
    const box = e.target;
    if (!box.matches("input[type=checkbox]")) return;
    if (box.checked) selected.add(box.dataset.path);
    else selected.delete(box.dataset.path);
    updateSheetSum();
  });
  $("sheet-list").addEventListener("click", (e) => {
    const btn = e.target.closest(".reveal");
    if (btn) revealInFinder(btn.dataset.path);
  });
  $("sheet-chips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    if ("old" in chip.dataset) filter.old = !filter.old;
    else filter.kind = chip.dataset.kind || null;
    renderList();
  });
  $("sheet-search").addEventListener("input", renderList);
  $("sheet-csv").onclick = () => {
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    exportCsv(visibleItems(), `storage-check-${stamp}.csv`);
  };
  $("sheet-all").onclick = () => {
    const boxes = [...document.querySelectorAll("#sheet-list input:not(:disabled)")];
    const allOn = boxes.every(b => b.checked);
    boxes.forEach(b => {
      b.checked = !allOn;
      if (b.checked) selected.add(b.dataset.path);
      else selected.delete(b.dataset.path);
    });
    updateSheetSum();
  };
  $("sheet-action").onclick = async () => {
    if (!state.sheet || !state.sheet.onAction) return;
    await state.sheet.onAction();
  };
  onLangChange(() => {
    if (!state.sheet) return;
    renderSheetHeader();
    if (state.sheet.mode === "list") renderList();
  });
}
