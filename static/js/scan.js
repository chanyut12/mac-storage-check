/* ปุ่มตรวจพื้นที่ และการโหลดผลสแกนล่าสุดที่บันทึกไว้ */

import { $, job } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { t } from "./i18n.js";
import { renderCards, renderFolders } from "./cards.js";

/* แสดงผลสแกน ใช้ทั้งตอนสแกนใหม่และตอนโหลดผลเดิมตอนเปิดหน้า */
export function applyScan(d) {
  state.files = d.files;
  state.cache = d.cache;
  state.folders = d.folders;
  state.scanned = true;
  state.scannedAt = d.time;
  state.disk = d.disk;

  $("disk").hidden = false;
  $("meter").style.width = (d.disk.used / d.disk.total * 100).toFixed(1) + "%";

  renderFolders(d.folders);
  $("cards").hidden = false;
  renderCards();
}

export function runScan() {
  return job(t("scan.busy"), async () => {
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
