"""ด่านป้องกันการลบ: ป้ายประเภท รายการห้ามลบ และการย้ายไปถังขยะ"""

import os

from .config import HOME
from .i18n import tr
from .platforms import CACHE, NEVER, trash


CATEGORY_LABELS = {"never": "⛔ ห้ามลบ", "cache": "🟢 cache", "review": "🟡 ตรวจก่อน"}


def classify(path):
    """คืนรหัสประเภท: never (ห้ามลบ), cache (สร้างใหม่ได้), review (ตรวจก่อน)"""
    if any(k in path for k in NEVER):
        return "never"
    if any(k in path for k in CACHE):
        return "cache"
    return "review"


def category_label(code):
    """ป้ายที่แสดงให้ผู้ใช้ของรหัสประเภท"""
    return CATEGORY_LABELS[code]


def is_never(path):
    return any(k in path for k in NEVER)


def move_to_trash(paths):
    """ย้ายไปถังขยะเพื่อกู้คืนได้ (ปฏิเสธเส้นทางนอก home และป้าย ⛔ ก่อนส่งให้ระบบปฏิบัติการ)"""
    if not paths:
        return True
    for p in paths:
        if not p.startswith(str(HOME) + os.sep) or is_never(p) or not os.path.exists(p):
            print(tr("safety.refused", path=p))
            return False
    return trash(paths)
