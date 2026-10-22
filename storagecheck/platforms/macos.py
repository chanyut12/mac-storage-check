"""ส่วนของ macOS: ถังขยะผ่าน Finder, เปิดใน Finder, ขนาดที่ใช้จริงบนดิสก์ และป้ายประเภท"""

import os
import subprocess

from ..i18n import tr


# ข้อมูลที่ห้ามลบ (ตรวจทุกโหมด)
NEVER = ("/Containers/com.docker", "/Mobile Documents/", "Photos Library", "/Keychains/")

# โฟลเดอร์ cache ที่สร้างใหม่ได้
CACHE = ("/Caches/", "/.cache/", "/Logs/")


def disk_bytes(st):
    """ขนาดที่ใช้จริงบนดิสก์จาก stat (macOS เก็บเป็นบล็อก 512 ไบต์)"""
    return st.st_blocks * 512


def is_link(entry):
    """symlink จาก DirEntry โดยไม่ตามเข้าไป"""
    return entry.is_symlink()


def is_link_path(path):
    return os.path.islink(path)


def trash(paths):
    """ย้ายไปถังขยะผ่าน Finder เพื่อกู้คืนได้ (ตรวจพาธก่อนเรียกที่ safety.py)"""

    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    items = ", ".join(f'POSIX file "{esc(p)}"' for p in paths)
    script = f'tell application "Finder" to delete {{{items}}}'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        print(tr("trash.failed", error=r.stderr.strip()))
        return False
    return True


def reveal(path):
    """เปิด Finder ไปที่ไฟล์หรือโฟลเดอร์นั้น"""
    subprocess.run(["open", "-R", path], check=False)
