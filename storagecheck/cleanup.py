"""เคลียร์ cache ใน ~/Library/Caches และ ~/.cache และโหมดเลือกไฟล์ทีละรายการ"""

from .config import HOME, TOP_N, min_size
from .platforms import is_link_path
from .safety import classify, is_never, move_to_trash
from .util import gb
from .walk import dir_size, scan


def cache_candidates():
    """โฟลเดอร์ cache ใน home ที่ใหญ่กว่าเกณฑ์ขนาด เรียงจากใหญ่ไปเล็ก"""
    roots = [HOME / "Library" / "Caches", HOME / ".cache"]
    limit = min_size()
    items = []
    for root in roots:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir() and not is_link_path(str(child)) and not is_never(str(child)):
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
