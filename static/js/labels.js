/* ป้ายที่แสดงของรหัสประเภทไฟล์ (รหัสมาจาก gui.py: kind_of) ข้อความอยู่ใน static/locales */

import { t } from "./i18n.js";

export function kindLabel(code) {
  return t(`kind.${code}`);
}
