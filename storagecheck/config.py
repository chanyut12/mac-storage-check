"""ค่าตั้งค่า พาธ และค่าคงที่ของเครื่องมือ"""

import json
import os

from pathlib import Path


HOME = Path.home()


BASE = Path(__file__).resolve().parent.parent          # โฟลเดอร์ของเครื่องมือ (ข้ามตอนสแกน)


SNAP_DIR = BASE / "snapshots"


REPORT_DIR = BASE / "reports"


SETTINGS_FILE = BASE / "settings.json"


CACHE_DIR = BASE / "cache"


LAST_SCAN = CACHE_DIR / "last_scan.json"


HASH_CACHE_FILE = CACHE_DIR / "hash_cache.json"


HASH_WORKERS = 4                  # จำนวนไฟล์ที่ hash พร้อมกัน (งานอ่านดิสก์)


DEFAULT_SETTINGS = {"min_mb": 100, "dup_min_mb": 10, "old_months": 12, "exclude": []}


HASH_HEAD = 64 * 1024             # ขั้นแรกของการหาไฟล์ซ้ำ: hash แค่ 64 KB แรก


HASH_CHUNK = 1024**2              # ขั้นที่สอง: hash ทั้งไฟล์เป็นก้อนละ 1 MB


TOP_N = 30


SKIP_DIRS = {".git", "node_modules", ".venv", "venv"}


def load_settings():
    """ค่าตั้งค่าจาก settings.json รวมกับค่าเริ่มต้น (ไฟล์เสียหายจะใช้ค่าเริ่มต้น)"""
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return s


def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def min_size():
    return int(load_settings()["min_mb"]) * 1024**2


def dup_min_size():
    return int(load_settings()["dup_min_mb"]) * 1024**2


def excluded_dirs():
    """โฟลเดอร์ที่ผู้ใช้ยกเว้นจากการสแกน เก็บเป็น ~/... ในไฟล์ตั้งค่า (~ คือ HOME)"""
    return {os.path.normpath(str(HOME) + x[1:]) for x in load_settings()["exclude"] if x.startswith("~")}
