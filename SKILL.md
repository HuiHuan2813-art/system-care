---
name: system-care
display_name: "SystemCare-系統健檢與安全清理"
display_name_en: "System Care"
version: 1.0.0
description: "跨平台系統健檢與安全清理（on-demand、非常駐）。三分支：A 記憶體健檢（唯讀，看記憶體壓力與吃 RAM 大戶）、B 磁碟白名單安全清理（先列清單、確認才刪、前後對比釋放空間）、C 一鍵效能健檢報告（記憶體＋磁碟＋開機啟動項＋大檔 Top 10＋建議）。支援 macOS / Windows / Linux；Android / iOS 僅唯讀診斷＋手動引導。觸發詞：清理、清快取、釋放空間、記憶體、RAM、加速、健檢、系統報告、system care。"
description_zh: "唯讀診斷記憶體壓力、白名單清理快取暫存、一鍵產出效能健檢報告。不關你的 App、不碰個人檔案，任何刪除前先給清單等你確認。"
description_en: "Read-only memory pressure diagnosis, allowlist-only cache cleanup, and a one-shot performance report. Never closes your apps, never touches personal files, always lists before deleting. macOS/Windows/Linux; Android/iOS read-only and manual guidance."
---

# System Care（系統健檢與安全清理）

按需（on-demand）執行：**只有被呼叫時才跑，跑完即退出，沒有常駐背景程序、沒有排程、沒有監控**。
適用：macOS / Windows / Linux（完整）；Android / iOS（唯讀＋手動引導）。

本 skill 是操作型工具，不是聊天型角色。使用者問到「清理／加速／記憶體／健檢」時，**直接開始跑診斷，不要先寒暄、不要先問一堆問題**。

---

## 執行前的四條硬規則（S0，每次都要過）

1. **先診斷後動手**：任何刪除之前，一律先「只讀」掃描，列出清單與大小，等使用者確認。**未取得明確確認，不得執行刪除。**
2. **絕不關閉／退出任何 App、絕不關閉任何視窗、絕不 kills 任何程序。** 即使某個 App 佔用大量記憶體也一樣——只報告，不動手。
3. **只動白名單**：只清「可重新生成」的快取／暫存。**絕不碰**：文件、照片、桌面、下載、音樂、影片、系統目錄、App 本體、使用者個人資料、瀏覽器設定檔、金鑰（`~/.ssh` 等）。
4. **前後對比**：清理後必須回報「釋放了多少」，並區分「刪除內容大小」與「磁碟實測釋放」。

補充（同樣不可放寬）：

- 刪除前先確認目標路徑**不是符號連結**、不在黑名單內；無法確認就跳過並說明。
- 多個使用者共用／公司管理的機器，只清目前使用者家目錄底下的白名單項目，不碰系統層。
- 使用者要求「清 X 資料夾」但 X 不在白名單（例如 `~/Downloads`、`~/Documents`）→ **拒絕自動清**，改成列出該資料夾的大檔清單讓他自己判斷，並明說「我不會動這些檔案，除非你逐一指定」。
- 使用者說「順手幫我清乾淨」不算確認；確認指的是看過清單後明確同意。

---

## 誠實界線（S0，不得越界）

- **永不宣稱能「無感釋放 RAM／記憶體」**。那在技術上不成立，任何 App 聲稱做得到都是行銷話術。
- 記憶體一律以**「記憶體壓力」**判斷，不看「可用記憶體」高低。macOS / Linux 會刻意把 RAM 填滿當檔案快取，數字高是正常，不是不足。
- 壓力為 `normal` 時，**明確說「不需要處理」**，不要為了交差硬湊建議。
- **Android / iOS 只能唯讀＋手動引導**，不得假裝能自動清理。`adb shell pm clear` 會清掉 App 資料（含登入狀態），屬破壞性操作，必須先警告並取得同意才可用；無 root 的 Android 無法自動清其他 App 快取。
- 不誇大數字：釋放量用實測，不用「最多可釋放 XX GB」這種估計話術。

---

## Step 0 — 偵測平台

```bash
uname -s          # Darwin=macOS / Linux
sw_vers           # macOS 版本
echo $OS          # Windows_NT=Windows（走 PowerShell）
adb devices       # Android 有連線才走 adb 路線
```

判定後走對應分支；iOS 直接跳手動引導（見 `references/platform-matrix.md`）。

---

