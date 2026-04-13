# Frontend 操作說明

`frontend/` 是 Smart Meeting Assistant 的前端應用，使用 **React + TypeScript + Vite** 建置，負責：

- 上傳會議音檔
- 顯示處理狀態
- 查看 transcript / summary
- 與後端 API 進行聯動

---

## 1. 前置條件

請先確認本機環境符合以下需求：

- **Node.js**：建議使用較新的 LTS 版本
- **npm**：專案目前以 `npm` 管理依賴
- **後端服務**：若要做真實聯調，後端需可訪問
  - 預設位址：`http://localhost:8000`

> 目前前端已可獨立啟動與建置；若後端未啟動，頁面仍可打開，但 API 功能會失敗。

---

## 2. 進入前端目錄

```bash
cd /Users/rainchen/Coding/SmartMeeting/frontend
```

---

## 3. 安裝依賴

首次啟動或切換環境後，先安裝依賴：

```bash
npm install
```

專案內已有 `package-lock.json`，建議維持使用 `npm install` 的工作流。

---

## 4. 環境變數設定

前端會從 Vite 環境變數讀取 API 與輪詢設定。

### 4.1 已支援的環境變數

`frontend/src/env.d.ts` 目前定義了以下變數：

- `VITE_API_BASE_URL`
- `VITE_POLL_INTERVAL_MS`
- `VITE_POLL_TIMEOUT_MS`

### 4.2 建議 `.env.local`

如果後端不是跑在預設位址，可以在 `frontend/` 下建立 `.env.local`：

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_POLL_INTERVAL_MS=3000
VITE_POLL_TIMEOUT_MS=600000
```

### 4.3 預設行為

若未設定 `VITE_API_BASE_URL`，前端會預設連到：

```text
http://localhost:8000
```

---

## 5. 啟動開發模式

```bash
npm run dev
```

啟動後，Vite 會輸出本機預覽位址，通常是：

```text
http://localhost:5173
```

如果你想指定主機與埠號，可以這樣啟動：

```bash
npm run dev -- --host 127.0.0.1 --port 4173
```

---

## 6. 打開頁面驗證

啟動成功後，可在瀏覽器打開：

```text
http://localhost:5173
```

目前前端路由包含：

- `/`：上傳頁
- `/meetings/:meetingId`：會議詳情頁

例如：

```text
http://localhost:5173/meetings/test-id
```

---

## 7. 常用腳本

`frontend/package.json` 目前提供以下腳本：

### 7.1 開發模式

```bash
npm run dev
```

### 7.2 建置生產版本

```bash
npm run build
```

此命令會先執行 TypeScript 編譯，再執行 Vite build。

### 7.3 程式碼檢查

```bash
npm run lint
```

### 7.4 預覽建置結果

```bash
npm run preview
```

---

## 8. 與後端聯調說明

前端 HTTP client 預設會呼叫：

- `GET /health`
- `POST /meetings/upload`
- `POST /meetings/process`
- `GET /meetings/{meeting_id}`
- `GET /meetings/{meeting_id}/transcript`
- `GET /meetings/{meeting_id}/summary`

### 8.1 聯調基本順序

建議按以下流程測試：

1. 先確認後端健康檢查可用
2. 上傳音檔
3. 觸發處理流程
4. 輪詢會議狀態
5. 狀態完成後再取 transcript 與 summary

### 8.2 重要提醒

- 前端 API base URL 可由 `VITE_API_BASE_URL` 控制
- 如果後端沒有啟動，前端頁面可以進入，但 API 呼叫會出現錯誤
- 目前前端沒有內建正式測試腳本，主要以 `lint`、`build` 與實際瀏覽器驗證為主

---

## 9. 驗證前端是否正常

建議你至少執行以下命令：

```bash
npm run lint
npm run build
npm run dev
```

如果要快速確認本機是否真的能服務頁面，可以在 dev server 啟動後打開：

```text
http://localhost:5173/
```

以及：

```text
http://localhost:5173/meetings/test-id
```

---

## 10. 常見問題

### 10.1 前端打不開或白畫面

請檢查：

- `npm install` 是否完成
- `npm run dev` 是否有成功啟動
- 瀏覽器是否開錯埠號

### 10.2 API 請求失敗

請檢查：

- 後端是否已啟動
- `VITE_API_BASE_URL` 是否正確
- 後端是否允許前端來源的跨域請求

### 10.3 `build` 成功但仍有警告

目前已知可能出現兩類提示：

- TypeScript 版本與 `@typescript-eslint` 的相容性警告
- 第三方套件在 bundle 時出現 `use client` 類型警告

只要 `npm run build` 最後成功完成，通常不影響前端啟動。

---

## 11. 目前已確認的狀態

我已在本機驗證過以下項目：

- `npm run lint` 可執行
- `npm run build` 可執行
- `npm run dev` 可正常啟動
- `/` 與 `/meetings/test-id` 可回應頁面

---

## 12. 目錄概覽

```text
frontend/
├── public/
├── src/
│   ├── app/
│   ├── features/
│   ├── pages/
│   ├── shared/
│   └── widgets/
├── package.json
├── package-lock.json
└── README.md
```

---
