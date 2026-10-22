"""ตรวจระบบแปลภาษา: คีย์ครบทั้งสองภาษา โค้ดเรียกใช้เฉพาะคีย์ที่มีจริง และไม่มีอักษรไทยหลงในไฟล์ UI

รัน: python3 -m unittest discover tests
"""

import ast
import json
import re
import sys
import unittest

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

STATIC = BASE / "static"
LOCALES = STATIC / "locales"
THAI = re.compile(r"[฀-๿]")

# i18n.js เก็บข้อความฉุกเฉินไว้เองเผื่อโหลดพจนานุกรมไม่ได้ จึงไม่นับเป็นข้อความที่หลงมา
THAI_ALLOWED = {STATIC / "js" / "i18n.js"}
# ชื่อคีย์ที่ประกอบตอนทำงาน (kind.<รหัส>, category.<รหัส>, settings.field.<ชื่อ>) ไม่มีให้ค้นหาเป็นสตริงตรง ๆ
DYNAMIC_PREFIXES = ("kind.", "category.", "settings.field.")
# คีย์ที่ฝั่ง Python อ้างถึงโดยไม่ได้เรียก tr("...") ตรง ๆ เช่นเก็บชื่อคีย์ไว้ในตาราง TOOLS
PY_KEY_PREFIXES = ("cli.", "report.", "category.", "safety.", "api.", "trash.", "error.")


def load(lang):
    return json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


def strip_js_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?<![:\w\"'])//.*$", "", src, flags=re.M)


def js_files():
    return sorted((STATIC / "js").glob("*.js"))


def keys_used_in_web():
    keys = set()
    for p in js_files():
        src = strip_js_comments(p.read_text(encoding="utf-8"))
        keys |= set(re.findall(r"\bt\(\s*[\"']([\w.]+)[\"']", src))
        for call in re.findall(r"groupSheet\(([^)]*)\)", src):      # คีย์ที่ส่งเป็นอาร์กิวเมนต์
            keys |= {k for k in re.findall(r"[\"']([a-z]\w*(?:\.\w+)+)[\"']", call)}
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    keys |= set(re.findall(r"data-i18n(?:-[\w-]+)?=\"([\w.]+)\"", html))
    return keys


def python_files():
    return sorted(BASE.glob("*.py")) + sorted((BASE / "storagecheck").rglob("*.py"))


def keys_used_in_python():
    keys = set()
    for p in python_files():
        src = p.read_text(encoding="utf-8")
        keys |= set(re.findall(r"\b(?:tr|ApiError|fail)\(\s*[\"']([\w.]+)[\"']", src))
        keys |= {s for s in re.findall(r"[\"']([a-z_]+(?:\.\w+)+)[\"']", src) if s.startswith(PY_KEY_PREFIXES)}
    return keys


class LocaleFiles(unittest.TestCase):
    def test_same_keys_in_both_languages(self):
        th, en = load("th"), load("en")
        # ".one" คือรูปเอกพจน์ของภาษาอังกฤษ ภาษาไทยไม่แยกรูป
        en_keys = {k for k in en if not k.endswith(".one")}
        self.assertEqual(set(th) - en_keys, set(), "มีในไทยแต่ไม่มีในอังกฤษ")
        self.assertEqual(en_keys - set(th), set(), "มีในอังกฤษแต่ไม่มีในไทย")

    def test_one_forms_have_a_base_key(self):
        en = load("en")
        orphans = {k for k in en if k.endswith(".one") and k[:-4] not in en}
        self.assertEqual(orphans, set())

    def test_placeholders_match(self):
        th, en = load("th"), load("en")
        ph = lambda s: set(re.findall(r"\{(\w+)\}", s))
        for k in th:
            if k in en:
                self.assertEqual(ph(th[k]), ph(en[k]), f"ตัวแปรในข้อความไม่ตรงกัน: {k}")

    def test_english_has_no_thai(self):
        bad = [k for k, v in load("en").items() if THAI.search(v)]
        self.assertEqual(bad, [])


class CodeUsesKnownKeys(unittest.TestCase):
    def test_keys_used_by_web_exist(self):
        th = load("th")
        builtin = {"err.connect", "err.not_json", "err.hint", "err.generic"}     # อยู่ใน i18n.js
        missing = {k for k in keys_used_in_web() if k not in th and k not in builtin}
        self.assertEqual(missing, set())

    def test_keys_used_by_python_exist(self):
        th = load("th")
        missing = {k for k in keys_used_in_python() if k not in th}
        self.assertEqual(missing, set())

    def test_kind_and_field_keys_exist(self):
        import gui
        th = load("th")
        codes = set(gui.KIND_BY_EXT) | {"other", "folder"}
        self.assertEqual({f"kind.{c}" for c in codes} - set(th), set())
        self.assertEqual({f"settings.field.{k}" for k in ("min_mb", "dup_min_mb", "old_months")} - set(th), set())

    def test_no_unused_keys(self):
        # นับสตริงลิเทอรัลที่ตรงกับชื่อคีย์ด้วย เพราะบางที่เลือกคีย์ด้วยเงื่อนไข เช่น t(ok ? "a" : "b")
        literals = set()
        for p in js_files():
            literals |= set(re.findall(r"[\"']([\w.]+)[\"']", strip_js_comments(p.read_text(encoding="utf-8"))))
        used = keys_used_in_web() | keys_used_in_python() | literals
        unused = {k for k in load("th") if k not in used and not k.startswith(DYNAMIC_PREFIXES)}
        self.assertEqual(unused, set(), "คีย์ที่ไม่มีโค้ดเรียกใช้")


class NoStrayThai(unittest.TestCase):
    def test_html_has_no_thai(self):
        src = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertIsNone(THAI.search(src), "index.html ต้องไม่มีอักษรไทย ให้ใช้ data-i18n")

    def test_python_has_no_thai_strings_outside_docstrings(self):
        from storagecheck import history
        # ตารางแปลงผลสแกนเก่า (เก็บป้ายไทยไว้โดยตั้งใจ) ไม่นับเป็นข้อความที่หลงมา
        allowed = set(history.OLD_CATEGORY) | set(history.OLD_KIND)
        found = []
        for p in python_files():
            tree = ast.parse(p.read_text(encoding="utf-8"))
            docs = set()
            for node in ast.walk(tree):
                body = getattr(node, "body", None)
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body:
                    first = body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                        docs.add(id(first.value))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str) and THAI.search(node.value)
                        and id(node) not in docs and node.value not in allowed):
                    found.append(f"{p.name}:{node.lineno}: {node.value[:50]!r}")
        self.assertEqual(found, [], "ข้อความไทยที่ยังไม่ได้ย้ายไปพจนานุกรม")

    def test_js_has_no_thai_outside_comments(self):
        for p in js_files():
            if p in THAI_ALLOWED:
                continue
            code = strip_js_comments(p.read_text(encoding="utf-8"))
            lines = [ln.strip() for ln in code.splitlines() if THAI.search(ln)]
            self.assertEqual(lines, [], f"{p.name} มีข้อความไทยที่ยังไม่ได้ย้ายไปพจนานุกรม")


if __name__ == "__main__":
    unittest.main()
