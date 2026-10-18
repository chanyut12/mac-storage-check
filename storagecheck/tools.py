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
    ("npm: cache", "npm", ["npm", "cache", "clean", "--force"], None),
    # ใช้ pip ของระบบโดยตรง เพราะ PATH อาจชี้ไปที่ venv ของโปรเจกต์
    ("pip: cache", "/opt/homebrew/bin/pip3", ["pip3", "cache", "purge"], ["pip3", "cache", "info"]),
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


BREW_UPGRADE_TIMEOUT = 30 * 60


def run_cmd(cmd, timeout=None, stdout_only=False):
    """รันคำสั่งโดยไม่รับ stdin เพื่อให้คำสั่งที่ขอรหัสผ่านล้มเหลวทันที (ไม่ค้าง)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        return -1, f"หมดเวลาหลัง {timeout} วินาที"
    if stdout_only:
        return r.returncode, r.stdout.strip()
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


def brew_upgrade(apply):
    """คืนข้อความผลและจำนวนแพ็กเกจที่ล้าสมัย ถ้า apply=True จะรัน brew upgrade (ไม่ลบไฟล์ผู้ใช้)"""
    exe = find_binary("brew")
    if not exe:
        return "ไม่พบคำสั่ง brew", 0
    # stdout เท่านั้น เพราะ brew พิมพ์ "==>" ลง stderr ตอนอัปเดตข้อมูลก่อน
    _, out = run_cmd([exe, "outdated"], stdout_only=True)
    count = len(out.splitlines())
    if not count:
        return "ไม่มีแพ็กเกจที่ต้องอัปเดต", 0
    if not apply:
        return f"{out[:3000]}\n[dry-run] จะรัน: {exe} upgrade", count
    code, out = run_cmd([exe, "upgrade"], timeout=BREW_UPGRADE_TIMEOUT)
    text = out[-1500:] if out else "(ไม่มีผลลัพธ์)"
    status = "อัปเดตสำเร็จ" if code == 0 else f"อัปเดตไม่สำเร็จ (รหัส {code})"
    return f"{text}\n{status}", count


def mode_brew_upgrade(apply):
    text, _ = brew_upgrade(apply)
    print(text)
