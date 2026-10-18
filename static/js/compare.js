/* บันทึกรายงาน และเปรียบเทียบกับ snapshot ที่เลือกเป็นตาราง */

import { $, esc, fmt, shortPath, job } from "./dom.js";
import { api, revealInFinder } from "./api.js";
import { alertBox, confirmBox, pickDialog } from "./dialog.js";

let snapshots = [];
let selectedName = null;        // snapshot ที่เลือกไว้สำหรับเทียบและลบ

function fmtTime(iso) {
  return new Date(iso).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" });
}

/* ป้ายสั้นที่อ่านง่าย: "วันนี้ 22:17", "เมื่อวาน 09:05", "3 วันก่อน · 15 ต.ค. 12:31" */
function snapLabel(iso) {
  const t = new Date(iso);
  const today = new Date();
  const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const days = Math.round((day(today) - day(t)) / 86400000);
  const hm = t.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
  if (days === 0) return `วันนี้ ${hm}`;
  if (days === 1) return `เมื่อวาน ${hm}`;
  const date = t.toLocaleDateString("th-TH", { day: "numeric", month: "short" });
  return `${days} วันก่อน · ${date} ${hm}`;
}

function renderSnapshots() {
  if (!snapshots.some(s => s.name === selectedName)) selectedName = snapshots[0]?.name ?? null;
  const cur = snapshots.find(s => s.name === selectedName);
  const pick = $("snap-pick");
  pick.textContent = cur ? snapLabel(cur.time) : "ยังไม่มี snapshot";
  pick.title = cur ? fmtTime(cur.time) : "";
  pick.disabled = !snapshots.length;
  $("snap-delete").disabled = !snapshots.length;
}

/* เลือก snapshot จากกล่องรายการ (เลื่อนดูได้ทั้งหมด) */
async function openSnapshotPicker() {
  const value = await pickDialog({
    title: "เลือก snapshot",
    items: snapshots.map(s => ({ value: s.name, label: snapLabel(s.time), sub: fmtTime(s.time) })),
    selected: selectedName,
  });
  if (value === null) return;
  selectedName = value;
  renderSnapshots();
}

export async function loadSnapshots() {
  try {
    const { items } = await api("/api/snapshots");
    snapshots = items;
    renderSnapshots();
  } catch (e) {
    // ไม่มีรายการก็ใช้ส่วนอื่นของหน้าได้ตามปกติ
  }
}

async function deleteSnapshot() {
  const cur = snapshots.find(s => s.name === selectedName);
  if (!cur) return;
  const ok = await confirmBox(
    `จะย้าย snapshot "${snapLabel(cur.time)}" ไปถังขยะ\n\nรายงาน .md และ .csv ที่บันทึกคู่กันจะไม่ถูกลบ`,
    { title: "ลบ snapshot", confirmLabel: "ย้ายไปถังขยะ", danger: true });
  if (!ok) return;
  try {
    const r = await api("/api/snapshot_delete", { snapshot: cur.name });
    if (!r.ok) throw new Error(r.output || "ย้ายไม่สำเร็จ");
    selectedName = null;
    await loadSnapshots();
  } catch (e) {
    await alertBox("ลบ snapshot ไม่สำเร็จ: " + e.message, { title: "ลบไม่สำเร็จ", tone: "error" });
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
  const name = selectedName;
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
  $("snap-pick").onclick = openSnapshotPicker;
  $("snap-delete").onclick = deleteSnapshot;
  $("diff-out").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-reveal]");
    if (btn) revealInFinder(btn.dataset.reveal);
  });
}
