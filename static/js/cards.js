/* การ์ดสรุปผลและแถบโฟลเดอร์ */

import { $, fmt, esc } from "./dom.js";
import { state } from "./state.js";
import { t, locale, onLangChange } from "./i18n.js";

function totals() {
  const cache = state.cache.reduce((a, x) => a + x.size, 0);
  const big = state.files.filter(x => x.category === "review").reduce((a, x) => a + x.size, 0);
  return { cache, big };
}

/* พื้นที่ที่คืนได้จากรายการซ้ำ = ทุกฉบับที่ไม่ใช่ฉบับที่เก็บไว้ */
function reclaimText(items) {
  if (!items) return "–";
  const removable = items.filter(x => !x.keep);
  if (!removable.length) return t("card.reclaim_none");
  return fmt(removable.reduce((a, x) => a + x.size, 0));
}

export function renderCards() {
  const sum = totals();
  $("cache-size").textContent = state.cache.length ? fmt(sum.cache) : "–";
  $("big-size").textContent = fmt(sum.big);
  $("dups-size").textContent = reclaimText(state.dups);
  $("fdups-size").textContent = reclaimText(state.folderDups);

  if (state.disk) {
    $("used-label").textContent = t("disk.used", { size: fmt(state.disk.used) });
    $("free-label").textContent = t("disk.free", { size: fmt(state.disk.free) });
  }
  $("scan-btn").textContent = t(state.scanned ? "scan.again" : "scan.start");

  const when = state.scannedAt
    ? t("summary.when", { time: new Date(state.scannedAt).toLocaleString(locale(), { dateStyle: "medium", timeStyle: "short" }) })
    : "";
  $("summary").textContent = state.scanned
    ? t("summary.found", { size: fmt(sum.cache + sum.big) }) + when
    : t("summary.idle");
}

export function renderFolders(folders) {
  const max = folders.length ? folders[0].size : 1;
  $("folders").innerHTML = folders.slice(0, 15).map(f => `
    <div class="row-bar nav" data-browse="${esc(f.path)}" title="${esc(t("folders.view_sub"))}">
      <span class="name" title="${esc(f.name)}">${esc(f.name)}</span>
      <div class="track"><span style="width:${(f.size / max * 100).toFixed(1)}%"></span></div>
      <button class="btn quiet reveal" data-reveal="${esc(f.path)}">${esc(t("common.finder_open"))}</button>
    </div>`).join("");
}

onLangChange(() => {
  renderCards();
  renderFolders(state.folders);
});