## 加速路徑：內建診斷腳本（macOS / Linux 首選）

本 skill 附一支**唯讀診斷 + 白名單清理**腳本，位於 skill 目錄下的 `scripts/system_care.py`。
先取得 skill 目錄的絕對路徑（`~/.workbuddy/skills/system-care/scripts/system_care.py`），以下簡稱 `<SC>`。

```bash
python3 <SC> mem                 # A 記憶體健檢（唯讀）
python3 <SC> disk                # B 白名單掃描（唯讀，只列清單）
python3 <SC> report              # C 快檢報告
python3 <SC> report --big-files  # C 完整版（含大檔 Top 10，較慢）
python3 <SC> clean               # B dry-run，只印計畫
python3 <SC> clean --apply --yes # 才真的刪（需使用者已確認）
```

腳本的安全設計（不要繞過）：清理目標寫死在白名單裡，**不接受任意路徑參數**；只刪白名單根目錄底下的子項；跳過符號連結；黑名單路徑直接拒絕；沒有 `--apply` 一律 dry-run。
若腳本不存在或執行失敗 → 退回下面各平台的原生指令，不要自己發明刪除指令。

Windows 不支援此腳本，一律用 PowerShell 指令（見下）。

---

## A. 記憶體健檢（唯讀，不改任何東西）

### macOS
```bash
memory_pressure                        # 壓力等級：normal / warn / critical
sysctl -n hw.memsize                   # 實體記憶體總量
vm_stat                                # 分頁統計
ps aux | sort -rk 4 | head -n 10       # 吃 RAM 前 10 名（%MEM）
```
若 `ps` 被權限擋住 → 改用「活動監視器 → 記憶體」引導使用者自己排序看。

### Windows（PowerShell）
```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='MemLoad%';e={[math]::Round(100-($_.FreePhysicalMemory/$_.TotalVisibleMemorySize*100),1)}}
Get-Process | Sort-Object WS -Descending | Select-Object -First 10 Name, @{n='MB';e={[int]($_.WS/1MB)}}
```

### Linux
```bash
free -h
sed -n '1,5p' /proc/meminfo
ps aux --sort=-%mem | head -n 10
```

### Android（唯讀，需 adb）
```bash
adb shell cat /proc/meminfo
adb shell dumpsys meminfo | head -n 40
```
無 adb → 引導：設定 → 系統 → 開發人員選項 → 記憶體。

### iOS
無法跑指令。引導：設定 → 一般 → iPhone 儲存空間。

解讀規則：壓力 `normal` → 說「正常，不需處理」；`warn` → 指出前幾名佔用者並說明「關掉是你自己的決定，我不會幫你關」；`critical` → 建議重啟該 App 或整機重開，仍不代勞。

---

## B. 磁碟安全清理（白名單、先量後清、先確認）

### 白名單（可清，系統或 App 會重新生成）

| 平台 | 項目 |
|---|---|
| macOS | `~/Library/Caches`、`~/Library/Logs`、`~/Library/Developer/Xcode/DerivedData`、`~/Library/Developer/CoreSimulator/Caches`、`~/.Trash` |
| Windows | `$env:TEMP\*`、`$env:LOCALAPPDATA\Temp\*`、資源回收筒、瀏覽器快取、`cleanmgr` |
| Linux | `~/.cache/*`、`~/.local/share/Trash/*`、`~/.thumbnails`、`journalctl --vacuum-time=7d`（需 sudo）、`apt-get clean`／`dnf clean all`（需 sudo） |

### 黑名單（絕不碰）

`~/Documents`、`~/Desktop`、`~/Downloads`、`~/Pictures`、`~/Movies`、`~/Music`、`~/.ssh`、
`~/Library` 根目錄本身、`/System`、`/Library`、`/Applications`、`/usr`、`/bin`、`/etc`、`/var`。

### 流程（三步，不可跳）

**Step B1 — 先量（只讀）**

macOS：
```bash
du -sh ~/Library/Caches ~/Library/Logs ~/.Trash 2>/dev/null
du -sh ~/Library/Developer/Xcode/DerivedData 2>/dev/null
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -n 10
```
Windows：
```powershell
$t = Get-ChildItem $env:TEMP -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum
"TEMP: {0:N2} MB" -f ($t.Sum/1MB)
Get-ChildItem $env:LOCALAPPDATA\Temp -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum | ForEach-Object { "LocalTemp: {0:N2} MB" -f ($_.Sum/1MB) }
```
Linux：
```bash
du -sh ~/.cache ~/.local/share/Trash 2>/dev/null
du -sh ~/.cache/* 2>/dev/null | sort -rh | head -n 10
```

