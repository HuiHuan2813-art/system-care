# 平台能力界線（誠實版）

| 平台 | 記憶體健檢 | 自動清理 | 大檔掃描 | 說明 |
|---|---|---|---|---|
| macOS | ✅ 完整 | ✅ 完整 | ✅ | `memory_pressure` + `vm_stat` 判壓力；白名單見 SKILL.md |
| Windows | ✅ 完整 | ✅ 完整 | ✅ | PowerShell；資源回收筒與 `cleanmgr` 皆可用 |
| Linux | ✅ 完整 | ✅ 完整（部分需 sudo） | ✅ | 套件快取、journal 需 sudo，先說明再問 |
| Android | ✅（需 adb 連線） | ⚠️ 手動引導 | ❌ | 無 root 無法清其他 App 快取；`pm clear` 會清資料 |
| iOS | ❌ 無法跑指令 | ⚠️ 手動引導 | ❌ | 沙盒限制，只能給步驟 |

**沒有任何平台能「無感釋放 RAM」。** 系統本來就會自動管理記憶體；真正該看的是「記憶體壓力」。
本 skill 的原則：只讀診斷 + 白名單清理 + 先確認再動手，**絕不關閉使用中的 App／視窗**。

---

## Android 手動步驟（給使用者照做）

1. 設定 → 儲存空間 → 清理建議（系統會列出可清的暫存與重複檔）
2. 設定 → 應用程式 → 選 App → 儲存空間 → **清除快取**（不要按「清除資料」，會登出）
3. 設定 → 電池與裝置維護 → 立即最佳化

需 adb 的唯讀指令：
```bash
adb shell cat /proc/meminfo
adb shell dumpsys meminfo | head -n 40
adb shell du -sh /sdcard/DCIM /sdcard/Download 2>/dev/null
```
破壞性指令（**必須另行警告並取得明確同意**）：
```bash
adb shell pm clear <package>   # 會清掉該 App 全部資料，含登入狀態
```

## iOS 手動步驟

1. 設定 → 一般 → iPhone 儲存空間 → 看 App 佔用 → 「卸載 App」（保留資料）或刪除
2. 設定 → Safari → 清除瀏覽紀錄與網站資料
3. 照片：設定 → 照片 → 開啟「最佳化 iPhone 儲存空間」
4. 重開機可清暫存，但**不要**承諾「釋放多少 GB」

---

## 需 sudo / 系統層的項目（先說明再問，绝不默默執行）

| 平台 | 指令 | 影響 |
|---|---|---|
| Linux | `journalctl --vacuum-time=7d` | 清 7 天前的系統日誌 |
| Linux | `sudo apt-get clean` / `sudo dnf clean all` | 套件快取，需重新下載 |
| Linux | `sudo pacman -Sc` | 舊版套件快取 |
| macOS | `sudo rm -rf /Library/Caches/*` | **公司／共用機器不建議**，且可能需重啟服務 |

系統層一律：先列大小 → 說明影響 → 由使用者自己決定是否輸入 sudo，agent 不代為提權。

---

## 已知誤區（遇到要主動糾正）

- **「可用記憶體只剩 1 GB 所以很卡」** → 錯。macOS/Linux 會用閒置 RAM 當快取，看壓力才對。
- **「一鍵釋放 RAM 讓電腦變快」** → 記憶體被清掉只會讓系統重新從磁碟讀取，通常更慢。
- **「清垃圾桶等於釋放空間」** → 只有垃圾桶真的佔空間時才成立，要先量。
- **「Optimization/加速 App 能修好一切」** → 多數只是重複系統既有功能；本 skill 只做可驗證的實測前後對比。
