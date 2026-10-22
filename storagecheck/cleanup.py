"""เคลียร์ cache ใน ~/Library/Caches และ ~/.cache และโหมดเลือกไฟล์ทีละรายการ"""

from .config import HOME, TOP_N, min_size
from .i18n import tr
from .platforms import is_link_path
from .safety import category_label, classify, is_never, move_to_trash
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
    print("\n" + tr("cli.cleanup_header", min=min_size() // 1024**2, n=len(items), total=gb(total).strip()))
    for size, p in items[:TOP_N]:
        print(f"{gb(size)}  {p}")

    if not apply:
        print("\n" + tr("cli.cleanup_dry_run"))
        return
    if not items:
        return
    ok = move_to_trash([str(p) for _, p in items])
    if ok:
        print("\n" + tr("cli.cleanup_moved", n=len(items), total=gb(total).strip()))


def mode_interactive():
    files, _ = scan()
    candidates = [(s, p) for s, p in sorted(files, reverse=True) if not is_never(p)][:TOP_N]
    if not candidates:
        print(tr("cli.pick_none"))
        return

    print("\n" + tr("cli.pick_header"))
    for i, (size, p) in enumerate(candidates, 1):
        print(f"{i:3}. {gb(size)}  {category_label(classify(p)):10}  {p}")

    raw = input("\n" + tr("cli.pick_prompt")).strip()
    if not raw:
        print(tr("cli.cancelled"))
        return
    try:
        picks = sorted({int(x) for x in raw.split(",") if x.strip()})
    except ValueError:
        print(tr("cli.pick_bad_format"))
        return
    if any(i < 1 or i > len(candidates) for i in picks):
        print(tr("cli.pick_out_of_range"))
        return

    chosen = [candidates[i - 1] for i in picks]
    total = sum(s for s, _ in chosen)
    print("\n" + tr("cli.pick_will_move", n=len(chosen), total=gb(total).strip()))
    if input(tr("cli.pick_confirm")).strip().lower() != "y":
        print(tr("cli.cancelled"))
        return
    if move_to_trash([p for _, p in chosen]):
        print(tr("cli.pick_moved"))
