/* บันทึกรายงาน และเปรียบเทียบกับ snapshot ที่เลือกเป็นตาราง */

import { $, esc, fmt, shortPath, job } from "./dom.js";
import { api, revealInFinder } from "./api.js";
import { alertBox, confirmBox, pickDialog } from "./dialog.js";
import { t, locale, onLangChange } from "./i18n.js";

let snapshots = [];
let selectedName = null;        // snapshot ที่เลือกไว้สำหรับเทียบและลบ
let diffView = null;            // สิ่งที่แสดงใน #diff-out เก็บเป็นข้อมูลไว้วาดใหม่เมื่อเปลี่ยนภาษา

function fmtTime(iso) {
  return new Date(iso).toLocaleString(locale(), { dateStyle: "medium", timeStyle: "short" });
}

/* ป้ายสั้นที่อ่านง่าย: "วันนี้ 22:17", "เมื่อวาน 09:05", "3 วันก่อน · 15 ต.ค. 12:31" */
function snapLabel(iso) {
  const when = new Date(iso);
  const today = new Date();
  const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const days = Math.round((day(today) - day(when)) / 86400000);
  const time = when.toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });
  if (days === 0) return t("snap.today", { time });
  if (days === 1) return t("snap.yesterday", { time });
  const date = when.toLocaleDateString(locale(), { day: "numeric", month: "short" });
  return t("snap.days_ago", { n: days, date, time });
}

function renderSnapshots() {
  if (!snapshots.some(s => s.name === selectedName)) selectedName = snapshots[0]?.name ?? null;
  const cur = snapshots.find(s => s.name === selectedName);
  const pick = $("snap-pick");
  pick.textContent = cur ? snapLabel(cur.time) : t("snap.none");
  pick.title = cur ? fmtTime(cur.time) : "";
  pick.disabled = !snapshots.length;
  $("snap-delete").disabled = !snapshots.length;
}

/* เลือก snapshot จากกล่องรายการ (เลื่อนดูได้ทั้งหมด) */
async function openSnapshotPicker() {
  const value = await pickDialog({
    title: t("compare.picker_title"),
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
    t("compare.delete_confirm", { label: snapLabel(cur.time) }),
    { title: t("compare.delete_title"), confirmLabel: t("common.move_to_trash"), danger: true });
  if (!ok) return;
  try {
    const r = await api("/api/snapshot_delete", { snapshot: cur.name });
    if (!r.ok) throw new Error(r.output || t("compare.delete_move_failed"));
    selectedName = null;
    await loadSnapshots();
  } catch (e) {
    await alertBox(t("compare.delete_failed", { message: e.message }),
                   { title: t("compare.delete_failed_title"), tone: "error" });
  }
}

export function saveReport() {
  const out = $("compare-out");
  out.hidden = false;
  out.textContent = t("compare.saving");
  return job(t("compare.saving"), async () => {
    const r = await api("/api/report");
    out.textContent = r.output || t("compare.no_output");
    await loadSnapshots();
  });
}

function deltaRows(list, sign) {
  if (!list.length) return `<div class="muted">${esc(t("common.none"))}</div>`;
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
          <button class="btn quiet reveal" data-reveal="${esc(r.path)}">${esc(t("common.finder_open"))}</button>
          <span></span>
        </div>`).join("")
    : `<div class="muted">${esc(t("common.none"))}</div>`;
  const addedTitle = t("diff.added", { shown: Math.min(d.added.length, d.added_total), total: d.added_total });
  return `
    <h3>${esc(t("diff.grown"))}</h3>${deltaRows(d.grown, "+")}
    <h3>${esc(t("diff.shrunk"))}</h3>${deltaRows(d.shrunk, "−")}
    <h3>${esc(addedTitle)}</h3>${added}
    <p class="note">${esc(t("diff.note", { n: d.removed, time: fmtTime(d.time) }))}</p>`;
}

/* วาด #diff-out จาก diffView (วาดใหม่ได้เมื่อเปลี่ยนภาษา) */
function renderDiffOut() {
  const out = $("diff-out");
  const v = diffView;
  if (!v) return;
  out.hidden = false;
  if (v.kind === "diff") out.innerHTML = renderDiff(v.data);
  else if (v.kind === "weekly") {
    out.innerHTML = `<p class="note">${esc(t("compare.weekly_note", { n: v.data.days }))}</p>${renderDiff(v.data)}`;
  } else {
    // loading, error (มี message) หรือข้อความจากเซิร์ฟเวอร์ (code + vars)
    const text = v.code ? t(v.code, v.vars) : t(v.key, { message: v.message });
    out.innerHTML = `<div class="empty">${esc(text)}</div>`;
  }
}

function showDiff(v) {
  diffView = v;
  renderDiffOut();
}

export function compareSelected() {
  const name = selectedName;
  $("diff-out").hidden = false;
  return job(t("compare.busy"), async () => {
    showDiff({ kind: "text", key: "compare.comparing" });
    try {
      const d = await api("/api/diff", name ? { snapshot: name } : {});
      showDiff(d.ok ? { kind: "diff", data: d } : { kind: "text", code: d.code, vars: d.vars });
    } catch (e) {
      showDiff({ kind: "text", key: "compare.compare_failed", message: e.message });
    }
  });
}

export async function weeklySummary() {
  $("diff-out").hidden = false;
  return job(t("compare.weekly_busy"), async () => {
    showDiff({ kind: "text", key: "compare.summarizing" });
    try {
      const d = await api("/api/weekly");
      showDiff(d.ok ? { kind: "weekly", data: d } : { kind: "text", code: d.code, vars: d.vars });
    } catch (e) {
      showDiff({ kind: "text", key: "compare.weekly_failed", message: e.message });
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
  onLangChange(() => {
    renderSnapshots();
    renderDiffOut();
  });
}
