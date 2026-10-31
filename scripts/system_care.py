#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
system_care.py — System Care 唯讀診斷 + 白名單清理引擎

設計原則（與 SKILL.md 一致，不得放寬）：
  1. 預設只讀：mem / disk / report 三個子命令不改動任何檔案。
  2. 清理需明示：clean 預設 dry-run，必須加 --apply 才會刪；有終端機時還要輸入 yes。
  3. 白名單硬編碼：只能刪白名單根目錄「底下」的內容，不接受任意路徑參數。
  4. 不碰符號連結、不碰黑名單、不關閉任何 App／視窗。

用法：
  python3 system_care.py mem
  python3 system_care.py disk
  python3 system_care.py report [--big-files]
  python3 system_care.py clean                 # 只列清單
  python3 system_care.py clean --apply --yes   # 才真的刪
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time

# ---------------------------------------------------------------- 基礎工具

BLACKLIST = [
    "~/Documents", "~/Desktop", "~/Downloads", "~/Pictures", "~/Movies",
    "~/Music", "~/.ssh", "~/Library", "/System", "/Library", "/Applications",
    "/usr", "/bin", "/sbin", "/etc", "/var", "/private/etc",
]


def home():
    return os.path.expanduser("~")


def human(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.2f %s" % (n, unit))
        n /= 1024.0


def detect_platform():
    s = platform.system()
    if s == "Darwin":
        return "macos"
    if s == "Windows":
        return "windows"
    if s == "Linux":
        return "linux"
    return s.lower()


def run(cmd, timeout=20):
    """執行外部指令，失敗或超時回傳 None，永不拋錯。"""
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
        return p.stdout if p.returncode == 0 else (p.stdout or None)
    except Exception:
        return None


def path_size(path):
    """不跟隨符號連結地累加大小。"""
    total = 0
    if os.path.islink(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.lstat(path).st_size
        except OSError:
            return 0
    for root, dirs, files in os.walk(path, followlinks=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if not os.path.islink(fp):
                    total += os.lstat(fp).st_size
            except OSError:
                pass
    return total


# ---------------------------------------------------------------- 白名單定義

def whitelist():
    """回傳白名單清單。path 為根目錄，清理時只刪其「子項」。"""
    plat = detect_platform()
    h = home()
    items = []
    if plat == "macos":
        items = [
            {"id": "user-caches", "label": "使用者快取 ~/Library/Caches",
             "path": os.path.join(h, "Library/Caches"),
             "note": "App 會自行重建；建議先關閉相關 App 再清"},
            {"id": "user-logs", "label": "使用者日誌 ~/Library/Logs",
             "path": os.path.join(h, "Library/Logs"),
             "note": "診斷用日誌，可重建"},
            {"id": "xcode-derived", "label": "Xcode DerivedData",
             "path": os.path.join(h, "Library/Developer/Xcode/DerivedData"),
             "note": "下次 build 會重建（會變慢一次）"},
            {"id": "simulator-cache", "label": "iOS 模擬器快取",
             "path": os.path.join(h, "Library/Developer/CoreSimulator/Caches"),
             "note": "模擬器下次啟動會重建"},
            {"id": "trash", "label": "垃圾桶 ~/.Trash",
             "path": os.path.join(h, ".Trash"),
             "note": "清空後無法復原"},
        ]
    elif plat == "linux":
        items = [
            {"id": "xdg-cache", "label": "使用者快取 ~/.cache",
             "path": os.path.join(h, ".cache"),
             "note": "應用程式快取，可重建"},
            {"id": "trash", "label": "回收筒 ~/.local/share/Trash/files",
             "path": os.path.join(h, ".local/share/Trash"),
             "note": "清空後無法復原"},
            {"id": "thumbnails", "label": "縮圖快取 ~/.thumbnails",
             "path": os.path.join(h, ".thumbnails"),
             "note": "檔案管理器會重建"},
        ]
    return [i for i in items if os.path.isdir(i["path"])]


def guard(path):
    """確認路徑可安全操作：必須在白名單根目錄內、且不在黑名單。"""
    real = os.path.realpath(path)
    for bad in BLACKLIST:
        b = os.path.realpath(os.path.expanduser(bad))
        if real == b:
            raise SystemExit("拒絕操作：%s 在黑名單內" % real)
    allowed = [os.path.realpath(w["path"]) for w in whitelist()]
    if not any(real == a or real.startswith(a + os.sep) for a in allowed):
        raise SystemExit("拒絕操作：%s 不在白名單內" % real)
    return real


# ---------------------------------------------------------------- A 記憶體

def mem_info():
    plat = detect_platform()
    out = {"platform": plat}
    if plat == "macos":
        total = run(["sysctl", "-n", "hw.memsize"])
        out["total"] = int(total.strip()) if total and total.strip().isdigit() else None
        vm = run(["vm_stat"]) or ""
        pages = {}
        page_size = 16384
        for line in vm.splitlines():
            if "page size of" in line:
                try:
                    page_size = int(line.split("page size of")[1].split()[0])
                except Exception:
                    pass
            if ":" in line:
                k, v = line.split(":", 1)
                v = v.strip().rstrip(".")
                if v.isdigit():
                    pages[k.strip()] = int(v)
        used = (pages.get("Pages active", 0) + pages.get("Pages wired down", 0) +
                pages.get("Pages occupied by compressor", 0)) * page_size
        out["used_est"] = used
        out["page_size"] = page_size
        mp = run(["memory_pressure"], timeout=25) or ""
        for line in mp.splitlines():
            if "System-wide memory free percentage" in line:
                out["free_pct"] = line.split(":")[-1].strip()
        out["pressure_level"] = _pressure_level(out.get("free_pct"), vm)
    elif plat == "linux":
        info = {}
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0]) * 1024
        except Exception:
            pass
        total = info.get("MemTotal")
        out["total"] = total
        out["used_est"] = total - info.get("MemAvailable", 0) if total else None
        avail = info.get("MemAvailable", 0)
        out["pressure_level"] = ("normal" if total and avail / total > 0.25
                                 else "warn" if total and avail / total > 0.10
                                 else "critical")
        out["free_pct"] = "%.0f%%" % (100.0 * avail / total) if total else None
    elif plat == "windows":
        out["note"] = "Windows 請由 agent 以 PowerShell 指令取得（見 SKILL.md）"
    return out


def _pressure_level(free_pct, vm_text):
    try:
        pct = float(str(free_pct).replace("%", "").strip())
    except Exception:
        pct = None
    if pct is None:
        return "unknown"
    if pct >= 30:
        return "normal"
    if pct >= 10:
        return "warn"
    return "critical"


def top_ram(n=10):
    """三層備援：psutil → ps aux → top。全部失敗則回傳空清單。"""
    rows = []
    # 1) psutil（不需外部指令，權限受限環境也能跑）
    try:
        import psutil  # noqa: F401
        procs = []
        for p in psutil.process_iter(["name", "memory_percent", "memory_info"]):
            try:
                pct = p.info["memory_percent"] or 0.0
                rss = (p.info["memory_info"].rss if p.info["memory_info"] else 0)
                procs.append((pct, rss, p.info["name"] or "?"))
            except Exception:
                continue
        procs.sort(reverse=True)
        if procs:
            return procs[:n]
    except Exception:
        pass
    # 2) ps aux
    out = run(["ps", "aux"], timeout=15) or ""
    for line in out.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        try:
            rows.append((float(parts[3]), float(parts[5]), parts[10][:90]))
        except ValueError:
            continue
    if rows:
        rows.sort(reverse=True)
        return rows[:n]
    # 3) top（macOS）
    out = run(["top", "-l", "1", "-o", "mem", "-n", str(n),
               "-stats", "pid,command,mem"], timeout=20) or ""
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1].endswith(("K", "M", "G", "-")):
            try:
                val = parts[1]
                mult = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}.get(val[-1], 1)
                size = int(val.rstrip("KMG+-")) * mult
                rows.append((0.0, size, " ".join(parts[2:])[:90]))
            except Exception:
                continue
    rows.sort(key=lambda r: -r[1])
    return rows[:n]


