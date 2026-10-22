/* หน้าต่างเครื่องมือนักพัฒนา: ดู dry-run แล้วค่อยเคลียร์หรืออัปเดตจริง */

import { $, esc } from "./dom.js";
import { api } from "./api.js";
import { t } from "./i18n.js";
import { alertBox, confirmBox } from "./dialog.js";

function showBrewUpgradeButton() {
  const btn = $("brew-upgrade-btn");
  if (btn) btn.onclick = onBrewUpgrade;
}

async function onBrewUpgrade() {
  const ok = await confirmBox(t("tools.brew_confirm"),
    { title: t("tools.brew_title"), confirmLabel: t("tools.brew_label"), danger: true });
  if (!ok) return;
  $("sheet-text").innerHTML = `<div class="empty">${esc(t("tools.brew_busy"))}</div>`;
  try {
    const r = await api("/api/brew_upgrade", { apply: true });
    $("sheet-text").innerHTML = `<pre class="out">${esc(r.output || t("tools.done"))}</pre>`;
  } catch (e) {
    await alertBox(t("error.with_message", { message: e.message }), { title: t("tools.brew_failed_title"), tone: "error" });
  }
}

export const toolsSheet = {
  title: () => t("card.tools.title"),
  sub: () => t("tools.sheet_sub"),
  mode: "text",
  load: async () => {
    $("sheet-text").innerHTML = `<div class="empty">${esc(t("tools.checking"))}</div>`;
    const [tools, brew] = await Promise.all([
      api("/api/tools", { apply: false }),
      api("/api/brew_upgrade", { apply: false }),
    ]);
    $("sheet-text").innerHTML = `
      <pre class="out">${esc(tools.output || t("tools.no_data"))}</pre>
      <p><strong>${esc(t("tools.brew_outdated"))}</strong></p>
      <pre class="out">${esc(brew.output || t("tools.no_data"))}</pre>
      ${brew.outdated ? `<div class="actions"><button class="btn quiet" id="brew-upgrade-btn">${esc(t("tools.brew_button"))}</button></div>` : ""}`;
    showBrewUpgradeButton();
  },
  action: () => t("tools.action"),
  onAction: async () => {
    const ok = await confirmBox(t("tools.clean_confirm"),
      { title: t("tools.clean_title"), confirmLabel: t("tools.clean_label"), danger: true });
    if (!ok) return;
    $("sheet-action").disabled = true;
    $("sheet-text").innerHTML = `<div class="empty">${esc(t("tools.cleaning"))}</div>`;
    try {
      const r = await api("/api/tools", { apply: true });
      $("sheet-text").innerHTML = `<pre class="out">${esc(r.output || t("tools.done"))}</pre>`;
    } catch (e) {
      await alertBox(t("error.with_message", { message: e.message }), { title: t("tools.clean_failed_title"), tone: "error" });
    }
    $("sheet-action").hidden = true;
  },
};
