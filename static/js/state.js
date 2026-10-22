/* สถานะกลางของหน้าเว็บ ใช้ร่วมกันทุกโมดูล */

export const state = {
  files: [],          // ไฟล์ขนาดใหญ่จากการสแกนล่าสุด
  cache: [],          // รายการแคช
  folders: [],        // โฟลเดอร์ระดับที่ 2 ที่ใช้พื้นที่มาก
  scanned: false,     // สแกนแล้วหรือยัง
  scannedAt: null,    // เวลาที่สแกนครั้งล่าสุด (ISO)
  disk: null,         // พื้นที่ดิสก์ {total, used, free} จากการสแกนล่าสุด
  settings: { min_mb: 100, dup_min_mb: 10, old_months: 12, exclude: [], home: "" },
  dups: null,         // ไฟล์ซ้ำ (null = ยังไม่ได้ค้นหา) แต่ละแถวมี keep และ group
  folderDups: null,   // โฟลเดอร์ซ้ำ รูปแบบเดียวกับ dups
  sheet: null,        // ข้อมูลหน้าต่างที่เปิดอยู่ (null เมื่อปิด)
};
