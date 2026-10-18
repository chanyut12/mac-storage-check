#!/usr/bin/env python3
"""เครื่องมือตรวจพื้นที่ดิสก์ macOS

โหมดที่มี
  scan          แสดงไฟล์และโฟลเดอร์ใหญ่สุด (อ่านอย่างเดียว)
  report        บันทึกรายงาน .md / .csv และ snapshot ไว้เทียบในภายหลัง (อ่านอย่างเดียว)
  diff          เทียบกับ snapshot ล่าสุด ดูว่าอะไรโตขึ้น (อ่านอย่างเดียว)
  tools         ดู/เคลียร์ cache ของ Docker, Homebrew, conda, pnpm (dry-run ถ้าไม่ใส่ --yes)
  clean-cache   ย้าย cache ใน ~/Library/Caches และ ~/.cache ไปถังขยะ (dry-run ถ้าไม่ใส่ --yes)
  interactive   เลือกไฟล์ทีละรายการแล้วย้ายไปถังขยะ (ยืนยันก่อนเสมอ)
  duplicates    หาไฟล์ที่เนื้อหาเหมือนกัน (dry-run ถ้าไม่ใส่ --yes; --yes เก็บฉบับที่แก้ไขล่าสุดไว้)
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HOME = Path.home()
BASE = Path(__file__).resolve().parent          # โฟลเดอร์ของเครื่องมือ (ข้ามตอนสแกน)
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

# ข้อมูลที่ห้ามลบ (ตรวจทุกโหมด)
NEVER = ("/Containers/com.docker", "/Mobile Documents/", "Photos Library", "/Keychains/")
# โฟลเดอร์ cache ที่สร้างใหม่ได้
CACHE = ("/Caches/", "/.cache/", "/Logs/")


# ---------- ช่วยเหลือทั่วไป ----------

def gb(n):
    return f"{n / 1024**3:6.2f} GB"


def classify(path):
    if any(k in path for k in NEVER):
        return "⛔ ห้ามลบ"
    if any(k in path for k in CACHE):
        return "🟢 cache"
    return "🟡 ตรวจก่อน"


def is_never(path):
    return any(k in path for k in NEVER)


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
    return {str(HOME) + x[1:] for x in load_settings()["exclude"] if x.startswith("~")}


def dir_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path, onerror=lambda e: None):
        for name in filenames:
            p = os.path.join(dirpath, name)
            if os.path.islink(p):
                continue
            try:
                total += os.lstat(p).st_blocks * 512
            except OSError:
                pass
    return total


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


# ---------- การสแกน ----------

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
                if e.is_symlink():
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
    return [(p, st.st_size, st.st_blocks * 512, st.st_atime, st.st_mtime, st.st_dev, st.st_ino)
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


def scan(atimes=None, rows=None):
    """คืนค่า (รายการไฟล์ใหญ่ [(size, path)], ขนาดรวมต่อโฟลเดอร์ {key: size})

    ถ้าส่ง atimes (dict) จะเก็บ atime ของไฟล์ใหญ่ไว้ตอนสแกน ก่อนที่การ hash จะเปลี่ยนค่า
    ถ้าส่ง rows (จาก file_rows/cached_rows) จะไม่เดินโฟลเดอร์ซ้ำอีก
    """
    print("กำลังสแกน... (อาจใช้เวลาหลายนาที)", file=sys.stderr)
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


# ---------- แคชผลสแกนล่าสุด ----------

def save_last_scan(data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SCAN.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_last_scan():
    if not LAST_SCAN.exists():
        return None
    try:
        return json.loads(LAST_SCAN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def clear_last_scan():
    LAST_SCAN.unlink(missing_ok=True)


# ---------- snapshot ----------

def save_snapshot(files, buckets):
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    data = {
        "time": now.isoformat(timespec="seconds"),
        "buckets": buckets,
        "files": {p: s for s, p in files},
    }
    path = SNAP_DIR / (now.strftime("%Y%m%d_%H%M%S") + ".json")
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def latest_snapshot():
    if not SNAP_DIR.exists():
        return None
    snaps = sorted(SNAP_DIR.glob("*.json"))
    return snaps[-1] if snaps else None


# ---------- โหมด ----------

def mode_scan():
    files, buckets = scan()
    print(f"\n== ไฟล์ใหญ่สุด {TOP_N} อันดับ ==")
    for size, p in sorted(files, reverse=True)[:TOP_N]:
        print(f"{gb(size)}  {classify(p):10}  {p}")
    print(f"\n== โฟลเดอร์ใหญ่สุด {TOP_N} อันดับ ==")
    for key, size in sorted(buckets.items(), key=lambda x: -x[1])[:TOP_N]:
        print(f"{gb(size)}  {key}")


def mode_report():
    files, buckets = scan()
    snap = save_snapshot(files, buckets)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = REPORT_DIR / f"report_{stamp}.md"
    csv_path = REPORT_DIR / f"report_{stamp}.csv"

    total, used, free = shutil.disk_usage(HOME)
    sorted_files = sorted(files, reverse=True)
    sorted_buckets = sorted(buckets.items(), key=lambda x: -x[1])

    lines = [
        f"# Storage report {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- ใช้ไป: {gb(used).strip()} / ทั้งหมด {gb(total).strip()} (ว่าง {gb(free).strip()})",
        f"- ไฟล์ตั้งแต่ {min_size() // 1024**2} MB: {len(files)} ไฟล์",
        "",
        f"## ไฟล์ใหญ่สุด {TOP_N} อันดับ",
        "",
        "| ขนาด | ประเภท | ไฟล์ |",
        "|---:|---|---|",
    ]
    for size, p in sorted_files[:TOP_N]:
        lines.append(f"| {gb(size).strip()} | {classify(p)} | `{p.replace('|', chr(92) + '|')}` |")
    lines += ["", f"## โฟลเดอร์ใหญ่สุด {TOP_N} อันดับ", "", "| ขนาด | โฟลเดอร์ |", "|---:|---|"]
    for key, size in sorted_buckets[:TOP_N]:
        lines.append(f"| {gb(size).strip()} | `{key}` |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["size_bytes", "category", "path"])
        for size, p in sorted_files:
            w.writerow([size, classify(p), p])

    print(f"บันทึกรายงานแล้ว:\n  {md_path}\n  {csv_path}\n  snapshot: {snap}")


def list_snapshots():
    """รายการ snapshot ที่มี เรียงจากใหม่ไปเก่า"""
    if not SNAP_DIR.exists():
        return []
    out = []
    for p in sorted(SNAP_DIR.glob("*.json"), reverse=True):
        try:
            t = datetime.strptime(p.stem, "%Y%m%d_%H%M%S").isoformat(timespec="seconds")
        except ValueError:
            continue
        out.append({"name": p.name, "time": t})
    return out


def diff_data(snap_path=None):
    """เทียบกับ snapshot (ค่าเริ่มต้นคือล่าสุด) คืนค่าโครงสร้างข้อมูล หรือ None ถ้าไม่มี snapshot"""
    snap = Path(snap_path) if snap_path else latest_snapshot()
    if snap is None:
        return None
    old = json.loads(snap.read_text(encoding="utf-8"))
    files, buckets = scan()
    new_files = {p: s for s, p in files}

    delta = []
    for key in set(old["buckets"]) | set(buckets):
        d = buckets.get(key, 0) - old["buckets"].get(key, 0)
        if d:
            delta.append((d, key))
    delta.sort(reverse=True)

    added = sorted(((s, p) for p, s in new_files.items() if p not in old["files"]), reverse=True)
    removed = sum(1 for p in old["files"] if p not in new_files)
    return {
        "time": old["time"],
        "grown": [{"name": k, "delta": d} for d, k in delta if d > 0][:15],
        "shrunk": [{"name": k, "delta": d} for d, k in delta[::-1] if d < 0][:5],
        "added": [{"size": s, "path": p} for s, p in added[:50]],
        "added_total": len(added),
        "removed": removed,
    }


def mode_diff():
    data = diff_data()
    if data is None:
        print("ยังไม่มี snapshot ให้รัน `python3 scan.py report` ก่อนเพื่อสร้างจุดเปรียบเทียบ")
        return
    limit_mb = min_size() // 1024**2
    print(f"\nเทียบกับ snapshot: {data['time']}")

    print(f"\n== โฟลเดอร์ที่โตขึ้นมากสุด ==")
    for row in data["grown"]:
        print(f"+{gb(row['delta'])}  {row['name']}")
    print(f"\n== โฟลเดอร์ที่เล็กลงมากสุด ==")
    for row in data["shrunk"]:
        print(f"{gb(row['delta'])}  {row['name']}")

    added = data["added"]
    print(f"\n== ไฟล์ใหญ่ใหม่ (ไม่มีใน snapshot เดิม) {min(15, data['added_total'])} จาก {data['added_total']} ==")
    for row in added[:15]:
        print(f"{gb(row['size'])}  {classify(row['path']):10}  {row['path']}")
    print(f"\nไฟล์ที่หายไป (ใหญ่กว่า {limit_mb} MB): {data['removed']} ไฟล์")
    print("\nหมายเหตุ: diff ไม่ได้บันทึก snapshot ใหม่ ถ้าต้องการจุดเทียบใหม่ให้รัน report")


def file_hash(path, head_only=False):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if head_only:
            h.update(f.read(HASH_HEAD))
        else:
            for chunk in iter(lambda: f.read(HASH_CHUNK), b""):
                h.update(chunk)
    return h.hexdigest()


class HashCache:
    """เก็บ hash ไว้ในไฟล์ JSON ใช้ซ้ำได้ตราบใดที่ขนาดและ mtime ของไฟล์ยังเหมือนเดิม

    บันทึกเฉพาะไฟล์ที่ถูกใช้ในรอบนั้น จึงไม่โตไม่จำกัดและไฟล์ที่ถูกลบจะหายไปเอง
    """

    def __init__(self):
        try:
            self.old = json.loads(HASH_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.old = {}
        self.new = {}

    def get(self, path, size, mtime, kind):
        e = self.old.get(path)
        if e and e.get("size") == size and e.get("mtime") == mtime and kind in e:
            self.new[path] = e
            return e[kind]
        return None

    def put(self, path, size, mtime, kind, sha):
        e = self.new.get(path)
        if e is None or e.get("size") != size or e.get("mtime") != mtime:
            old = self.old.get(path, {})
            same = old.get("size") == size and old.get("mtime") == mtime
            e = dict(old) if same else {"size": size, "mtime": mtime}
            self.new[path] = e
        e[kind] = sha

    def save(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = HASH_CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.new, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, HASH_CACHE_FILE)


def _sha_or_none(path, head_only):
    try:
        return file_hash(path, head_only)
    except OSError:
        return None


def hash_paths(paths, meta, head_only, cache):
    """คืน {path: sha256} ของไฟล์ที่อ่านได้ ใช้ cache กับไฟล์ที่ไม่เปลี่ยน และ hash ที่เหลือแบบขนาน

    meta = {path: (ขนาด, mtime)} ซึ่งมาจากดัชนีไฟล์
    """
    kind = "head" if head_only else "full"
    out, todo = {}, []
    for p in paths:
        size, mtime = meta[p]
        sha = cache.get(p, size, mtime, kind)
        if sha is None:
            todo.append(p)
        else:
            out[p] = sha
    if todo:
        with ThreadPoolExecutor(max_workers=HASH_WORKERS) as ex:
            results = list(ex.map(lambda q: _sha_or_none(q, head_only), todo))
        for p, sha in zip(todo, results):
            if sha is not None:
                out[p] = sha
                size, mtime = meta[p]
                cache.put(p, size, mtime, kind, sha)
    return out


def _group_by_hash(paths, hashes):
    groups = {}
    for p in paths:
        if p in hashes:
            groups.setdefault(hashes[p], []).append(p)
    return groups.values()


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


TOOLS = [
    # (ชื่อ, คำสั่งที่ต้องมี, คำสั่งทำความสะอาด, คำสั่งแสดงข้อมูล หรือ None)
    ("Docker: build cache", "docker", ["docker", "builder", "prune", "-f"], ["docker", "system", "df"]),
    ("Docker: image ที่ไม่มีแท็ก (dangling)", "docker", ["docker", "image", "prune", "-f"], None),
    ("Homebrew: cache เก่า", "brew", ["brew", "cleanup", "-s"], ["brew", "cleanup", "-n"]),
    ("conda: package cache", "conda", ["conda", "clean", "--all", "-y"], None),
    ("pnpm: store ที่ไม่ได้ใช้", "pnpm", ["pnpm", "store", "prune"], None),
]


EXTRA_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/anaconda3/bin"]


def find_binary(name):
    """หาคำสั่งจาก PATH ก่อน แล้วค่อยดูตำแหน่งติดตั้งทั่วไป"""
    found = shutil.which(name)
    if found:
        return found
    for d in EXTRA_BIN_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def run_cmd(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def mode_tools(apply):
    for label, binary, clean_cmd, info_cmd in TOOLS:
        print(f"\n== {label} ==")
        exe = find_binary(binary)
        if not exe:
            print(f"ไม่พบคำสั่ง {binary} ข้าม")
            continue
        clean_cmd = [exe] + clean_cmd[1:]
        if info_cmd:
            info_cmd = [exe] + info_cmd[1:]
        if binary == "docker":
            code, _ = run_cmd([exe, "info"])
            if code:
                print("Docker ไม่ได้รันอยู่ ข้าม")
                continue
        if info_cmd:
            _, out = run_cmd(info_cmd)
            print(out[:1500])
        if not apply:
            print(f"[dry-run] จะรัน: {' '.join(clean_cmd)}")
            continue
        code, out = run_cmd(clean_cmd)
        print(out[-800:] if out else "(ไม่มีผลลัพธ์)")
        print("สำเร็จ" if code == 0 else f"ไม่สำเร็จ (exit {code})")

    ollama = find_binary("ollama")
    if ollama:
        print("\n== ollama ==")
        _, out = run_cmd([ollama, "list"])
        print(out)
        print("(เครื่องมือนี้ไม่ลบโมเดลของ ollama ให้ใช้ `ollama rm <ชื่อ>` เอง)")


def cache_candidates():
    """โฟลเดอร์ cache ใน home ที่ใหญ่กว่าเกณฑ์ขนาด เรียงจากใหญ่ไปเล็ก"""
    roots = [HOME / "Library" / "Caches", HOME / ".cache"]
    limit = min_size()
    items = []
    for root in roots:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir() and not child.is_symlink() and not is_never(str(child)):
                size = dir_size(child)
                if size >= limit:
                    items.append((size, child))
    items.sort(reverse=True)
    return items


def mode_clean_cache(apply):
    items = cache_candidates()

    total = sum(s for s, _ in items)
    print(f"\n== cache ที่มีขนาดตั้งแต่ {min_size() // 1024**2} MB: {len(items)} รายการ รวม {gb(total).strip()} ==")
    for size, p in items[:TOP_N]:
        print(f"{gb(size)}  {p}")

    if not apply:
        print("\n[dry-run] ยังไม่ได้ย้ายอะไร ใส่ --yes เพื่อย้ายไปถังขยะ")
        return
    if not items:
        return
    ok = move_to_trash([str(p) for _, p in items])
    if ok:
        print(f"\nย้าย {len(items)} รายการไปถังขยะแล้ว (รวม {gb(total).strip()})")


def mode_interactive():
    files, _ = scan()
    candidates = [(s, p) for s, p in sorted(files, reverse=True) if not is_never(p)][:TOP_N]
    if not candidates:
        print("ไม่มีไฟล์ให้เลือก")
        return

    print(f"\n== ไฟล์ที่เลือกได้ (ไม่รวมป้าย ⛔) ==")
    for i, (size, p) in enumerate(candidates, 1):
        print(f"{i:3}. {gb(size)}  {classify(p):10}  {p}")

    raw = input("\nเลือกหมายเลข (คั่นด้วย , เช่น 1,3,5) หรือ Enter เพื่อยกเลิก: ").strip()
    if not raw:
        print("ยกเลิกแล้ว")
        return
    try:
        picks = sorted({int(x) for x in raw.split(",") if x.strip()})
    except ValueError:
        print("รูปแบบไม่ถูกต้อง ยกเลิก")
        return
    if any(i < 1 or i > len(candidates) for i in picks):
        print("มีหมายเลขเกินช่วง ยกเลิก")
        return

    chosen = [candidates[i - 1] for i in picks]
    total = sum(s for s, _ in chosen)
    print(f"\nจะย้ายไปถังขยะ {len(chosen)} ไฟล์ รวม {gb(total).strip()}")
    if input("ยืนยัน? (y/N): ").strip().lower() != "y":
        print("ยกเลิกแล้ว")
        return
    if move_to_trash([p for _, p in chosen]):
        print("ย้ายไปถังขยะแล้ว กู้คืนได้จากถังขยะ")


def main():
    ap = argparse.ArgumentParser(description="เครื่องมือตรวจพื้นที่ดิสก์ macOS")
    ap.add_argument(
        "mode",
        nargs="?",
        default="scan",
        choices=["scan", "report", "diff", "tools", "clean-cache", "interactive", "duplicates"],
    )
    ap.add_argument("--yes", action="store_true", help="ทำจริง (ค่าเริ่มต้นคือแสดงอย่างเดียว)")
    args = ap.parse_args()

    if args.mode == "scan":
        mode_scan()
    elif args.mode == "report":
        mode_report()
    elif args.mode == "diff":
        mode_diff()
    elif args.mode == "tools":
        mode_tools(args.yes)
    elif args.mode == "clean-cache":
        mode_clean_cache(args.yes)
    elif args.mode == "interactive":
        mode_interactive()
    elif args.mode == "duplicates":
        mode_duplicates(args.yes)


if __name__ == "__main__":
    main()
