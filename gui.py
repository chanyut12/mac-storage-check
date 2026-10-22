#!/usr/bin/env python3
"""GUI ของ storage check

รันด้วย `python3 gui.py` แล้วเปิดในเบราว์เซอร์ที่ http://127.0.0.1:8765
หน้าเว็บอยู่ในโฟลเดอร์ static/ (HTML, CSS, JS แยกไฟล์) ส่วนนี้ทำหน้าที่เป็น API ที่เรียกฟังก์ชันจาก scan.py
เซิร์ฟเวอร์รับคำขอเฉพาะจากเครื่องนี้ (127.0.0.1)
"""
import contextlib
import io
import json
import os
import shutil
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import scan
from storagecheck.i18n import set_lang, tr
from storagecheck.platforms import disk_bytes, is_link_path, reveal

PORT = int(os.environ.get("STORAGECHECK_PORT", "8765"))
STATIC_DIR = Path(__file__).resolve().parent / "static"
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8"}
LOCK = threading.Lock()          # ทำงานทีละงาน เพราะ scan.py พิมพ์ผลลง stdout


def capture(fn, *args):
    """รันฟังก์ชันของ scan.py แล้วเก็บผลที่พิมพ์ไว้คืนเป็นข้อความ"""
    buf = io.StringIO()
    with LOCK, contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


class ApiError(Exception):
    """ข้อผิดพลาดที่ผู้ใช้ควรเห็น: เก็บรหัสข้อความและตัวแปร แปลตามภาษาของคำขอตอนตอบกลับ"""

    def __init__(self, code, **vars):
        super().__init__(code)
        self.code = code
        self.vars = vars


def fail(code, **vars):
    """ผลล้มเหลวมาตรฐาน: รหัส ตัวแปร และข้อความที่แปลแล้ว (ใส่ทั้ง message และ output ที่หน้าเว็บเดิมอ่าน)"""
    text = tr(code, **vars)
    return {"ok": False, "code": code, "vars": vars, "message": text, "output": text}


def capture_result(fn, *args):
    """เหมือน capture แต่คืน (ค่าที่ฟังก์ชันคืนมา, ข้อความที่พิมพ์)"""
    buf = io.StringIO()
    with LOCK, contextlib.redirect_stdout(buf):
        result = fn(*args)
    return result, buf.getvalue()


# รหัสประเภทไฟล์ ป้ายที่แสดงอยู่ฝั่งหน้าเว็บ (static/js/labels.js)
KIND_BY_EXT = {
    "video": {"mov", "mp4", "mkv", "avi", "m4v", "webm"},
    "archive": {"zip", "rar", "7z", "tar", "gz", "tgz", "xz", "bz2"},
    "disk_image": {"dmg", "iso", "img", "pkg"},
    "data": {"csv", "db", "sqlite", "xlsx", "xls", "json", "parquet", "pkl", "npy", "h5", "sav", "dta"},
    "ai_model": {"pt", "pth", "safetensors", "gguf", "onnx", "ckpt"},
    "document": {"pdf", "doc", "docx", "ppt", "pptx", "txt", "md", "pages", "key", "numbers"},
    "image": {"png", "jpg", "jpeg", "heic", "gif", "webp", "tiff", "raw"},
}


def kind_of(path):
    ext = Path(path).suffix.lower().lstrip(".")
    for name, exts in KIND_BY_EXT.items():
        if ext in exts:
            return name
    return "other"


def item(size, path, atime=None):
    """แถวของรายการ atime (ถ้ามี) คือเวลาที่เปิดไฟล์ครั้งล่าสุดโดยประมาณ"""
    return {"size": size, "path": path, "category": scan.classify(path),
            "locked": scan.is_never(path), "kind": kind_of(path), "last_access": atime}


def disk_now():
    total, used, free = shutil.disk_usage(scan.HOME)
    return {"total": total, "used": used, "free": free}


def api_scan(_body):
    """สแกนใหม่ทั้งหมดแล้วบันทึกเป็นผลล่าสุด"""
    atimes = {}
    with LOCK:
        rows = scan.cached_rows(refresh=True)
        files, buckets = scan.scan(atimes, rows)
    data = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "files": [item(s, p, atimes.get(p)) for s, p in sorted(files, reverse=True) if not scan.is_never(p)],
        "folders": [{"size": s, "name": k, "path": str(scan.HOME / k)}
                    for k, s in sorted(buckets.items(), key=lambda x: -x[1])[:100]],
        "cache": [item(s, str(p)) for s, p in scan.cache_candidates()],
    }
    scan.save_last_scan(data)
    return {**data, "disk": disk_now()}


