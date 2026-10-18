/* กล่องข้อความแทน alert() กับ confirm() ของเบราว์เซอร์ ออกแบบให้เข้ากับหน้าเว็บ */

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

export function alertBox(message, { title = "แจ้งให้ทราบ", tone = "info" } = {}) {
  return openDialog({
    title, message, tone, cancelValue: true,
    buttons: [{ label: "ตกลง", value: true, kind: "primary" }],
  });
}

export function confirmBox(message, { title = "ยืนยันการทำรายการ", confirmLabel = "ยืนยัน", danger = false } = {}) {
  return openDialog({
    title, message, tone: danger ? "warn" : "info", cancelValue: false,
    buttons: [
      { label: "ยกเลิก", value: false, kind: "quiet" },
      { label: confirmLabel, value: true, kind: danger ? "danger" : "primary" },
    ],
  });
}
