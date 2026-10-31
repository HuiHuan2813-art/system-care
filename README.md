# System Care

跨平台的系統健檢工具，給 AI agent 用的技能包（Skill），不是獨立 App。

它按需執行——被叫到才跑，跑完就退出，**沒有常駐程序、沒有背景監控、沒有排程**。

```
A 記憶體健檢（唯讀）  看記憶體壓力與吃 RAM 前 10 名，不改任何東西
B 磁碟安全清理        只清白名單的快取暫存，先列清單、確認才刪、前後對比
C 一鍵效能報告        記憶體 + 磁碟 + 開機啟動項 + 大檔 Top 10 + 建議
```

支援 macOS / Windows / Linux。Android / iOS 只做唯讀診斷與手動步驟。

---

## 它不做的事

- 不關閉、不退出你正在用的 App，不關視窗，不 kill 程序
- 不碰文件、照片、桌面、下載、音樂、影片、系統目錄、App 本體、金鑰
- 不需要 root／管理員權限
- 不連網，不上傳任何資料

## 一句話說明立場

沒有任何工具能「無感釋放 RAM」，那在技術上不成立。macOS 與 Linux 會刻意把閒置記憶體當檔案快取用，所以「可用記憶體」很低是正常現象；清掉快取只會讓系統重新從磁碟讀，通常更慢。

這支工具因此只看**記憶體壓力**（normal / warn / critical）。壓力正常時它會直接說「不需要處理」，不會為了交差硬湊建議。

---

## 安裝（WorkBuddy）

```bash
git clone https://github.com/HuiHuan2813-art/system-care ~/.workbuddy/skills/system-care
```

WorkBuddy 在工作階段啟動時掃描技能目錄，裝好後**開一個新對話**才會載入。

裝好後直接說：

- 「幫我看一下記憶體」→ 走 A
- 「C 槽滿了，幫我清快取」→ 先列清單，等你挑
- 「做一份效能健檢報告」→ 走 C

## 不安裝也能用（macOS / Linux）

`scripts/system_care.py` 是純標準庫、零依賴的診斷引擎：

```bash
python3 scripts/system_care.py mem                 # 記憶體健檢（唯讀）
python3 scripts/system_care.py disk                # 白名單掃描（只列清單）
python3 scripts/system_care.py report              # 快檢報告
python3 scripts/system_care.py report --big-files  # 含大檔 Top 10（較慢）
python3 scripts/system_care.py clean               # dry-run，只印計畫
python3 scripts/system_care.py clean --apply --yes # 才真的刪
```

清理的安全機制，四層：

1. 目標寫死在白名單，**不接受任意路徑參數**
2. 只刪白名單根目錄底下的子項，不刪根目錄本身
3. 符號連結一律跳過，黑名單路徑直接拒絕
4. 沒有 `--apply` 一律 dry-run；有終端機時還要再輸入 `yes`

Windows 不需要腳本，走 PowerShell 指令即可（見 `SKILL.md`）。

---

## 白名單

| 平台 | 項目 |
|---|---|
| macOS | `~/Library/Caches`、`~/Library/Logs`、Xcode DerivedData、CoreSimulator Caches、`~/.Trash` |
| Windows | `%TEMP%\*`、`%LOCALAPPDATA%\Temp\*`、資源回收筒、瀏覽器快取 |
| Linux | `~/.cache/*`、`~/.local/share/Trash/*`、`~/.thumbnails` |

黑名單（永不觸碰）：`~/Documents`、`~/Desktop`、`~/Downloads`、`~/Pictures`、`~/Movies`、`~/Music`、`~/.ssh`、`~/Library` 本身、`/System`、`/Library`、`/Applications`、`/usr`、`/etc`、`/var`。

## 平台能力界線

| 平台 | 記憶體 | 自動清理 | 說明 |
|---|---|---|---|
| macOS | ✅ | ✅ | 完整支援 |
| Windows | ✅ | ✅ | 完整支援（PowerShell） |
| Linux | ✅ | ✅ | 套件快取、journal 需 sudo，會先說明再問 |
| Android | ✅（需 adb） | 手動引導 | 無 root 無法清其他 App 的快取 |
| iOS | ❌ | 手動引導 | 沙盒限制，只能給步驟 |

`adb shell pm clear` 會清掉 App 資料（含登入狀態），屬破壞性操作，本專案不主動使用。

---

## 目錄

```
SKILL.md                        技能本體：執行規則、各平台指令、輸出格式
scripts/system_care.py          唯讀診斷 + 白名單清理引擎
references/platform-matrix.md   平台界線、Android/iOS 手動步驟、需 sudo 的項目
references/safety-checklist.md  刪除前逐項檢查表
```

## 為什麼做這個

規則比程式先寫好。

一開始只有兩頁文字：一份說明它該做什麼，一份說明它絕對不能做什麼。第二份寫得比較久——不能關使用者的 App、不能碰白名單以外的路徑、任何刪除都要先給清單。這些不是後來補的限制，是動手前就先劃好的線。

原因很簡單：清理工具是最容易闖禍的一類軟體。它拿到刪除權限，判斷依據卻只是一個資料夾名稱。寫的時候就得假設它會判斷錯。

程式寫完，我原本想標價一元上架。一元不是為了賺錢，是想知道有沒有人願意為「不亂刪」這件事付錢。結果卡在開發者認證——平台只受理中國大陸二代居民身份證，我沒有，這條路就斷了，沒有轉圜餘地。

後來想想，一元和免費之間其實沒差多遠。真正想驗證的東西——有沒有人需要一個「明確告訴你它不做什麼」的工具——不用收錢也驗證得出來。所以我把它放出來。

這種工具沒有護城河，任何人會用 `du` 和 `rm` 都能寫一個。它唯一值錢的地方是你相信它不會亂來，而信任沒辦法靠功能列表建立，只能靠你看得見它。

所以原始碼在這裡，每一行你都能讀。

## 授權

MIT。拿去改、拿去賣、拿去放進你自己的工具裡都可以，唯一要求是保留授權聲明。
如果你把它改得更好，歡迎回來開 PR。
