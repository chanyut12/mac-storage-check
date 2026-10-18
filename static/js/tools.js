/* หน้าต่างเครื่องมือนักพัฒนา: ดู dry-run แล้วค่อยเคลียร์หรืออัปเดตจริง */

import { $, esc } from "./dom.js";
import { api } from "./api.js";
import { alertBox, confirmBox } from "./dialog.js";

function showBrewUpgradeButton() {
  const btn = $("brew-upgrade-btn");
  if (btn) btn.onclick = onBrewUpgrade;
}

async function onBrewUpgrade() {
  const ok = await confirmBox(
    "จะอัปเดตแพ็กเกจ Homebrew ที่ล้าสมัยทั้งหมด (brew upgrade)\n\n" +
    "อาจใช้เวลานาน แพ็กเกจที่ต้องใช้รหัสผ่านผู้ดูแลระบบอาจอัปเดตไม่สำเร็จ",
    { title: "อัปเดตแพ็กเกจ Homebrew", confirmLabel: "อัปเดต", danger: true });
  if (!ok) return;
  $("sheet-text").innerHTML = `<div class="empty">กำลังอัปเดต... อาจใช้เวลาหลายนาที</div>`;
  try {
    const r = await api("/api/brew_upgrade", { apply: true });
    $("sheet-text").innerHTML = `<pre class="out">${esc(r.output || "เสร็จแล้ว")}</pre>`;
  } catch (e) {
    await alertBox("เกิดข้อผิดพลาด: " + e.message, { title: "อัปเดตไม่สำเร็จ", tone: "error" });
  }
}

export const toolsSheet = {
  title: "เครื่องมือนักพัฒนา",
  sub: "นี่คือพื้นที่ที่คืนได้ตามคำสั่งของแต่ละเครื่องมือ ยังไม่มีอะไรถูกลบหรืออัปเดตจนกว่าจะกดปุ่ม",
  mode: "text",
  load: async () => {
    $("sheet-text").innerHTML = `<div class="empty">กำลังตรวจ...</div>`;
    const [tools, brew] = await Promise.all([
      api("/api/tools", { apply: false }),
      api("/api/brew_upgrade", { apply: false }),
    ]);
    $("sheet-text").innerHTML = `
      <pre class="out">${esc(tools.output || "(ไม่มีข้อมูล)")}</pre>
      <p><strong>Homebrew: แพ็กเกจที่ล้าสมัย</strong></p>
      <pre class="out">${esc(brew.output || "(ไม่มีข้อมูล)")}</pre>
      <div class="actions"><button class="btn quiet" id="brew-upgrade-btn">อัปเดตแพ็กเกจ Homebrew</button></div>`;
    showBrewUpgradeButton();
  },
  action: "เคลียร์ตามที่แสดง",
  onAction: async () => {
    const ok = await confirmBox(
      "จะเคลียร์แคชของ Docker, Homebrew, conda, pnpm, npm และ pip\n\nDocker volumes จะไม่ถูกแตะ",
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
