"""หาไฟล์ซ้ำและโฟลเดอร์ซ้ำ"""

import os
import sys

from .config import HOME, SKIP_DIRS, TOP_N, dup_min_size, excluded_dirs
from .hashing import HashCache, _group_by_hash, hash_paths
from .safety import is_never, move_to_trash
from .util import gb
from .walk import file_rows


def find_duplicates(atimes=None, rows=None):
    """คืนค่า [(ขนาดต่อไฟล์, [path, ...])] ของไฟล์ที่เนื้อหาเหมือนกันทุกไบต์

    ขั้นตอน: จัดกลุ่มตามขนาด -> hash 64 KB แรก -> hash ทั้งไฟล์ เพื่อให้ขั้นที่แพงทำน้อยที่สุด
    ถ้าส่ง atimes (dict) จะเก็บ atime ไว้ก่อนการ hash จะอ่านไฟล์
    """
    print("กำลังหาไฟล์ซ้ำ... (อาจใช้เวลานาน)", file=sys.stderr)
    limit = dup_min_size()
    rows = file_rows() if rows is None else rows
    by_size, meta, seen_inodes = {}, {}, set()
    for p, size, _disk, atime, mtime, dev, ino in rows:
        if size < limit or is_never(p):
            continue
        key = (dev, ino)
        if key in seen_inodes:          # hard link ชี้ไปข้อมูลเดียวกัน ลบแล้วไม่คืนพื้นที่
            continue
        seen_inodes.add(key)
        if atimes is not None:
            atimes[p] = atime
        by_size.setdefault(size, []).append(p)
        meta[p] = (size, mtime)

    cache = HashCache()
    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        heads = hash_paths(paths, meta, True, cache)
        for same_head in _group_by_hash(paths, heads):
            if len(same_head) < 2:
                continue
            fulls = hash_paths(same_head, meta, False, cache)
            for same in _group_by_hash(same_head, fulls):
                if len(same) >= 2:
                    groups.append((size, sorted(same)))
    cache.save()
    groups.sort(key=lambda g: g[0] * (len(g[1]) - 1), reverse=True)
    return groups


def keeper(paths):
    """ฉบับที่แก้ไขล่าสุดในกลุ่มไฟล์ซ้ำ ซึ่งจะถูกเก็บไว้เสมอ"""
    return max(paths, key=os.path.getmtime)


def removal_plan(paths):
    """ฉบับอื่นทั้งหมดในกลุ่ม คือรายการที่จะย้ายไปถังขยะ"""
    keep = keeper(paths)
    return [p for p in paths if p != keep]


def _walk_files(d, excluded):
    """ไฟล์ทั้งหมดใต้โฟลเดอร์ d โดยใช้กฎการข้ามเดียวกับดัชนีไฟล์"""
    out = []
    for root, dirs, names in os.walk(d, onerror=lambda e: None):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and os.path.join(root, x) not in excluded]
        for name in names:
            p = os.path.join(root, name)
            if not os.path.islink(p):
                out.append(p)
    return out


