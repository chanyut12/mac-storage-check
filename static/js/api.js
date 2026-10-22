/* เรียก API ของ gui.py ทุกอย่างผ่านฟังก์ชันนี้ */

import { alertBox } from "./dialog.js";
import { getLang, t } from "./i18n.js";

export async function api(path, body = {}) {
  let r;
  try {
    r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ ...body, lang: getLang() }) });
  } catch (e) {
    throw new Error(`${t("err.connect")} ${t("err.hint")}`);
  }

  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }

  if (data === null) throw new Error(`${t("err.not_json", { status: r.status })} ${t("err.hint")}`);
  if (!r.ok) {
    if (data.detail) console.error(data.detail);      // รายละเอียดของข้อผิดพลาดที่ไม่คาดคิด ไว้ให้ผู้พัฒนา
    throw new Error(data.error || t("err.generic"));
  }
  return data;
}

/* เปิดตำแหน่งไฟล์หรือโฟลเดอร์ใน Finder ใช้ร่วมกันทุกหน้า */
export async function revealInFinder(path) {
  try {
    const r = await api("/api/reveal", { path });
    if (!r.ok) await alertBox(r.output, { title: t("reveal.error.title"), tone: "warn" });
  } catch (e) {
    await alertBox(t("reveal.error.failed", { message: e.message }), { title: t("reveal.error.title"), tone: "error" });
  }
}
