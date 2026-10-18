/* การ์ดสรุปผลและแถบโฟลเดอร์ */

import { $, fmt, esc } from "./dom.js";
import { state } from "./state.js";

function totals() {
  const cache = state.cache.reduce((a, x) => a + x.size, 0);
  const big = state.files.filter(x => x.category.includes("ตรวจก่อน")).reduce((a, x) => a + x.size, 0);
  return { cache, big };
}

/* พื้นที่ที่คืนได้จากรายการซ้ำ = ทุกฉบับที่ไม่ใช่ฉบับที่เก็บไว้ */
function reclaimText(items) {
  if (!items) return "–";
  const removable = items.filter(x => !x.keep);
  if (!removable.length) return "ไม่พบ";
  return fmt(removable.reduce((a, x) => a + x.size, 0));
}

export function renderCards() {
  const t = totals();
  $("cache-size").textContent = state.cache.length ? fmt(t.cache) : "–";
  $("big-size").textContent = fmt(t.big);
  $("dups-size").textContent = reclaimText(state.dups);
  $("fdups-size").textContent = reclaimText(state.folderDups);

  const when = state.scannedAt
    ? ` · ผลสแกนเมื่อ ${new Date(state.scannedAt).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" })}`
    : "";
  $("summary").textContent = state.scanned
    ? `พบพื้นที่ที่คืนได้ราว ${fmt(t.cache + t.big)} (เครื่องมือนักพัฒนาแยกต่างหาก)${when}`
    : "กดปุ่มด้านล่างเพื่อตรวจหาพื้นที่ที่คืนได้";
}

export function renderFolders(folders) {
  const max = folders.length ? folders[0].size : 1;
  $("folders").innerHTML = folders.slice(0, 15).map(f => `
    <div class="row-bar nav" data-browse="${esc(f.path)}" title="ดูโฟลเดอร์ย่อย">
      <span class="name" title="${esc(f.name)}">${esc(f.name)}</span>
      <div class="track"><span style="width:${(f.size / max * 100).toFixed(1)}%"></span></div>
      <button class="btn quiet reveal" data-reveal="${esc(f.path)}">เปิดใน Finder</button>
    </div>`).join("");
}
