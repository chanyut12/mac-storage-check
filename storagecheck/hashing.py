"""hash ของไฟล์ พร้อมแคชที่ใช้ซ้ำได้และการ hash แบบขนาน"""

import hashlib
import json
import os

from concurrent.futures import ThreadPoolExecutor

from .config import CACHE_DIR, HASH_CACHE_FILE, HASH_CHUNK, HASH_HEAD, HASH_WORKERS


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
