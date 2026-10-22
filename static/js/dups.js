/* การ์ดไฟล์ซ้ำและโฟลเดอร์ซ้ำ: ค้นหาครั้งแรกแล้วเก็บผลไว้จนกว่าจะรีสแกน */

import { job } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { t } from "./i18n.js";
import { openSheet } from "./sheet.js";
import { trashSelected } from "./trash.js";
import { renderCards } from "./cards.js";

/* หน้าต่างรายการของกลุ่มซ้ำ ใช้ได้ทั้งไฟล์และโฟลเดอร์ โดยแยกผลด้วย key ใน state */
function groupSheet(key, titleKey, subKey) {
  return {
    title: () => t(titleKey),
    sub: () => t(subKey),
    mode: "list",
    items: () => state[key],
    action: () => t("common.move_to_trash"),
    onAction: () => trashSelected((paths) => {
      state[key] = state[key].filter(x => !paths.includes(x.path));
    }),
  };
}

const dupsSheet = groupSheet("dups", "card.dups.title", "dups.sub");
const folderDupsSheet = groupSheet("folderDups", "card.fdups.title", "fdups.sub");

async function openFound(key, path, sheet) {
  if (!state[key]) {
    const d = await job(t("dups.busy"), () => api(path));
    if (!d) return;
    state[key] = d.items;
    renderCards();
  }
  openSheet(sheet);
}

export function openDuplicates() {
  return openFound("dups", "/api/duplicates", dupsSheet);
}

export function openFolderDuplicates() {
  return openFound("folderDups", "/api/folder_duplicates", folderDupsSheet);
}
