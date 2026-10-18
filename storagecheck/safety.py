"""ด่านป้องกันการลบ: ป้ายประเภท รายการห้ามลบ และการย้ายไปถังขยะ"""

import os
import subprocess

from .config import CACHE, HOME, NEVER


def classify(path):
    if any(k in path for k in NEVER):
        return "⛔ ห้ามลบ"
    if any(k in path for k in CACHE):
        return "🟢 cache"
    return "🟡 ตรวจก่อน"


def is_never(path):
    return any(k in path for k in NEVER)


def move_to_trash(paths):
    """ย้ายไปถังขยะผ่าน Finder เพื่อกู้คืนได้ (ปฏิเสธเส้นทางนอก home และป้าย ⛔)"""
    if not paths:
        return True
    for p in paths:
        if not p.startswith(str(HOME) + os.sep) or is_never(p) or not os.path.exists(p):
            print(f"ปฏิเสธ: {p} (อยู่นอก home, ไม่มีอยู่จริง หรืออยู่ในรายการห้ามลบ)")
            return False

    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    items = ", ".join(f'POSIX file "{esc(p)}"' for p in paths)
    script = f'tell application "Finder" to delete {{{items}}}'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode:
        print("ย้ายไปถังขยะไม่สำเร็จ:", r.stderr.strip())
        return False
    return True
