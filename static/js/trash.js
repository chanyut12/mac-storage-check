/* ย้ายรายการที่เลือกไปถังขยะ (ผ่าน API ที่มีการตรวจเส้นทางฝั่งเซิร์ฟเวอร์) */

import { $, fmt, setBusy } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { selectedPaths, renderList, updateSheetSum } from "./sheet.js";
import { renderCards } from "./cards.js";
import { alertBox, confirmBox } from "./dialog.js";

export async function trashSelected(afterRemove) {
  const paths = selectedPaths();
  if (!paths.length) return;
  const items = state.sheet.items().filter(x => paths.includes(x.path));
  const size = items.reduce((a, x) => a + x.size, 0);

  const ok = await confirmBox(
    `จะย้าย ${paths.length} รายการ (${fmt(size)}) ไปถังขยะ\n\nกู้คืนได้จากถังขยะ`,
    { title: "ย้ายไปถังขยะ", confirmLabel: "ย้ายไปถังขยะ", danger: true });
  if (!ok) return;

  $("sheet-action").disabled = true;
  setBusy(true, `กำลังย้าย ${paths.length} รายการไปถังขยะ...`);
  try {
    const r = await api("/api/trash", { paths });
    if (!r.ok) {
      await alertBox(r.output, { title: "ย้ายไม่สำเร็จ", tone: "warn" });
      return;
    }
    afterRemove(paths);
    renderList();
    renderCards();
    await alertBox(`ย้าย ${paths.length} รายการไปถังขยะแล้ว (รวม ${fmt(size)})\nกู้คืนได้จากถังขยะ`,
                   { title: "ย้ายแล้ว", tone: "ok" });
  } catch (e) {
    await alertBox("เกิดข้อผิดพลาด: " + e.message, { title: "ย้ายไม่สำเร็จ", tone: "error" });
  } finally {
    setBusy(false);
    updateSheetSum();
  }
}
