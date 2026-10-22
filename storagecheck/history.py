"""ผลสแกนล่าสุด, snapshot, รายงาน และการเทียบ snapshot"""

import csv
import json
import shutil

from datetime import datetime, timedelta
from pathlib import Path

from .config import CACHE_DIR, HOME, LAST_SCAN, REPORT_DIR, SNAP_DIR, TOP_N, min_size
from .i18n import tr
from .safety import category_label, classify
from .util import gb
from .walk import scan


# ผลสแกนที่บันทึกก่อนใช้รหัสเก็บป้ายเป็นข้อความไทย แปลงเป็นรหัสตอนโหลด
OLD_CATEGORY = {"⛔ ห้ามลบ": "never", "🟢 cache": "cache", "🟡 ตรวจก่อน": "review"}
OLD_KIND = {"วิดีโอ": "video", "ไฟล์บีบอัด": "archive", "disk image": "disk_image", "ข้อมูล": "data",
            "โมเดล AI": "ai_model", "เอกสาร": "document", "รูปภาพ": "image", "โฟลเดอร์": "folder",
            "อื่น ๆ": "other"}


def save_last_scan(data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SCAN.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_last_scan():
    if not LAST_SCAN.exists():
        return None
    try:
        data = json.loads(LAST_SCAN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for key in ("files", "cache"):
        for x in data.get(key, []):
            x["category"] = OLD_CATEGORY.get(x.get("category"), x.get("category"))
            x["kind"] = OLD_KIND.get(x.get("kind"), x.get("kind"))
    return data


def clear_last_scan():
    LAST_SCAN.unlink(missing_ok=True)


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
        tr("report.used", used=gb(used).strip(), total=gb(total).strip(), free=gb(free).strip()),
        tr("report.files_over", min=min_size() // 1024**2, n=len(files)),
        "",
        tr("report.top_files", n=TOP_N),
        "",
        tr("report.table_files"),
        "|---:|---|---|",
    ]
    for size, p in sorted_files[:TOP_N]:
        lines.append(f"| {gb(size).strip()} | {category_label(classify(p))} | `{p.replace('|', chr(92) + '|')}` |")
    lines += ["", tr("report.top_folders", n=TOP_N), "", tr("report.table_folders"), "|---:|---|"]
    for key, size in sorted_buckets[:TOP_N]:
        lines.append(f"| {gb(size).strip()} | `{key}` |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["size_bytes", "category", "path"])
        for size, p in sorted_files:
            w.writerow([size, category_label(classify(p)), p])

    print(tr("report.saved", md=md_path, csv=csv_path, snap=snap))


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


def weekly_snapshot(days=7):
    """snapshot ที่ใหม่ที่สุดในบรรดาที่มีอายุอย่างน้อย days วัน หรือ None ถ้าไม่มี"""
    cutoff = datetime.now() - timedelta(days=days)
    for s in list_snapshots():  # เรียงจากใหม่ไปเก่า
        if datetime.fromisoformat(s["time"]) <= cutoff:
            return SNAP_DIR / s["name"]
    return None


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
        print(tr("cli.diff_no_snapshot"))
        return
    limit_mb = min_size() // 1024**2
    print("\n" + tr("cli.diff_compared", time=data["time"]))

    print("\n" + tr("cli.diff_grown"))
    for row in data["grown"]:
        print(f"+{gb(row['delta'])}  {row['name']}")
    print("\n" + tr("cli.diff_shrunk"))
    for row in data["shrunk"]:
        print(f"{gb(row['delta'])}  {row['name']}")

    added = data["added"]
    print("\n" + tr("cli.diff_added", shown=min(15, data["added_total"]), total=data["added_total"]))
    for row in added[:15]:
        print(f"{gb(row['size'])}  {category_label(classify(row['path'])):10}  {row['path']}")
    print("\n" + tr("cli.diff_removed", min=limit_mb, n=data["removed"]))
    print("\n" + tr("cli.diff_note"))
