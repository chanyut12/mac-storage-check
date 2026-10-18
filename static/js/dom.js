/* ตัวช่วยเกี่ยวกับ DOM และการจัดรูปแบบข้อความ */

import { alertBox } from "./dialog.js";

export const $ = (id) => document.getElementById(id);

/* ใช้หน่วยทศนิยม (1 GB = 10^9 ไบต์) ให้ตรงกับที่ macOS แสดงในหน้า Storage */
export function fmt(bytes) {
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + " GB";
  return Math.max(1, Math.round(bytes / 1e6)) + " MB";
}

export function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
}

export function shortPath(p) {
  return p.replace(/^\/Users\/[^/]+/, "~");
}

/* เปิด/ปิดสถานะกำลังทำงาน: แถบลอยด้านล่างมองเห็นได้เสมอ แม้เปิดหน้าต่างรายการค้างอยู่ */
export function setBusy(on, text) {
  $("busy").hidden = !on;
  if (text) $("busy-text").textContent = text;
  $("scan-btn").disabled = on;
  document.querySelectorAll(".card .btn, .more .btn").forEach(b => b.disabled = on);
}

/* รันงานที่ใช้เวลานาน พร้อมแจ้งข้อผิดพลาดถ้ามี */
export async function job(text, fn) {
  setBusy(true, text);
  try { return await fn(); }
  catch (e) { await alertBox("เกิดข้อผิดพลาด: " + e.message, { tone: "error", title: "ทำรายการไม่สำเร็จ" }); }
  finally { setBusy(false); }
}
