"""เดินไฟล์ในโฮม ดัชนีไฟล์ที่ใช้ร่วมกัน และการสแกนหาไฟล์ใหญ่"""

import os
import sys

from pathlib import Path

from .config import BASE, HOME, SKIP_DIRS, excluded_dirs, load_settings, min_size
from .i18n import tr
from .platforms import disk_bytes, is_link


def dir_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path, onerror=lambda e: None):
        for name in filenames:
            p = os.path.join(dirpath, name)
            if os.path.islink(p):
                continue
            try:
                total += disk_bytes(os.lstat(p))
            except OSError:
                pass
    return total


def scanned_dir_size(path):
    """ขนาดโฟลเดอร์ตามกฎเดียวกับดัชนี: ข้าม SKIP_DIRS โฟลเดอร์ที่ยกเว้น และ symlink"""
    excluded = excluded_dirs()
    total = 0
    stack = [path]
    while stack:
        dirpath = stack.pop()
        try:
            with os.scandir(dirpath) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            try:
                if is_link(e):
                    continue
                if e.is_dir(follow_symlinks=False):
                    if e.name not in SKIP_DIRS and e.path not in excluded:
                        stack.append(e.path)
                else:
                    total += disk_bytes(e.stat(follow_symlinks=False))
            except OSError:
                continue
    return total


def iter_files():
    """เดินไฟล์ทั้ง home คืนค่า (path, lstat) ข้ามโฟลเดอร์ของเครื่องมือ SKIP_DIRS และ symlink"""
    base = str(BASE)
    excluded = excluded_dirs()
    stack = [str(HOME)]
    while stack:
        dirpath = stack.pop()
        if dirpath == base or dirpath.startswith(base + os.sep) or dirpath in excluded:
            continue
        try:
            with os.scandir(dirpath) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            try:
                if is_link(e):
                    continue
                if e.is_dir(follow_symlinks=False):
                    if e.name not in SKIP_DIRS and e.path not in excluded:
                        stack.append(e.path)
                else:
                    yield e.path, e.stat(follow_symlinks=False)
            except OSError:
                continue


def file_rows():
    """เดินไฟล์ทั้ง home แล้วเก็บเฉพาะค่าที่ใช้ต่อ:
    (path, ขนาดจริง, ขนาดที่ใช้บนดิสก์, atime, mtime, dev, inode)
    atime ต้องเก็บตอนนี้ ก่อนการ hash จะอ่านไฟล์และเปลี่ยนค่า
    """
    return [(p, st.st_size, disk_bytes(st), st.st_atime, st.st_mtime, st.st_dev, st.st_ino)
            for p, st in iter_files()]


# ดัชนีไฟล์ที่เดินแล้วเก็บไว้ในหน่วยความจำ ใช้ร่วมกันระหว่างการกดปุ่มต่าง ๆ ในหน้าเว็บ
_index = {"key": None, "rows": None}


def _index_key():
    s = load_settings()
    return (s["min_mb"], s["dup_min_mb"], tuple(s["exclude"]))


def cached_rows(refresh=False):
    """คืนดัชนีไฟล์ เดินใหม่เมื่อสั่ง refresh, ยังไม่มีดัชนี, หรือการตั้งค่าเปลี่ยน"""
    key = _index_key()
    if refresh or _index["rows"] is None or _index["key"] != key:
        _index["rows"] = file_rows()
        _index["key"] = key
    return _index["rows"]


def clear_index():
    """ล้างดัชนี ใช้หลังมีไฟล์ถูกย้ายไปถังขยะ เพื่อไม่ให้ดัชนีค้างข้อมูลเก่า"""
    _index["rows"] = None


_dir_sizes = {"rows": None, "sizes": None}


def dir_sizes():
    """ขนาดรวมของทุกโฟลเดอร์ย่อยใน home จากดัชนีล่าสุด คำนวณครั้งเดียวต่อดัชนี
    คืน None ถ้ายังไม่มีดัชนี (ผู้เรียกต้องเดินโฟลเดอร์เองแทน)"""
    rows = _index["rows"]
    if rows is None:
        return None
    if _dir_sizes["rows"] is not rows:
        home = str(HOME)
        sizes = {}
        for row in rows:
            d = os.path.dirname(row[0])
            while d.startswith(home + os.sep):
                sizes[d] = sizes.get(d, 0) + row[2]
                d = os.path.dirname(d)
        _dir_sizes["rows"] = rows
        _dir_sizes["sizes"] = sizes
    return _dir_sizes["sizes"]


def scan(atimes=None, rows=None):
    """คืนค่า (รายการไฟล์ใหญ่ [(size, path)], ขนาดรวมต่อโฟลเดอร์ {key: size})

    ถ้าส่ง atimes (dict) จะเก็บ atime ของไฟล์ใหญ่ไว้ตอนสแกน ก่อนที่การ hash จะเปลี่ยนค่า
    ถ้าส่ง rows (จาก file_rows/cached_rows) จะไม่เดินโฟลเดอร์ซ้ำอีก
    """
    print(tr("cli.scanning"), file=sys.stderr)
    limit = min_size()
    rows = file_rows() if rows is None else rows
    files, buckets = [], {}
    for p, _size, disk, atime, _mtime, _dev, _ino in rows:
        rel = Path(p).relative_to(HOME).parts
        key = "/".join(rel[:2]) if len(rel) > 1 else rel[0]
        buckets[key] = buckets.get(key, 0) + disk
        if disk >= limit:
            files.append((disk, p))
            if atimes is not None:
                atimes[p] = atime
    return files, buckets
