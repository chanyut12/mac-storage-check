/* ป้ายที่แสดงของรหัสประเภทไฟล์ (รหัสมาจาก gui.py: kind_of) ขั้นถัดไปจะย้ายไปอยู่ในระบบแปลภาษา */

const KIND_LABELS = {
  video: "วิดีโอ",
  archive: "ไฟล์บีบอัด",
  disk_image: "disk image",
  data: "ข้อมูล",
  ai_model: "โมเดล AI",
  document: "เอกสาร",
  image: "รูปภาพ",
  folder: "โฟลเดอร์",
  other: "อื่น ๆ",
};

export function kindLabel(code) {
  return KIND_LABELS[code] ?? code;
}
