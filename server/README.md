# Kyte 系列軟體雲端授權驗證系統 (Cloudflare Workers + KV)

本系統為 **KyteShelf** 與 **KyteView** 共用的授權驗證核心，採用 **Cloudflare 免費方案**（每天 100,000 次請求、0 維護成本），支援兩款軟體的 **14 天全功能試用 + 永久買斷啟用 + 雙軟體合購同捆包（Bundle）**。

---

## 一、 序號命名規範與產品分類

為便於蝦皮/官方賣場管理、出貨與客服快速識別，序號前綴嚴格遵循產品代號：

| 產品類別 | 序號格式範例 | 前綴代號 | 適用軟體 |
| :--- | :--- | :--- | :--- |
| **KyteShelf 專用** | `KS-9H2B-4N8C-Z7W1` | `KS-` | 僅限 KyteShelf 專業版啟用 |
| **KyteView 專用** | `KV-M3F5-8K1P-A6D2` | `KV-` | 僅限 KyteView 專業版啟用 |
| **雙軟體合購同捆包** | `KB-T7V9-2E4X-L8Q3` | `KB-` | **一組序號同時解鎖 KyteShelf + KyteView** |
| **舊版相容序號** | `KYTE-XXXX-XXXX-XXXX` | `KYTE-` | 向下相容，自動視為 KyteShelf 序號 |

> **說明：KyteShelf 舊序號能改嗎？**
> - **完全相容，無痛升級**：伺服器程式碼具備自動相容邏輯，過去已經賣給客人的 `KYTE-` 舊序號**不需要收回或重新發卡**，客人的軟體依然 100% 正常使用。
> - **即日起新出貨**：全面改發新標準前綴 `KS-`（KyteShelf）與 `KV-`（KyteView），一眼就能辨識產品。

---

## 二、 Cloudflare KV 資料結構

在 Cloudflare Worker KV（命名空間：`KYTE_LICENSES`）中，每組序號儲存為 JSON 物件：

### 1. 單買 KyteShelf 序號 (`KS-`)
```json
{
  "product": "kyteshelf",
  "email": "buyer@example.com",
  "created_at": "2026-09-24",
  "activated_devices": ["c4a8f9b2-3e1a-4d22-b5e1-88f910ab3cd4"],
  "max_devices": 2,
  "status": "active",
  "note": "蝦皮首批銷售"
}
```

### 2. 單買 KyteView 序號 (`KV-`)
```json
{
  "product": "kyteview",
  "email": "buyer2@example.com",
  "created_at": "2026-09-24",
  "activated_devices": ["f7b1e4c8-9d22-48a1-b3f5-77a829bc1ef0"],
  "max_devices": 2,
  "status": "active",
  "note": "KyteView 首發"
}
```

### 3. 「雙工具組合包」或「全家桶」通用序號 (`KB-`，Kyte Bundle)
```json
{
  "product": "all",
  "email": "vip@example.com",
  "created_at": "2026-09-24",
  "activated_devices": [
    "c4a8f9b2-3e1a-4d22-b5e1-88f910ab3cd4",
    "f7b1e4c8-9d22-48a1-b3f5-77a829bc1ef0"
  ],
  "max_devices": 2,
  "status": "active",
  "note": "蝦皮合購特惠包"
}
```

---

## 三、 30 秒升級 Cloudflare Worker

如果你之前已經在 Cloudflare 部署過 `kyteshelf-license` Worker：

