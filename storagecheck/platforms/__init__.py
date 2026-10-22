"""ส่วนที่ผูกกับระบบปฏิบัติการ: ตอนนี้รองรับเฉพาะ macOS"""

import sys


if sys.platform == "darwin":
    from .macos import CACHE, NEVER, disk_bytes, is_link, is_link_path, reveal, trash
else:
    raise RuntimeError(f"ยังไม่รองรับระบบ {sys.platform}")