**Step B2 — 列清單並等確認**

輸出格式（照抄這個結構）：

```
可清理項目（尚未刪除）
1. 使用者快取 ~/Library/Caches   4.11 GB   ← App 會重建，建議先關相關 App
2. 使用者日誌 ~/Library/Logs      29.8 MB
3. 垃圾桶 ~/.Trash                 0 B
合計：4.14 GB

要清哪幾項？（回「全清」或指定編號；不清就回「不用」）
```

沒有拿到回覆 → 停在這裡，什麼都不刪。

**Step B3 — 執行 + 前後對比**

- macOS / Linux：`python3 <SC> clean --apply --yes`，或依確認的項目用原生指令刪。
- Windows：
```powershell
$before = (Get-PSDrive C).Free
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue
$after = (Get-PSDrive C).Free
"釋放: {0:N2} MB" -f (($after-$before)/1MB)
```
- 「使用中／被鎖定」的檔案刪不掉是正常的，**不要**為了刪掉它去關 App。
- 回報必須含：刪了哪些項目、刪除內容大小、磁碟實測釋放、跳過幾項與原因。

### Android / iOS

- Android：引導「設定 → 儲存空間 → 清理」與「應用程式 → 個別 App → 清除快取」。`pm clear` 為破壞性，需另行警告並取得同意。
- iOS：引導「設定 → 一般 → iPhone 儲存空間 → 卸載未使用的 App」、Safari 清除網站資料。**不聲稱能自動清**。

---

## C. 一鍵效能健檢報告

一次跑完六段，輸出成一份可直接貼給人看的報告：

1. **平台與時間**
2. **記憶體**：總量、已用、可用比例、**壓力等級**、前 5 名佔用者
3. **磁碟**：已用／總量／使用率／可用
4. **可清理項目**：白名單各項大小與合計（**只列不清**）
5. **開機啟動項**：`~/Library/LaunchAgents`、`/Library/LaunchAgents`、`/Library/LaunchDaemons`（Windows：`Get-CimInstance Win32_StartupCommand`；Linux：`systemctl list-unit-files --type=service --state=enabled`、`~/.config/autostart`）
6. **大檔 Top 10**（>500 MB；**先告知全碟掃描較慢**）＋ **建議清單**，分「可自動」「需手動」兩欄

指令：
```bash
python3 <SC> report            # 含 1–4、5、6 的建議段
python3 <SC> report --big-files
```
```powershell
# Windows 大檔
Get-ChildItem $env:USERPROFILE -Recurse -File -ErrorAction SilentlyContinue |
  Sort-Object Length -Descending | Select-Object -First 10 FullName, @{n='GB';e={[math]::Round($_.Length/1GB,2)}}
```
```bash
# macOS / Linux 大檔
find ~ -type f -size +500M 2>/dev/null -exec du -h {} + | sort -rh | head -n 10
```

建議段的話術規則：壓力 normal 就寫「記憶體正常，不需處理」；磁碟 >85% 才提清理；啟動項只列不建議亂關（標註「關閉前請確認用途」）。

---

## 輸出規範

| 情境 | 必須包含 |
|---|---|
| A 記憶體 | 壓力等級 + 前幾名佔用者 + 「不動手」聲明 |
| B 清理 | 清理前清單 → 確認 → 刪除明細 → 前後對比 → 跳過項原因 |
| C 報告 | 六段齊全，建議分「可自動／需手動」 |

語氣：直接給數字與判斷，不鋪陳、不催促、不重複同一句結論。報告用表格或清單，不要整段散文。

## 失敗處理

- 腳本不存在 → 用 SKILL.md 的原生指令，不要臆造。
- `du` 卡住（大目錄／網路磁碟）→ 加 `timeout`，改為只掃第一層。
- 權限不足（`Operation not permitted`）→ 誠實說「此環境限制讀取，請手動查看 X」，不要假裝成功。
- 平台不在支援清單 → 說明限制，給手動步驟，不硬跑指令。

## 參考檔

- `references/platform-matrix.md` — 各平台能力界線、Android/iOS 手動步驟、需 sudo 的項目
- `references/safety-checklist.md` — 刪除前逐項檢查表（執行前必過）
