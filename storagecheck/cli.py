"""จุดเข้าของ CLI: แยกคำสั่งไปยังโหมดต่าง ๆ"""

import argparse
import os
import sys

from .cleanup import mode_clean_cache, mode_interactive
from .config import TOP_N
from .duplicates import mode_duplicates
from .history import mode_diff, mode_report
from .i18n import LANGS, set_lang, tr
from .safety import category_label, classify
from .tools import mode_brew_upgrade, mode_tools
from .util import gb
from .walk import scan


def mode_scan():
    files, buckets = scan()
    print("\n" + tr("cli.top_files", n=TOP_N))
    for size, p in sorted(files, reverse=True)[:TOP_N]:
        print(f"{gb(size)}  {category_label(classify(p)):10}  {p}")
    print("\n" + tr("cli.top_folders", n=TOP_N))
    for key, size in sorted(buckets.items(), key=lambda x: -x[1])[:TOP_N]:
        print(f"{gb(size)}  {key}")


def pick_lang(argv):
    """อ่าน --lang ก่อนสร้าง parser เพื่อให้ข้อความ help แปลตามภาษา (ถ้าไม่ระบุใช้ STORAGECHECK_LANG)"""
    lang = os.environ.get("STORAGECHECK_LANG")
    for i, a in enumerate(argv):
        if a == "--lang" and i + 1 < len(argv):
            lang = argv[i + 1]
        elif a.startswith("--lang="):
            lang = a.split("=", 1)[1]
    return lang


def main():
    set_lang(pick_lang(sys.argv[1:]))
    ap = argparse.ArgumentParser(description=tr("cli.description"))
    ap.add_argument(
        "mode",
        nargs="?",
        default="scan",
        choices=["scan", "report", "diff", "tools", "brew-upgrade", "clean-cache", "interactive", "duplicates"],
    )
    ap.add_argument("--yes", action="store_true", help=tr("cli.help_yes"))
    ap.add_argument("--lang", choices=LANGS, help=tr("cli.help_lang"))
    args = ap.parse_args()

    if args.mode == "scan":
        mode_scan()
    elif args.mode == "report":
        mode_report()
    elif args.mode == "diff":
        mode_diff()
    elif args.mode == "tools":
        mode_tools(args.yes)
    elif args.mode == "brew-upgrade":
        mode_brew_upgrade(args.yes)
    elif args.mode == "clean-cache":
        mode_clean_cache(args.yes)
    elif args.mode == "interactive":
        mode_interactive()
    elif args.mode == "duplicates":
        mode_duplicates(args.yes)
