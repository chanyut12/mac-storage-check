"""ข้อความหลายภาษาฝั่ง Python: อ่านพจนานุกรมจาก static/locales/<lang>.json ไฟล์เดียวกับที่หน้าเว็บใช้

ภาษาเก็บเป็นค่าต่อคำขอ (ContextVar) เว็บเซิร์ฟเวอร์ตั้งจากคำขอ ส่วน CLI ตั้งครั้งเดียวตอนเริ่ม
"""

import json
import re

from contextvars import ContextVar

from .config import BASE


LANGS = ("th", "en")
DEFAULT_LANG = "th"
LOCALES_DIR = BASE / "static" / "locales"

_lang = ContextVar("lang", default=DEFAULT_LANG)
_dicts = {}


def _load(lang):
    if lang not in _dicts:
        try:
            _dicts[lang] = json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _dicts[lang] = {}
    return _dicts[lang]


def set_lang(lang):
    """ตั้งภาษาของคำขอนี้ ค่าที่ไม่รู้จักใช้ภาษาไทย"""
    _lang.set(lang if lang in LANGS else DEFAULT_LANG)


def get_lang():
    return _lang.get()


def tr(key, **vars):
    """ข้อความตามภาษาปัจจุบัน แทนที่ {ชื่อ} ด้วยค่าใน vars (n == 1 ใช้คีย์ "<key>.one" ถ้ามี)
    ไม่มีคีย์ในภาษานั้นจะย้อนไปใช้ภาษาไทย และถ้าไม่มีเลยจะคืนชื่อคีย์
    """
    for lang in (get_lang(), DEFAULT_LANG):
        d = _load(lang)
        s = d.get(key + ".one") if vars.get("n") == 1 else None
        s = s if s is not None else d.get(key)
        if s is not None:
            return re.sub(r"\{(\w+)\}", lambda m: str(vars.get(m.group(1), m.group(0))), s)
    return key