1. 登入 [Cloudflare Dashboard](https://dash.cloudflare.com/)。
2. 點擊左側 **Workers & Pages** $\rightarrow$ 點擊原有的 Worker（例如 `kyteshelf-license`）。
3. 點擊右上角 **Edit code**。
4. 將本資料夾內的 [`worker.js`](worker.js) 內容**全部複製並覆蓋貼上**。
5. 點擊右上角 **Save and deploy** 即可！

> 你的 API 網址維持不變（如 `https://kyteshelf-license.ais7896.workers.dev`），現有 KyteShelf 與新版 KyteView 即刻共用同一套後台。

---

## 四、 PowerShell 批次產生序號指令

打開 Windows PowerShell，直接調用 API 即可批次產生序號，直接複製去蝦皮上架或給自動發卡機器人：

### 1. 產生 10 組 KyteView 專用序號 (`KV-`)
```powershell
$headers = @{ "X-Admin-Secret" = "AdminSuperSecret_2026"; "Content-Type" = "application/json" }
$body = @{ count = 10; max_devices = 2; product = "kyteview"; note = "KyteView 蝦皮首批" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "https://kyteshelf-license.ais7896.workers.dev/api/admin/generate-keys" -Method Post -Headers $headers -Body $body
$response.keys
```
**輸出範例：**
```text
KV-8F2B-4N8C-Z7W1
KV-M3F5-8K1P-A6D2
KV-T7V9-2E4X-L8Q3
```

### 2. 產生 10 組 KyteShelf 專用序號 (`KS-`)
```powershell
$body = @{ count = 10; max_devices = 2; product = "kyteshelf"; note = "KyteShelf 新版序號" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "https://kyteshelf-license.ais7896.workers.dev/api/admin/generate-keys" -Method Post -Headers $headers -Body $body
$response.keys
```
**輸出範例：**
```text
KS-9H2B-4N8C-Z7W1
KS-L2D8-7P4Q-R9K6
```

### 3. 產生 5 組雙軟體合購全家桶序號 (`KB-`，一組啟用兩款)
```powershell
$body = @{ count = 5; max_devices = 2; product = "all"; note = "雙軟體合購同捆包" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "https://kyteshelf-license.ais7896.workers.dev/api/admin/generate-keys" -Method Post -Headers $headers -Body $body
$response.keys
```
**輸出範例：**
```text
KB-7V92-E4XL-8Q3A
KB-M4N8-2P9X-W1C5
```

---

## 五、 查詢序號狀態（售後與設備查詢）

當顧客詢問換電腦或無法啟用時，執行此指令查詢綁定狀態：
```powershell
$headers = @{ "X-Admin-Secret" = "AdminSuperSecret_2026" }
Invoke-RestMethod -Uri "https://kyteshelf-license.ais7896.workers.dev/api/admin/query-key?key=KV-8F2B-4N8C-Z7W1" -Headers $headers
```

---

## 六、 蝦皮出貨發卡範本

### 範本 A：KyteView 單獨版
```text
感謝您購買 KyteView 極速檔案預覽神器！

【您的專屬授權序號】：
KV-XXXX-XXXX-XXXX

【啟用方式】：
1. 請至官方頁面下載 KyteView 最新安裝檔並完成安裝。
2. 啟動軟體後，選取任意檔案按 Space 空白鍵彈出預覽。
3. 點擊頂部工具列右上角的 [免費版] 徽章，或按下「輸入授權序號」。
4. 貼上您的序號，點擊「驗證並啟用」即可永久解鎖專業版全部功能！

📌 本組序號支援個人 2 台 Windows 電腦使用。
📌 首次啟用後即享 100% 離線秒開；日後若更換新電腦，可在軟體內點選「解除綁定」無痛轉移。
```

### 範本 B：Kyte 雙軟體合購同捆包 (KyteShelf + KyteView)
```text
感謝您購買 Kyte 雙工具生產力終極合購組合包！

【您的全家桶通用序號】：
KB-XXXX-XXXX-XXXX

【啟用說明】：
此組序號為通用合購碼，可同時在「KyteShelf」與「KyteView」兩款軟體中啟用：
1. KyteShelf：開啟設定 $\rightarrow$ 軟體授權 $\rightarrow$ 輸入序號即可解鎖無限置物架。
2. KyteView：開啟預覽 $\rightarrow$ 點擊授權徽章 $\rightarrow$ 輸入同一組序號即可解鎖全部專業預覽。

📌 本組序號支援個人 2 台 Windows 電腦同時啟用兩款軟體。
```