def api_last(_body):
    """คืนผลสแกนล่าสุดที่บันทึกไว้ ไม่สแกนใหม่ (ใช้ตอนเปิดหน้า)"""
    data = scan.load_last_scan()
    if data is None:
        return {"scanned": False}
    return {**data, "disk": disk_now()}


def api_settings(body):
    """อ่านหรือบันทึกค่าตั้งค่า ถ้าค่าเปลี่ยนจะล้างผลสแกนที่บันทึกไว้"""
    s = scan.load_settings()
    if body:
        limits = {"min_mb": (1, 10240), "dup_min_mb": (1, 10240), "old_months": (1, 120)}
        for key, (lo, hi) in limits.items():
            if key in body:
                v = int(body[key])
                if not lo <= v <= hi:
                    raise ApiError("api.settings.range", field=tr(f"settings.field.{key}"), lo=lo, hi=hi)
                s[key] = v
        scan.save_settings(s)
        scan.clear_last_scan()
    return {**s, "home": str(scan.HOME)}


def api_exclude(body):
    """เพิ่มหรือเอาโฟลเดอร์ออกจากรายการยกเว้น (เฉพาะโฟลเดอร์ย่อยใน home)"""
    home = os.path.realpath(scan.HOME)
    path = os.path.realpath(body.get("path", ""))
    if path == home or not path.startswith(home + os.sep):
        raise ApiError("api.exclude.only_subfolders")
    entry = "~" + path[len(home):]
    s = scan.load_settings()
    if body.get("remove"):
        s["exclude"] = [x for x in s["exclude"] if x != entry]
    elif entry not in s["exclude"]:
        s["exclude"].append(entry)
    scan.save_settings(s)
    scan.clear_last_scan()
    return {**s, "home": str(scan.HOME)}


def api_report(_body):
    return {"output": capture(scan.mode_report)}


def api_snapshots(_body):
    return {"items": scan.list_snapshots()}


def api_diff(body):
    """เทียบกับ snapshot ที่เลือก (ถ้าไม่ระบุ ใช้ตัวล่าสุด) คืนเป็นโครงสร้างข้อมูล"""
    name = body.get("snapshot")
    if name and name not in {s["name"] for s in scan.list_snapshots()}:
        raise ApiError("api.snapshot.not_found")
    with LOCK:
        data = scan.diff_data(str(scan.SNAP_DIR / name) if name else None)
    if data is None:
        return fail("api.snapshot.none")
    return {"ok": True, **data}


def api_weekly(_body):
    """เทียบกับ snapshot ที่เก่ากว่า 7 วัน (ใหม่ที่สุดในกลุ่มนั้น)"""
    snap = scan.weekly_snapshot()
    if snap is None:
        return fail("api.weekly.none")
    with LOCK:
        data = scan.diff_data(str(snap))
    days = (datetime.now() - datetime.fromisoformat(data["time"])).days
    return {"ok": True, "days": days, **data}


def api_tools(body):
    return {"output": capture(scan.mode_tools, bool(body.get("apply")))}


def api_brew_upgrade(body):
    """แพ็กเกจ Homebrew ที่ล้าสมัย หรืออัปเดตเมื่อส่ง apply: true (ไม่ล็อกเซิร์ฟเวอร์ระหว่างรอ)"""
    text, count = scan.brew_upgrade(bool(body.get("apply")))
    return {"output": text, "outdated": count}


def api_cache(_body):
    return {"items": [item(s, str(p)) for s, p in scan.cache_candidates()]}


def api_children(body):
    """รายการในโฟลเดอร์หนึ่งภายใน home เรียงจากใหญ่ไปเล็ก (ไม่ตามลิงก์ออกนอก home และอ่านอย่างเดียว)"""
    home = os.path.realpath(scan.HOME)
    path = os.path.realpath(body.get("path") or home)
    if (path != home and not path.startswith(home + os.sep)) or not os.path.isdir(path):
        raise ApiError("api.browse.not_allowed")
    sizes = scan.dir_sizes()    # ใช้ดัชนีจากการสแกนล่าสุดถ้ามี จะได้ไม่ต้องเดินโฟลเดอร์ซ้ำทุกคลิก
    rows = []
    for name in os.listdir(path):
        p = os.path.join(path, name)
        if is_link_path(p):
            continue
        try:
            st = os.lstat(p)
        except OSError:
            continue
        is_dir = os.path.isdir(p)
        if not is_dir:
            size = disk_bytes(st)
        elif sizes is not None:
            size = sizes.get(p, 0)      # โฟลเดอร์ที่ถูกข้ามตาม SKIP_DIRS หรือยกเว้นจะไม่อยู่ในดัชนี
        else:
            size = scan.scanned_dir_size(p)
        rows.append({"name": name, "path": p, "size": size, "is_dir": is_dir})
    rows.sort(key=lambda r: -r["size"])
    return {"path": path, "parent": os.path.dirname(path) if path != home else None,
            "items": rows[:200], "indexed": sizes is not None}


