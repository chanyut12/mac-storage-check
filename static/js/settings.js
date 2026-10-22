/* ตั้งค่าเกณฑ์ขนาดและอายุ รวมถึงรายการโฟลเดอร์ที่ยกเว้น อยู่ในส่วนตัวเลือกเพิ่มเติม */

import { $, esc } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { t, onLangChange } from "./i18n.js";
import { renderCards } from "./cards.js";
import { alertBox } from "./dialog.js";

export function renderSettings() {
  const s = state.settings;
  $("set-min").value = s.min_mb;
  $("set-dup").value = s.dup_min_mb;
  $("set-old").value = s.old_months;
  $("excluded").innerHTML = s.exclude.length
    ? s.exclude.map(p => `
        <div class="exrow">
          <span class="name">${esc(p)}</span>
          <button class="btn quiet" data-remove="${esc(p)}">${esc(t("settings.remove"))}</button>
        </div>`).join("")
    : `<div class="muted">${esc(t("settings.excluded_empty"))}</div>`;
}

export async function loadSettings() {
  state.settings = await api("/api/settings");
  renderSettings();
}

/* ค่าที่เปลี่ยนจะล้างผลสแกนและผลซ้ำที่ค้างไว้ จึงให้ตรวจใหม่ */
function resetResults(msg) {
  state.dups = null;
  state.folderDups = null;
  renderSettings();
  renderCards();
  $("set-msg").textContent = msg;
}

async function saveSettings() {
  const body = {
    min_mb: +$("set-min").value,
    dup_min_mb: +$("set-dup").value,
    old_months: +$("set-old").value,
  };
  try {
    state.settings = await api("/api/settings", body);
    resetResults(t("settings.saved"));
  } catch (e) {
    $("set-msg").textContent = t("settings.save_failed", { message: e.message });
  }
}

async function updateExclude(body, msg) {
  try {
    state.settings = await api("/api/exclude", body);
    resetResults(msg);
  } catch (e) {
    await alertBox(t("settings.update_failed", { message: e.message }),
                   { title: t("settings.update_failed_title"), tone: "error" });
  }
}

/* ยกเว้นโฟลเดอร์ (path เป็นพาธเต็ม) จากการสแกนครั้งถัดไป */
export function excludeFolder(path) {
  return updateExclude({ path }, t("settings.excluded_ok"));
}

export function initSettings() {
  $("set-save").onclick = saveSettings;
  $("excluded").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-remove]");
    if (!btn) return;
    const entry = btn.dataset.remove;                  // รูปแบบ ~/... ในไฟล์ตั้งค่า
    updateExclude({ path: state.settings.home + entry.slice(1), remove: true },
                  t("settings.removed_ok"));
  });
  onLangChange(renderSettings);
}
