/* หน้าต่างเครื่องมือนักพัฒนา: ดู dry-run แล้วค่อยเคลียร์จริง */

import { $, esc } from "./dom.js";
import { api } from "./api.js";
import { alertBox, confirmBox } from "./dialog.js";

export const toolsSheet = {
  title: "เครื่องมือนักพัฒนา",
  sub: "นี่คือพื้นที่ที่คืนได้ตามคำสั่งของแต่ละเครื่องมือ ยังไม่มีอะไรถูกลบ",
  mode: "text",
  load: async () => {
    $("sheet-text").innerHTML = `<div class="empty">กำลังตรวจ...</div>`;
    const r = await api("/api/tools", { apply: false });
    $("sheet-text").innerHTML = `<pre class="out">${esc(r.output || "(ไม่มีข้อมูล)")}</pre>`;
  },
  action: "เคลียร์ตามที่แสดง",
  onAction: async () => {
    const ok = await confirmBox(
      "จะเคลียร์แคชของ Docker, Homebrew, conda และ pnpm\n\nDocker volumes จะไม่ถูกแตะ",
      { title: "เคลียร์แคชของเครื่องมือนักพัฒนา", confirmLabel: "เคลียร์", danger: true });
    if (!ok) return;
    $("sheet-action").disabled = true;
    $("sheet-text").innerHTML = `<div class="empty">กำลังเคลียร์...</div>`;
    try {
      const r = await api("/api/tools", { apply: true });
      $("sheet-text").innerHTML = `<pre class="out">${esc(r.output || "เสร็จแล้ว")}</pre>`;
    } catch (e) {
      await alertBox("เกิดข้อผิดพลาด: " + e.message, { title: "เคลียร์ไม่สำเร็จ", tone: "error" });
    }
    $("sheet-action").hidden = true;
  },
};
