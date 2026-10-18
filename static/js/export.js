/* ส่งออกรายการที่แสดงอยู่เป็น CSV ประกอบในเบราว์เซอร์ (ไม่ส่งข้อมูลออกนอกเครื่อง) */

function cell(v) {
  const s = v == null ? "" : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function exportCsv(rows, filename) {
  const lines = [["path", "size_bytes", "kind", "last_access", "keep"].join(",")];
  for (const x of rows) {
    const last = x.last_access == null ? "" : new Date(x.last_access * 1000).toISOString();
    lines.push([x.path, x.size, x.kind, last, x.keep ? "yes" : "no"].map(cell).join(","));
  }
  // BOM ทำให้ Excel อ่านภาษาไทยได้ถูกต้อง
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
