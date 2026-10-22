/* จุดเริ่มต้นของหน้าเว็บ: ผูกปุ่มต่าง ๆ เข้ากับโมดูลที่เกี่ยวข้อง */

import { t } from "./i18n.js";
import { $ } from "./dom.js";
import { state } from "./state.js";
import { openSheet, initSheet } from "./sheet.js";
import { renderCards } from "./cards.js";
import { trashSelected } from "./trash.js";
import { runScan, loadLast } from "./scan.js";
import { saveReport, compareSelected, weeklySummary, loadSnapshots, initCompare } from "./compare.js";
import { toolsSheet } from "./tools.js";
import { openDuplicates, openFolderDuplicates } from "./dups.js";
import { initBrowser } from "./browse.js";
import { loadSettings, initSettings } from "./settings.js";

initSheet();
initBrowser();
initSettings();
initCompare();

$("scan-btn").onclick = runScan;

$("cache-btn").onclick = () => {
  if (!state.scanned) return;
  openSheet({
    title: () => t("card.cache.title"),
    sub: () => t("sheet.cache_sub"),
    mode: "list",
    items: () => state.cache,
    action: () => t("common.move_to_trash"),
    onAction: () => trashSelected((paths) => {
      state.cache = state.cache.filter(x => !paths.includes(x.path));
    }),
  });
};

$("big-btn").onclick = () => {
  if (!state.scanned) return;
  openSheet({
    title: () => t("card.big.title"),
    sub: () => t("sheet.big_sub"),
    mode: "list",
    items: () => state.files.filter(x => x.category === "review"),
    action: () => t("common.move_to_trash"),
    onAction: () => trashSelected((paths) => {
      state.files = state.files.filter(x => !paths.includes(x.path));
    }),
  });
};

$("tools-btn").onclick = () => openSheet(toolsSheet);
$("dups-btn").onclick = openDuplicates;
$("fdups-btn").onclick = openFolderDuplicates;

$("report-btn").onclick = saveReport;
$("diff-btn").onclick = compareSelected;
$("weekly-btn").onclick = weeklySummary;

/* เริ่มต้น: วาดข้อความเริ่มต้น โหลดค่าตั้งค่า ผลสแกนเดิม และรายการ snapshot */
renderCards();
loadSettings();
loadLast();
loadSnapshots();
