/* ปุ่มตรวจพื้นที่ และการโหลดผลสแกนล่าสุดที่บันทึกไว้ */

import { $, fmt, job } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { renderCards, renderFolders } from "./cards.js";

/* แสดงผลสแกน ใช้ทั้งตอนสแกนใหม่และตอนโหลดผลเดิมตอนเปิดหน้า */
export function applyScan(d) {
  state.files = d.files;
  state.cache = d.cache;
  state.folders = d.folders;
  state.scanned = true;
  state.scannedAt = d.time;

  const { used, total, free } = d.disk;
  $("disk").hidden = false;
  $("meter").style.width = (used / total * 100).toFixed(1) + "%";
  $("used-label").textContent = `ใช้ไป ${fmt(used)}`;
  $("free-label").textContent = `ว่าง ${fmt(free)}`;

  renderFolders(d.folders);
  $("cards").hidden = false;
  renderCards();
  $("scan-btn").textContent = "ตรวจอีกครั้ง";
}

export function runScan() {
  return job("กำลังตรวจ... อาจใช้เวลาหลายนาที กรุณารอสักครู่", async () => {
    applyScan(await api("/api/scan"));
  });
}

/* ตอนเปิดหน้า โหลดผลล่าสุดถ้ามี (ไม่สแกนใหม่เอง เพราะใช้เวลานาน) */
export async function loadLast() {
  try {
    const d = await api("/api/last");
    if (d.scanned !== false) applyScan(d);
  } catch (e) {
    // ไม่มีผลเดิมหรือเซิร์ฟเวอร์ยังไม่พร้อม ให้หน้าเริ่มต้นตามปกติ
  }
}
