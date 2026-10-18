#!/usr/bin/env python3
"""เครื่องมือตรวจพื้นที่ดิสก์ macOS

โหมดที่มี
  scan          แสดงไฟล์และโฟลเดอร์ใหญ่สุด (อ่านอย่างเดียว)
  report        บันทึกรายงาน .md / .csv และ snapshot ไว้เทียบในภายหลัง (อ่านอย่างเดียว)
  diff          เทียบกับ snapshot ล่าสุด ดูว่าอะไรโตขึ้น (อ่านอย่างเดียว)
  tools         ดู/เคลียร์ cache ของ Docker, Homebrew, conda, pnpm (dry-run ถ้าไม่ใส่ --yes)
  clean-cache   ย้าย cache ใน ~/Library/Caches และ ~/.cache ไปถังขยะ (dry-run ถ้าไม่ใส่ --yes)
  interactive   เลือกไฟล์ทีละรายการแล้วย้ายไปถังขยะ (ยืนยันก่อนเสมอ)
  brew-upgrade  แสดงแพ็กเกจ Homebrew ที่ล้าสมัย และอัปเดตเมื่อใส่ --yes
  duplicates    หาไฟล์ที่เนื้อหาเหมือนกัน (dry-run ถ้าไม่ใส่ --yes; --yes เก็บฉบับที่แก้ไขล่าสุดไว้)

โค้ดแยกอยู่ในแพ็กเกจ storagecheck/ ไฟล์นี้เป็นจุดเข้าของ CLI และคงชื่อเดิมไว้ให้ gui.py ใช้ต่อได้
"""
from storagecheck.cleanup import cache_candidates
from storagecheck.config import HOME, SNAP_DIR, load_settings, save_settings
from storagecheck.duplicates import find_duplicates, find_folder_duplicates, keeper
from storagecheck.history import clear_last_scan, diff_data, list_snapshots, load_last_scan, mode_report, save_last_scan
from storagecheck.safety import classify, is_never, move_to_trash
from storagecheck.tools import brew_upgrade, mode_brew_upgrade, mode_tools
from storagecheck.walk import cached_rows, clear_index, dir_size, scan
from storagecheck.cli import main

if __name__ == "__main__":
    main()
