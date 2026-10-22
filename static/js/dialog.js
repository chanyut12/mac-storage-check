/* กล่องข้อความแทน alert() กับ confirm() ของเบราว์เซอร์ ออกแบบให้เข้ากับหน้าเว็บ */

import { t } from "./i18n.js";

const ICONS = { info: "ℹ️", ok: "✅", warn: "⚠️", error: "⛔" };

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
}

/* เปิดกล่องข้อความ คืน Promise ที่ให้ค่าของปุ่มที่กด (หรือค่าตอนยกเลิกด้วย Esc) */
function openDialog({ title, message, tone = "info", buttons, cancelValue }) {
  return new Promise((resolve) => {
    const wrap = document.createElement("div");
    wrap.className = "dlg-overlay";
    wrap.innerHTML = `
      <div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="dlg-title">
        <div class="dlg-icon ${tone}">${ICONS[tone] || ICONS.info}</div>
        <h3 id="dlg-title">${escapeHtml(title)}</h3>
        <p>${escapeHtml(message).replace(/\n/g, "<br>")}</p>
        <div class="dlg-actions"></div>
      </div>`;
    const actions = wrap.querySelector(".dlg-actions");
    let primary = null;

    const close = (value) => {
      document.removeEventListener("keydown", onKey);
      wrap.classList.add("out");
      setTimeout(() => wrap.remove(), 160);
      resolve(value);
    };
    const onKey = (e) => {
      if (e.key === "Escape" && cancelValue !== undefined) close(cancelValue);
      if (e.key === "Enter" && primary) primary.click();
    };

    buttons.forEach((b) => {
      const btn = document.createElement("button");
      btn.className = `btn ${b.kind || "quiet"}`;
      btn.textContent = b.label;
      btn.onclick = () => close(b.value);
      if (b.kind === "primary" || b.kind === "danger") primary = btn;
      actions.appendChild(btn);
    });

    document.addEventListener("keydown", onKey);
    document.body.appendChild(wrap);
    (primary || actions.querySelector("button")).focus();
  });
}

/* กล่องเลือกจากรายการ คืนค่าของรายการที่กด หรือ null ถ้าปิด (ปุ่มปิด, คลิกนอกกล่อง, Esc) */
export function pickDialog({ title, items, selected = null }) {
  return new Promise((resolve) => {
    const wrap = document.createElement("div");
    wrap.className = "dlg-overlay";
    wrap.innerHTML = `
      <div class="dlg wide" role="dialog" aria-modal="true" aria-labelledby="dlg-title">
        <h3 id="dlg-title">${escapeHtml(title)}</h3>
        <div class="pick-list">${items.map(it => `
          <button class="pick-item${it.value === selected ? " on" : ""}" data-value="${escapeHtml(it.value)}">
            <span>${escapeHtml(it.label)}</span><small>${escapeHtml(it.sub || "")}</small>
          </button>`).join("")}
        </div>
        <div class="dlg-actions"><button class="btn quiet" data-close>${escapeHtml(t("common.close"))}</button></div>
      </div>`;
    const close = (value) => {
      document.removeEventListener("keydown", onKey);
      wrap.classList.add("out");
      setTimeout(() => wrap.remove(), 160);
      resolve(value);
    };
    const onKey = (e) => { if (e.key === "Escape") close(null); };
    wrap.addEventListener("click", (e) => {
      if (e.target === wrap || e.target.closest("[data-close]")) return close(null);
      const item = e.target.closest(".pick-item");
      if (item) close(item.dataset.value);
    });
    document.addEventListener("keydown", onKey);
    document.body.appendChild(wrap);
    (wrap.querySelector(".pick-item.on") || wrap.querySelector("[data-close]")).focus();
  });
}

export function alertBox(message, { title = t("dialog.notice"), tone = "info" } = {}) {
  return openDialog({
    title, message, tone, cancelValue: true,
    buttons: [{ label: t("dialog.ok"), value: true, kind: "primary" }],
  });
}

export function confirmBox(message, { title = t("dialog.confirm_title"), confirmLabel = t("dialog.confirm"), danger = false } = {}) {
  return openDialog({
    title, message, tone: danger ? "warn" : "info", cancelValue: false,
    buttons: [
      { label: t("dialog.cancel"), value: false, kind: "quiet" },
      { label: confirmLabel, value: true, kind: danger ? "danger" : "primary" },
    ],
  });
}
