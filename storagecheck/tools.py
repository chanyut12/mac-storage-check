"""เครื่องมือนักพัฒนา: Docker, Homebrew, conda, pnpm"""

import os
import shutil
import subprocess


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
