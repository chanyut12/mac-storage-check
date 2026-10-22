/* ย้ายรายการที่เลือกไปถังขยะ (ผ่าน API ที่มีการตรวจเส้นทางฝั่งเซิร์ฟเวอร์) */

import { $, fmt, setBusy } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { t } from "./i18n.js";
import { selectedPaths, renderList, updateSheetSum } from "./sheet.js";
import { renderCards } from "./cards.js";
import { alertBox, confirmBox } from "./dialog.js";

export async function trashSelected(afterRemove) {
  const paths = selectedPaths();
  if (!paths.length) return;
  const items = state.sheet.items().filter(x => paths.includes(x.path));
  const size = items.reduce((a, x) => a + x.size, 0);
  const vars = { n: paths.length, size: fmt(size) };

  const ok = await confirmBox(t("trash.confirm", vars),
    { title: t("common.move_to_trash"), confirmLabel: t("common.move_to_trash"), danger: true });
  if (!ok) return;

  $("sheet-action").disabled = true;
  setBusy(true, t("trash.busy", vars));
  try {
    const r = await api("/api/trash", { paths });
    if (!r.ok) {
      await alertBox(r.output, { title: t("trash.failed_title"), tone: "warn" });
      return;
    }
    afterRemove(paths);
    renderList();
    renderCards();
    await alertBox(t("trash.done", vars), { title: t("trash.done_title"), tone: "ok" });
  } catch (e) {
    await alertBox(t("error.with_message", { message: e.message }), { title: t("trash.failed_title"), tone: "error" });
  } finally {
    setBusy(false);
    updateSheetSum();
  }
}
