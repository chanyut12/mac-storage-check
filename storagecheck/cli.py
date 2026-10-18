"""จุดเข้าของ CLI: แยกคำสั่งไปยังโหมดต่าง ๆ"""

import argparse

from .cleanup import mode_clean_cache, mode_interactive
from .config import TOP_N
from .duplicates import mode_duplicates
from .history import mode_diff, mode_report
from .safety import classify
from .tools import mode_tools
from .util import gb
from .walk import scan


def mode_scan():
    files, buckets = scan()
    print(f"\n== ไฟล์ใหญ่สุด {TOP_N} อันดับ ==")
    for size, p in sorted(files, reverse=True)[:TOP_N]:
        print(f"{gb(size)}  {classify(p):10}  {p}")
    print(f"\n== โฟลเดอร์ใหญ่สุด {TOP_N} อันดับ ==")
    for key, size in sorted(buckets.items(), key=lambda x: -x[1])[:TOP_N]:
        print(f"{gb(size)}  {key}")


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