def api_reveal(body):
    """เปิด Finder ไปที่ไฟล์หรือโฟลเดอร์นั้น (เฉพาะใน home และมีอยู่จริง)"""
    path = body.get("path", "")
    if not path.startswith(str(scan.HOME) + os.sep) or not os.path.exists(path):
        return fail("api.reveal.not_allowed")
    reveal(path)
    return {"ok": True, "output": ""}


def api_duplicates(_body):
    """คืนรายการไฟล์ซ้ำแบบแบน ทุกแถวมี group และ keep (true = ฉบับที่เก็บไว้ ย้ายไม่ได้)"""
    atimes = {}
    with LOCK:
        groups = scan.find_duplicates(atimes, scan.cached_rows())
    items = []
    for gi, (size, paths) in enumerate(groups):
        keep = scan.keeper(paths)
        items += [{**item(size, p, atimes.get(p)), "keep": p == keep, "group": gi} for p in paths]
    return {"items": items}


def api_folder_duplicates(_body):
    """โฟลเดอร์ซ้ำแบบแบน ทุกแถวมี group และ keep (true = ฉบับที่เก็บไว้ ย้ายไม่ได้)"""
    with LOCK:
        groups = scan.find_folder_duplicates(scan.cached_rows())
    items = []
    for gi, (size, paths, keep) in enumerate(groups):
        items += [{**item(size, p), "kind": "folder", "keep": p == keep, "group": gi} for p in paths]
    return {"items": items}


def api_snapshot_delete(body):
    """ย้าย snapshot หนึ่งไฟล์ไปถังขยะ (รายงาน .md/.csv ไม่ถูกลบ)"""
    name = body.get("snapshot")
    if name not in {s["name"] for s in scan.list_snapshots()}:
        raise ApiError("api.snapshot.not_found")
    ok, output = capture_result(scan.move_to_trash, [str(scan.SNAP_DIR / name)])
    return {"ok": bool(ok), "output": output}


def api_trash(body):
    paths = body.get("paths") or []
    if not paths:
        return fail("api.trash.none_selected")
    ok, output = capture_result(scan.move_to_trash, paths)
    scan.clear_index()      # ไฟล์ที่ย้ายไปแล้วต้องไม่ค้างในดัชนี
    return {"ok": bool(ok), "output": output or tr("api.trash.done")}


ROUTES = {
    "/api/scan": api_scan,
    "/api/last": api_last,
    "/api/settings": api_settings,
    "/api/exclude": api_exclude,
    "/api/report": api_report,
    "/api/snapshots": api_snapshots,
    "/api/diff": api_diff,
    "/api/folder_duplicates": api_folder_duplicates,
    "/api/tools": api_tools,
    "/api/brew_upgrade": api_brew_upgrade,
    "/api/weekly": api_weekly,
    "/api/snapshot_delete": api_snapshot_delete,
    "/api/cache": api_cache,
    "/api/trash": api_trash,
    "/api/reveal": api_reveal,
    "/api/duplicates": api_duplicates,
    "/api/children": api_children,
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            return self._serve_static("index.html")
        if self.path.startswith("/static/"):
            return self._serve_static(self.path[len("/static/"):])
        self._send(404, b"not found", "text/plain")

    def _serve_static(self, rel):
        target = (STATIC_DIR / rel).resolve()
        if not target.is_relative_to(STATIC_DIR) or not target.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = MIME.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            set_lang(body.pop("lang", None))        # ภาษาของคำขอนี้ ไม่ให้ปนเข้าไปในข้อมูลของ route
            route = ROUTES.get(self.path)
            if route is None:
                result, code = {"error": tr("error.not_found"), "code": "error.not_found", "vars": {}}, 404
            else:
                result, code = route(body), 200
        except ApiError as e:
            result, code = {"error": tr(e.code, **e.vars), "code": e.code, "vars": e.vars}, 400
        except Exception as e:  # ข้อผิดพลาดที่ไม่คาดคิด: ส่งข้อความกลาง (แปลแล้ว) ส่วนรายละเอียดอยู่ใน detail
            result, code = {"error": tr("error.internal"), "code": "error.internal", "vars": {}, "detail": str(e)}, 500
        self._send(code, json.dumps(result, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")


def main():
    set_lang(os.environ.get("STORAGECHECK_LANG"))       # ภาษาของข้อความในเทอร์มินัล (หน้าเว็บส่งภาษามากับแต่ละคำขอ)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(tr("cli.gui_open", url=url))
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n" + tr("cli.gui_closed"))
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