def cmd_mem(_args):
    info = mem_info()
    print("== 記憶體健檢（唯讀） ==")
    print("平台：%s" % info.get("platform"))
    if info.get("total"):
        print("實體記憶體：%s" % human(info["total"]))
    if info.get("used_est") is not None:
        print("已使用（估算）：%s" % human(info["used_est"]))
    print("系統可用比例：%s" % (info.get("free_pct") or "未知"))
    print("記憶體壓力：%s" % (info.get("pressure_level") or "未知"))
    print("\n-- 吃 RAM 前 10 名（%MEM） --")
    tops = top_ram()
    if not tops:
        print("    （無法取得程序清單：目前執行環境限制程序查詢）")
        print("    macOS 請開「活動監視器 → 記憶體」依「記憶體」欄排序；"
              "Linux 用 `ps aux --sort=-%mem | head`。")
    for pct, rss, cmd in tops:
        pct_s = ("%5.1f%%" % pct) if pct else "  --  "
        print("%s  %10s  %s" % (pct_s, human(rss * 1024), cmd))
    print("\n提醒：macOS/Linux 會刻意用 RAM 當檔案快取，數字高不等於不足。"
          "以「記憶體壓力」為準；本工具不關閉任何 App。")
    return 0


# ---------------------------------------------------------------- B 磁碟清理

