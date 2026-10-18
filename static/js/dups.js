/* การ์ดไฟล์ซ้ำและโฟลเดอร์ซ้ำ: ค้นหาครั้งแรกแล้วเก็บผลไว้จนกว่าจะรีสแกน */

import { job } from "./dom.js";
import { api } from "./api.js";
import { state } from "./state.js";
import { openSheet } from "./sheet.js";
import { trashSelected } from "./trash.js";
import { renderCards } from "./cards.js";

/* หน้าต่างรายการของกลุ่มซ้ำ ใช้ได้ทั้งไฟล์และโฟลเดอร์ โดยแยกผลด้วย key ใน state */
function groupSheet(key, title, sub) {
  return {
    title,
    sub,
    mode: "list",
    items: () => state[key],
    action: "ย้ายไปถังขยะ",
    onAction: () => trashSelected((paths) => {
      state[key] = state[key].filter(x => !paths.includes(x.path));
    }),
  };
}

const dupsSheet = groupSheet("dups", "ไฟล์ซ้ำ",
  "ฉบับที่ติดป้าย 'เก็บไว้' คือฉบับที่แก้ไขล่าสุดของแต่ละกลุ่ม เลือกไม่ได้ ติ๊กเฉพาะฉบับอื่นที่ต้องการย้ายออก");
const folderDupsSheet = groupSheet("folderDups", "โฟลเดอร์ซ้ำ",
  "โฟลเดอร์ที่เนื้อหาทั้งหมดเหมือนกัน ติ๊กได้เฉพาะโฟลเดอร์ที่ไม่ได้ติดป้าย 'เก็บไว้'");

async function openFound(key, path, sheet) {
  if (!state[key]) {
    const d = await job("กำลังค้นหา... อาจใช้เวลานานหลายนาที กรุณารอสักครู่", () => api(path));
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
