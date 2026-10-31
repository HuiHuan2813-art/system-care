# 刪除前檢查表（每次執行 B 之前逐項過，任一項不過就停）

## 1. 使用者同意
- [ ] 已列出清單（項目、大小、影響）
- [ ] 使用者看過並明確同意（「全清」或指定編號）
- [ ] 不是「順手清一下」這類模糊授權

## 2. 路徑合法性
- [ ] 目標在白名單內（macOS：`~/Library/Caches`、`~/Library/Logs`、DerivedData、Simulator Caches、`~/.Trash`；Linux：`~/.cache`、Trash、`~/.thumbnails`；Windows：`%TEMP%`、`%LOCALAPPDATA%\Temp`）
- [ ] 目標不在黑名單（Documents / Desktop / Downloads / Pictures / Movies / Music / `~/.ssh` / `~/Library` 本身 / `/System` / `/Library` / `/Applications` / `/usr` / `/etc` / `/var`）
- [ ] 目標不是符號連結（`readlink` 有輸出就跳過）
- [ ] 只刪白名單根目錄**底下**的子項，不刪根目錄本身

## 3. 不動程序
- [ ] 沒有關閉任何 App／視窗
- [ ] 沒有 kill 任何程序
- [ ] 沒有為了刪檔案而要求使用者先關 App（只「建議」，由他自己決定）

## 4. 前後對比
- [ ] 刪除前已記錄可用空間 `df -h` / `Get-PSDrive`
- [ ] 刪除後再記一次
- [ ] 回報含「刪除內容大小」與「磁碟實測釋放」兩個數字
- [ ] 跳過的項目與原因一併列出（使用中／權限不足／符號連結）

## 5. 例外處理
- [ ] 刪不掉就跳過，不重試強制刪除
- [ ] 權限不足就誠實回報，不假裝成功
- [ ] 使用者中途反悔 → 立即停止，不再刪任何東西

---

## 絕對禁止（任何情況下都不做）

1. `rm -rf ~`、`rm -rf /`、對家目錄用萬用字元
2. 遞迴刪除 Desktop / Downloads / Documents
3. 刪除 `~/Library` 或 `/Library` 根目錄
4. 用 `pm clear` 清 App 資料而未警告
5. 聲稱「已釋放 XX GB」而沒有實測
6. 聲稱「無感釋放 RAM」
7. 未經同意就提權（sudo）
