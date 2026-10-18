/* บันทึกรายงาน และเปรียบเทียบกับ snapshot ที่เลือกเป็นตาราง */

import { $, esc, fmt, shortPath, job } from "./dom.js";
import { api, revealInFinder } from "./api.js";

function fmtTime(iso) {
  return new Date(iso).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" });
}

export async function loadSnapshots() {
  try {
    const { items } = await api("/api/snapshots");
    $("snap-select").innerHTML = items.length
      ? items.map(s => `<option value="${esc(s.name)}">${esc(fmtTime(s.time))}</option>`).join("")
      : `<option value="">ยังไม่มี snapshot</option>`;
  } catch (e) {
    // ไม่มีรายการก็ใช้ส่วนอื่นของหน้าได้ตามปกติ
  }
}

export function saveReport() {
  const out = $("compare-out");
  out.hidden = false;
  out.textContent = "กำลังบันทึกรายงาน...";
  return job("กำลังบันทึกรายงาน...", async () => {
    const r = await api("/api/report");
    out.textContent = r.output || "(ไม่มีผลลัพธ์)";
    await loadSnapshots();
  });
}

function deltaRows(list, sign) {
  if (!list.length) return `<div class="muted">ไม่มี</div>`;
  return `<table class="diff">${list.map(r => `
    <tr><td class="sz">${sign}${fmt(Math.abs(r.delta))}</td><td class="name">${esc(r.name)}</td></tr>`).join("")}
  </table>`;
}

export function renderDiff(d) {
  const added = d.added.length
    ? d.added.map(r => `
        <div class="entry">
          <span class="sz">${fmt(r.size)}</span>
          <span class="name">${esc(shortPath(r.path))}</span>
          <button class="btn quiet reveal" data-reveal="${esc(r.path)}">เปิดใน Finder</button>
          <span></span>
        </div>`).join("")
    : `<div class="muted">ไม่มี</div>`;
  return `
    <h3>โฟลเดอร์ที่โตขึ้น</h3>${deltaRows(d.grown, "+")}
    <h3>โฟลเดอร์ที่เล็กลง</h3>${deltaRows(d.shrunk, "−")}
    <h3>ไฟล์ใหญ่ใหม่ ${Math.min(d.added.length, d.added_total)} จาก ${d.added_total}</h3>${added}
    <p class="note">ไฟล์ที่หายไปจาก snapshot เดิม ${d.removed} ไฟล์ · เทียบกับ ${esc(fmtTime(d.time))}</p>`;
}

export function compareSelected() {
  const out = $("diff-out");
  const name = $("snap-select").value;
  out.hidden = false;
  return job("กำลังเทียบ... ต้องสแกนทั้ง home ใหม่ อาจใช้เวลาหลายนาที", async () => {
    out.innerHTML = `<div class="empty">กำลังเทียบ...</div>`;
    try {
      const d = await api("/api/diff", name ? { snapshot: name } : {});
      out.innerHTML = d.ok ? renderDiff(d) : `<div class="empty">${esc(d.message)}</div>`;
    } catch (e) {
      out.innerHTML = `<div class="empty">เทียบไม่สำเร็จ: ${esc(e.message)}</div>`;
    }
  });
}

export async function weeklySummary() {
  const out = $("diff-out");
  out.hidden = false;
  return job("กำลังสรุป... ต้องสแกนทั้ง home ใหม่ อาจใช้เวลาหลายนาที", async () => {
    out.innerHTML = `<div class="empty">กำลังสรุป...</div>`;
    try {
      const d = await api("/api/weekly");
      out.innerHTML = d.ok
        ? `<p class="note">สรุปเทียบกับเมื่อ ${d.days} วันก่อน</p>${renderDiff(d)}`
        : `<div class="empty">${esc(d.message)}</div>`;
    } catch (e) {
      out.innerHTML = `<div class="empty">สรุปไม่สำเร็จ: ${esc(e.message)}</div>`;
    }
  });
}

export function initCompare() {
  $("diff-out").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-reveal]");
    if (btn) revealInFinder(btn.dataset.reveal);
  });
}