def scan_targets():
    result = []
    for w in whitelist():
        children = []
        try:
            with os.scandir(w["path"]) as it:
                for e in it:
                    try:
                        sz = 0 if e.is_symlink() else path_size(e.path)
                        children.append({"name": e.name, "path": e.path,
                                         "size": sz, "symlink": e.is_symlink()})
                    except OSError:
                        continue
        except OSError:
            continue
        children.sort(key=lambda c: -c["size"])
        result.append({"target": w, "children": children,
                       "total": sum(c["size"] for c in children)})
    return result


def cmd_disk(_args):
    print("== 磁碟白名單掃描（唯讀，尚未刪除任何東西） ==")
    total_all = 0
    for blk in scan_targets():
        w = blk["target"]
        print("\n[%s] %s  —  %s" % (w["id"], w["label"], human(blk["total"])))
        print("    %s" % w["note"])
        for c in blk["children"][:8]:
            flag = "（符號連結，跳過）" if c["symlink"] else ""
            print("    - %-40s %10s %s" % (c["name"][:40], human(c["size"]), flag))
        if len(blk["children"]) > 8:
            print("    ... 另有 %d 項" % (len(blk["children"]) - 8))
        total_all += blk["total"]
    print("\n可清理總計（估計）：%s" % human(total_all))
    print("以上僅為清單。要真的刪除需使用者確認後執行 clean --apply。")
    return 0


def _remove(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
        return True
    shutil.rmtree(path, ignore_errors=True)
    return not os.path.exists(path)


def cmd_clean(args):
    blocks = scan_targets()
    if not blocks:
        print("此平台無可用白名單項目。")
        return 0
    plan = [b for b in blocks if b["total"] > 0]
    grand = sum(b["total"] for b in plan)
    print("== 清理計畫 ==")
    for b in plan:
        print("- [%s] %s：%d 項，%s" % (b["target"]["id"], b["target"]["label"],
                                     len(b["children"]), human(b["total"])))
    print("合計可釋放：%s" % human(grand))

    if not args.apply:
        print("\n目前是 dry-run，未刪除任何檔案。")
        print("確認後執行：system_care.py clean --apply --yes")
        return 0

    if sys.stdin.isatty() and not args.yes:
        ans = input("\n這會永久刪除上述快取／暫存。輸入 yes 繼續：").strip().lower()
        if ans != "yes":
            print("已取消，未刪除任何東西。")
            return 1

    before = shutil.disk_usage(home()).free
    deleted, failed = 0, 0
    for b in plan:
        root = guard(b["target"]["path"])
        for c in b["children"]:
            if c["symlink"]:
                failed += 1
                continue
            if not os.path.realpath(c["path"]).startswith(root + os.sep):
                failed += 1
                continue
            try:
                ok = _remove(c["path"])
            except Exception:
                ok = False
            if ok:
                deleted += c["size"]
            else:
                failed += 1
    time.sleep(1)
    after = shutil.disk_usage(home()).free
    print("\n== 清理結果 ==")
    print("已刪除內容：%s" % human(deleted))
    print("實際釋放（磁碟實測）：%s" % human(max(0, after - before)))
    if failed:
        print("跳過／失敗：%d 項（多為使用中或被鎖定，屬正常）" % failed)
    return 0


# ---------------------------------------------------------------- C 健檢報告

def disk_usage():
    u = shutil.disk_usage("/")
    return {"total": u.total, "used": u.used, "free": u.free,
            "pct": 100.0 * u.used / u.total if u.total else 0}


def startup_items():
    plat = detect_platform()
    items = []
    if plat == "macos":
        for d in ("~/Library/LaunchAgents", "/Library/LaunchAgents",
                  "/Library/LaunchDaemons"):
            p = os.path.expanduser(d)
            if os.path.isdir(p):
                for f in sorted(os.listdir(p)):
                    if f.endswith(".plist"):
                        items.append("%s/%s" % (d, f))
    elif plat == "linux":
        p = os.path.expanduser("~/.config/autostart")
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.endswith(".desktop"):
                    items.append("~/.config/autostart/%s" % f)
        out = run(["systemctl", "list-unit-files", "--type=service",
                   "--state=enabled", "--no-pager"], timeout=15) or ""
        for line in out.splitlines()[1:]:
            if line.strip():
                items.append("systemd: " + line.split()[0])
    return items


def big_files(threshold=500 * 1024 * 1024, limit=10, budget=25):
    """掃描家目錄大檔；有時間預算，避免跑太久。"""
    found = []
    skip = {os.path.expanduser(p) for p in
            ("~/Library/Caches", "~/.cache", "~/.Trash", "~/Library/Developer",
             "~/.local/share/Trash")}
    start = time.time()
    for root, dirs, files in os.walk(home(), followlinks=False):
        if time.time() - start > budget:
            break
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and os.path.join(root, d) not in skip]
        for f in files:
            fp = os.path.join(root, f)
            try:
                if os.path.islink(fp):
                    continue
                sz = os.lstat(fp).st_size
            except OSError:
                continue
            if sz >= threshold:
                found.append((sz, fp))
    found.sort(reverse=True)
    return found[:limit]