def find_folder_duplicates(rows=None):
    """คืนค่า [(ขนาดรวมของโฟลเดอร์, [โฟลเดอร์ที่เนื้อหาเหมือนกัน], ฉบับที่เก็บไว้)]

    - โฟลเดอร์ที่มีรายการห้ามลบอยู่ข้างใน จะไม่ถูกนับ
    - รายงานเฉพาะโฟลเดอร์ระดับบนสุดของกลุ่ม โฟลเดอร์ที่อยู่ในกลุ่มซ้ำอื่นอยู่แล้วจะถูกข้าม
    - รวมค่าจากล่างขึ้นบนในรอบเดียว, คัดด้วยชื่อไฟล์และขนาดก่อน แล้วจึง hash เฉพาะที่เหลือ
    """
    print("กำลังหาโฟลเดอร์ซ้ำ... (อาจใช้เวลานานมาก)", file=sys.stderr)
    limit = dup_min_size()
    home = str(HOME)
    rows = file_rows() if rows is None else rows
    excluded = excluded_dirs()

    # ขั้นที่ 1: ค่าของไฟล์ที่อยู่ในโฟลเดอร์นั้นโดยตรง
    direct, bad_direct, meta = {}, set(), {}
    for p, fsize, _disk, _atime, fmtime, _dev, _ino in rows:
        meta[p] = (fsize, fmtime)
        d = os.path.dirname(p)
        if is_never(p):
            bad_direct.add(d)
            continue
        acc = direct.setdefault(d, [0, 0, 0.0])
        acc[0] += 1
        acc[1] += fsize
        acc[2] = max(acc[2], fmtime)

    # ขั้นที่ 2: เพิ่มโฟลเดอร์บรรพบุรุษทั้งหมด แล้วรวมค่าจากลึกที่สุดขึ้นไปหาพ่อแม่ในรอบเดียว
    dirs = set()
    for d in list(direct) + list(bad_direct):
        while d.startswith(home + os.sep) and d not in dirs:
            dirs.add(d)
            d = os.path.dirname(d)
    count, size, mtime, bad = {}, {}, {}, set()
    for d in dirs:
        count[d], size[d], mtime[d] = direct.get(d, [0, 0, 0.0])
        if d in bad_direct:
            bad.add(d)
    for d in sorted(dirs, key=lambda x: x.count(os.sep), reverse=True):
        parent = os.path.dirname(d)
        if parent not in dirs:
            continue
        count[parent] += count[d]
        size[parent] += size[d]
        mtime[parent] = max(mtime[parent], mtime[d])
        if d in bad:
            bad.add(parent)

    candidates = [d for d in dirs if d not in bad and size[d] >= limit and not is_never(d)]
    by_shape = {}
    for d in candidates:
        by_shape.setdefault((count[d], size[d]), []).append(d)

    # ขั้นที่ 3: คัดด้วยชื่อไฟล์และขนาดก่อน ถ้าไม่ตรงก็ไม่ต้อง hash
    cache = HashCache()
    fp_groups = []
    for members in by_shape.values():
        if len(members) < 2:
            continue
        lists = {d: _walk_files(d, excluded) for d in members}
        by_sig = {}
        for d in members:
            sig = tuple(sorted((os.path.relpath(p, d), meta[p][0]) for p in lists[d] if p in meta))
            by_sig.setdefault(sig, []).append(d)
        for same_sig in by_sig.values():
            if len(same_sig) < 2:
                continue
            # ขั้นที่ 4: hash เฉพาะโฟลเดอร์ที่ผ่านการคัดด้วยชื่อและขนาดแล้ว
            paths = [p for d in same_sig for p in lists[d] if p in meta]
            hashes = hash_paths(paths, meta, False, cache)
            by_fp = {}
            for d in same_sig:
                names = [p for p in lists[d] if p in meta]
                if any(p not in hashes for p in names):
                    continue
                fp = tuple(sorted((os.path.relpath(p, d), hashes[p]) for p in names))
                by_fp.setdefault(fp, []).append(d)
            fp_groups += [g for g in by_fp.values() if len(g) >= 2]
    cache.save()

    # ตัดโฟลเดอร์ที่มีบรรพบุรุษอยู่ในกลุ่มซ้ำอื่นแล้ว เพื่อไม่ให้รายงานซ้ำซ้อน
    in_groups = {d for g in fp_groups for d in g}

    def has_group_ancestor(d):
        a = os.path.dirname(d)
        while a.startswith(home + os.sep):
            if a in in_groups:
                return True
            a = os.path.dirname(a)
        return False

    out = []
    for g in fp_groups:
        top = [d for d in g if not has_group_ancestor(d)]
        if len(top) >= 2:
            keep = max(top, key=lambda d: mtime[d])
            out.append((size[top[0]], sorted(top), keep))
    out.sort(key=lambda r: r[0] * (len(r[1]) - 1), reverse=True)
    return out


def mode_duplicates(apply):
    groups = find_duplicates()
    if not groups:
        print(f"ไม่พบไฟล์ซ้ำตั้งแต่ {dup_min_size() // 1024**2} MB ขึ้นไป")
        return

    reclaim = sum(size * (len(paths) - 1) for size, paths in groups)
    print(f"\n== ไฟล์ซ้ำ {len(groups)} กลุ่ม คืนได้ราว {gb(reclaim).strip()} ==")
    for size, paths in groups[:TOP_N]:
        print(f"\n{gb(size)} x {len(paths)} ชุด (คืนได้ {gb(size * (len(paths) - 1)).strip()})")
        for p in paths:
            print(f"  {p}")
    if len(groups) > TOP_N:
        print(f"\n... และอีก {len(groups) - TOP_N} กลุ่ม")

    to_remove = [p for _, paths in groups for p in removal_plan(paths)]
    print(f"\nแผนลบ: เก็บฉบับที่แก้ไขล่าสุดในแต่ละกลุ่มไว้ ย้ายไปถังขยะ {len(to_remove)} ไฟล์")
    if not apply:
        print("[dry-run] ยังไม่ได้ย้ายอะไร ตรวจรายการด้านบน แล้วใส่ --yes เพื่อย้ายไปถังขยะ")
        return
    if move_to_trash(to_remove):
        print(f"ย้าย {len(to_remove)} ไฟล์ไปถังขยะแล้ว กู้คืนได้จากถังขยะ")
