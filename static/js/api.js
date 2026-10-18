/* เรียก API ของ gui.py ทุกอย่างผ่านฟังก์ชันนี้ */

import { alertBox } from "./dialog.js";

const HINT = "ต้องเปิดผ่าน gui.py ที่ http://127.0.0.1:8765 (ไม่ใช่ Live Server หรือไฟล์ที่เปิดตรง ๆ)";

export async function api(path, body = {}) {
  let r;
  try {
    r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(body) });
  } catch (e) {
    throw new Error("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ " + HINT);
  }

  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }

  if (data === null) throw new Error(`ได้รับคำตอบที่ไม่ใช่ JSON (สถานะ ${r.status}) ${HINT}`);
  if (!r.ok) throw new Error(data.error || "เกิดข้อผิดพลาด");
  return data;
}

/* เปิดตำแหน่งไฟล์หรือโฟลเดอร์ใน Finder ใช้ร่วมกันทุกหน้า */
export async function revealInFinder(path) {
  try {
    const r = await api("/api/reveal", { path });
    if (!r.ok) await alertBox(r.output, { title: "เปิด Finder ไม่ได้", tone: "warn" });
  } catch (e) {
    await alertBox("เปิด Finder ไม่สำเร็จ: " + e.message, { title: "เปิด Finder ไม่ได้", tone: "error" });
  }
}