def cmd_report(args):
    info = mem_info()
    du = disk_usage()
    print("=" * 58)
    print(" System Care — 效能健檢報告")
    print(" 時間：%s" % time.strftime("%Y-%m-%d %H:%M"))
    print("=" * 58)

    print("\n[1] 記憶體")
    print("  平台：%s" % info.get("platform"))
    if info.get("total"):
        print("  實體：%s／已用（估算）：%s"
              % (human(info["total"]), human(info.get("used_est") or 0)))
    print("  可用比例：%s　壓力：%s"
          % (info.get("free_pct") or "未知", info.get("pressure_level") or "未知"))
    tops = top_ram(5)
    if not tops:
        print("    程序清單不可得（環境限制），請改用活動監視器。")
    for pct, rss, cmd in tops:
        pct_s = ("%5.1f%%" % pct) if pct else "  --  "
        print("    %s  %s  %s" % (pct_s, human(rss * 1024), cmd[:60]))

    print("\n[2] 磁碟")
    print("  已用 %s / %s（%.1f%%），可用 %s"
          % (human(du["used"]), human(du["total"]), du["pct"], human(du["free"])))

    print("\n[3] 可清理項目（白名單，尚未刪除）")
    total = 0
    for blk in scan_targets():
        if blk["total"] > 0:
            print("    %-28s %10s" % (blk["target"]["label"][:28], human(blk["total"])))
            total += blk["total"]
    print("    合計：%s" % human(total))

    print("\n[4] 開機啟動項")
    st = startup_items()
    if st:
        for s in st[:15]:
            print("    - %s" % s)
        if len(st) > 15:
            print("    ... 另有 %d 項" % (len(st) - 15))
    else:
        print("    無（或此平台需另查）")

    if args.big_files:
        print("\n[5] 大檔 Top 10（>500MB，掃描較慢）")
        for sz, fp in big_files():
            print("    %10s  %s" % (human(sz), fp))
    else:
        print("\n[5] 大檔 Top 10：未掃描（需加 --big-files，全碟掃描較慢）")

    print("\n[6] 建議")
    print("    - 記憶體以「壓力」判斷，normal 就不必處理。")
    print("    - 磁碟可清項目需確認後才刪，指令：clean --apply --yes")
    print("    - 本報告全程唯讀，未關閉任何 App。")
    return 0


# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description="System Care 診斷與白名單清理")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("mem", help="A 記憶體健檢（唯讀）")
    sub.add_parser("disk", help="B 磁碟白名單掃描（唯讀）")
    p_rep = sub.add_parser("report", help="C 一鍵健檢報告")
    p_rep.add_argument("--big-files", action="store_true", help="加掃大檔 Top 10")
    p_clean = sub.add_parser("clean", help="B 清理（預設 dry-run）")
    p_clean.add_argument("--apply", action="store_true", help="真正執行刪除")
    p_clean.add_argument("--yes", action="store_true", help="跳過互動確認")
    args = ap.parse_args()

    plat = detect_platform()
    if plat not in ("macos", "linux"):
        print("此腳本支援 macOS / Linux。目前平台：%s。" % plat)
        print("Windows 請由 agent 使用 SKILL.md 的 PowerShell 指令；"
              "Android／iOS 僅能唯讀＋手動引導。")
        return 2

    if args.cmd == "mem":
        return cmd_mem(args)
    if args.cmd == "disk":
        return cmd_disk(args)
    if args.cmd == "report":
        return cmd_report(args)
    if args.cmd == "clean":
        return cmd_clean(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
