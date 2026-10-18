/* เรียกดูโฟลเดอร์ย่อยใน home ทีละชั้น เปิดใน Finder และยกเว้นได้ (ไม่มีการลบในหน้านี้) */

import { $, esc, fmt, shortPath } from "./dom.js";
import { api, revealInFinder } from "./api.js";
import { state } from "./state.js";
import { openSheet } from "./sheet.js";
import { excludeFolder } from "./settings.js";

function entryRow(x) {
  const nav = x.is_dir ? ` nav" data-browse="${esc(x.path)}` : "";
  const exclude = x.is_dir
    ? `<button class="btn quiet" data-exclude="${esc(x.path)}">ยกเว้น</button>`
    : `<span></span>`;
  return `
    <div class="entry${nav}">
      <span class="sz">${fmt(x.size)}</span>
      <span class="name">${x.is_dir ? "📁" : "📄"} ${esc(x.name)}</span>
      <button class="btn quiet reveal" data-reveal="${esc(x.path)}">เปิดใน Finder</button>
      ${exclude}
    </div>`;
}

async function show(path) {
  const body = $("sheet-text");
  $("sheet-title").textContent = shortPath(path);
  $("sheet-sub").textContent = "กำลังคำนวณขนาด... โฟลเดอร์ใหญ่อาจใช้เวลาสักครู่";
  body.innerHTML = `<div class="empty">กำลังโหลด...</div>`;
  try {
    const d = await api("/api/children", { path });
    const total = d.items.reduce((a, x) => a + x.size, 0);
    $("sheet-title").textContent = shortPath(d.path);
    $("sheet-sub").textContent = `รวม ${fmt(total)} · ${d.items.length} รายการ (แสดงสูงสุด 200)`;
    const up = d.parent ? `<button class="btn ghost" data-browse="${esc(d.parent)}">⬆ ขึ้นหนึ่งระดับ</button>` : "";
    body.innerHTML = `
      <div class="crumb">${up}<span class="muted">${esc(shortPath(d.path))}</span></div>
      ${d.items.length ? d.items.map(entryRow).join("") : `<div class="empty">โฟลเดอร์ว่าง</div>`}`;
  } catch (e) {
    body.innerHTML = `<div class="empty">เปิดดูไม่ได้: ${esc(e.message)}</div>`;
  }
}

export function openBrowser(path) {
  openSheet({ title: shortPath(path), mode: "text", browse: true, load: () => show(path) });
}

/* ผูกอีเวนต์ครั้งเดียว: ปุ่มเปิดใน Finder ทำงานก่อนการเข้าโฟลเดอร์ */
export function initBrowser() {
  $("folders").addEventListener("click", (e) => {
    const rev = e.target.closest("[data-reveal]");
    if (rev) return revealInFinder(rev.dataset.reveal);
    const nav = e.target.closest("[data-browse]");
    if (nav) openBrowser(nav.dataset.browse);
  });
  $("sheet-text").addEventListener("click", (e) => {
    if (!state.sheet || !state.sheet.browse) return;
    const rev = e.target.closest("[data-reveal]");
    if (rev) return revealInFinder(rev.dataset.reveal);
    const ex = e.target.closest("[data-exclude]");
    if (ex) return excludeFolder(ex.dataset.exclude);
    const nav = e.target.closest("[data-browse]");
    if (nav) show(nav.dataset.browse);
  });
}
