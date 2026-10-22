"""ส่วนที่ผูกกับระบบปฏิบัติการ: ตอนนี้รองรับเฉพาะ macOS"""

import sys

from ..i18n import tr


if sys.platform == "darwin":
    from .macos import CACHE, NEVER, disk_bytes, is_link, is_link_path, reveal, trash
else:
    raise RuntimeError(tr("cli.unsupported_platform", name=sys.platform))
