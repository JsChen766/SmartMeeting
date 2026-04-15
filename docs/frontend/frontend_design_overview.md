# 前端開發文檔（Smart Meeting Assistant）

> 版本：v1.0
> 
> 適用範圍：`frontend/` 目錄下所有前端實作、測試與聯調工作。
> 
> 編寫目標：將現有後端能力、API 草案與系統架構，轉化成可直接落地的前端實作規範，方便兩位前端工程師並行開發、互相審查與最終交付。

## 1. 文檔目標與閱讀方式

本項目目前後端已完成基礎骨架與接口設計，前端仍處於空 scaffold 狀態。本文檔的目的不是只列出頁面，而是把「要做咩、點做、邊個做、點驗收」一次寫清楚，讓前端可以按規範直接開工。

本文檔適合以下角色閱讀：

1. 前端工程師 A / B
2. 後端工程師，用於核對接口契約
3. QA / 測試工程師，用於理解頁面狀態與測試路徑
4. 產品或項目負責人，用於確認範圍與非目標

---

## 2. 項目背景與現狀

### 2.1 項目定位

Smart Meeting Assistant 係一個面向會議音頻處理嘅助手型系統，核心能力包括：

1. 會議音頻上傳
2. 語音轉文字（ASR）
3. 說話人分離（diarization）
4. 文本與說話人時間戳對齊融合（alignment）
5. 翻譯（translation）
6. 摘要生成（summarization）

### 2.2 現有後端現狀

根據 `backend/app/main.py`，後端目前至少已提供：

- `GET /health`

根據 `docs/api/frontend_backend_api_contract.md` 與 `docs/api/request_response_schema.md`，前端聯調所需嘅主要業務接口已被設計為：

- `POST /meetings/upload`
- `POST /meetings/process`
- `GET /meetings/{meeting_id}`
- `GET /meetings/{meeting_id}/transcript`
- `GET /meetings/{meeting_id}/summary`

### 2.3 當前前端狀態

`frontend/` 目前係空 scaffold，未有正式應用代碼、路由、狀態管理或 API 層。意味住前端可以用「規範先行、結構先行」方式建立，避免之後大量重構。

---

## 3. 前端總體目標

前端首版目標係：

1. 讓用戶可上傳會議音頻
2. 讓用戶可觸發處理流程
3. 讓用戶可查看處理狀態
4. 讓用戶可閱讀轉錄內容、翻譯內容與摘要內容
5. 讓前後端契約保持穩定、可測試、可擴展

### 3.1 非目標範圍

首版前端**不**處理以下內容：

1. 音視頻通話能力
2. 會議日曆、邀請、賬號系統
3. 服務端模型訓練與算法調參
4. 原始數據目錄管理
5. 後端運算邏輯替代實作
6. 實時流式字幕播放（除非後端另行提供流式接口）

---

## 4. 建議技術棧與工程原則

> 說明：後端倉庫未鎖定任何前端框架，因此本文檔先採用一個穩定、主流、適合中小型產品的建議棧。若團隊已另有既定技術選型，可保留架構思想，只替換具體工具。

### 4.1 建議技術棧

- **框架**：React 18+
- **語言**：TypeScript
- **建構工具**：Vite
- **路由**：React Router
- **服務端狀態**：TanStack Query（React Query）
- **表單處理**：React Hook Form
- **Schema 驗證**：Zod
- **HTTP 客戶端**：fetch 封裝或 Axios（二選一，建議統一封裝）
- **樣式方案**：Tailwind CSS + 少量設計系統封裝
- **測試**：Vitest + Testing Library + Playwright
- **Mock 層**：MSW（Mock Service Worker）

### 4.2 選型原則

1. **型別優先**：接口與 UI 狀態盡量以 TypeScript 型別驅動。
2. **契約優先**：API 契約先定義，再實作頁面。
3. **組件可復用**：UI 元件按 domain / feature 分層，不寫大而全的頁面巨石組件。
4. **異步可觀測**：上傳、處理、輪詢、錯誤要可追踪、可重試。
5. **可測試**：接口層、格式轉換層、核心交互至少要有單元測試或組件測試。
6. **漸進式交付**：先完成核心單機流程，再逐步補充高級 UI 與細節。

### 4.3 前端工程規範

- 全部功能用 TypeScript 實作，不接受 `any` 滿地飛。
- 所有對外 API 只經由統一 client 層調用。
- 組件需保持單一職責。
- Page 層只做組裝，避免直接寫業務轉換邏輯。
- 所有顯示用時間統一格式化，避免散落各頁。
- 所有狀態判斷集中在 schema / helper，不要每個組件自己寫一套。

---

## 5. 推薦前端目錄結構

以下結構適合 `frontend/` 空 scaffold 的首版落地：

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── providers/
│   │   ├── router/
│   │   ├── config/
│   │   └── App.tsx
│   ├── pages/
│   │   ├── UploadPage/
│   │   ├── MeetingDetailPage/
│   │   └── NotFoundPage/
│   ├── widgets/
│   │   ├── UploadPanel/
│   │   ├── ProcessingStatusPanel/
│   │   ├── TranscriptPanel/
│   │   ├── SummaryPanel/
│   │   └── ErrorBanner/
│   ├── features/
│   │   ├── upload-meeting/
│   │   ├── start-processing/
│   │   ├── poll-meeting-status/
│   │   ├── toggle-translation/
│   │   └── search-transcript/
│   ├── entities/
│   │   ├── meeting/
│   │   ├── transcript/
│   │   ├── summary/
│   │   └── language/
│   ├── shared/
│   │   ├── api/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── hooks/
│   │   ├── ui/
│   │   └── constants/
│   └── styles/
├── tests/
└── vite.config.ts
```

### 5.1 分層原則

- `app/`：應用啟動、路由、全局 provider、環境配置。
- `pages/`：路由級頁面，只負責組裝 widgets/features。
- `widgets/`：可跨頁復用的區塊級 UI。
- `features/`：可獨立測試的交互能力，例如上傳、輪詢、切換翻譯。
- `entities/`：領域模型與展示規則，例如 meeting、transcript、summary。
- `shared/`：基礎能力、API 客戶端、公共型別、工具方法、低層 UI。

### 5.2 核心原則

1. **頁面不直接發散 API 細節**：所有 API 調用集中到 `shared/api`。
2. **資料模型只定義一次**：meeting、segment、summary 等型別唔好多處重複定義。
3. **轉換邏輯獨立**：例如 status 映射、語言代碼映射、時間格式化，全部放 utility。
4. **UI 與 domain 分離**：顯示層同數據層分開，方便測試與替換。

---

## 6. 頁面與信息架構

首版前端只需要以下主頁面：

1. **上傳頁 / Home**：建立新會議處理任務
2. **會議詳情頁 / Meeting Detail**：顯示處理進度、轉錄、翻譯、摘要
3. **404 頁**：處理未知路由

### 6.1 建議路由

- `/`：上傳頁
- `/meetings/:meetingId`：會議詳情頁
- `/meetings/:meetingId/transcript`：可選，若想用 URL tab 深鏈接
- `/meetings/:meetingId/summary`：可選，若想用 URL tab 深鏈接

### 6.2 介面流轉

**建議主流程：**

1. 用戶打開首頁
2. 選擇音頻文件與可選語言提示
3. 點擊「上傳並開始處理」
4. 系統先呼叫 `POST /meetings/upload`
5. 成功後再呼叫 `POST /meetings/process`
6. 前端導向會議詳情頁
7. 詳情頁輪詢 `GET /meetings/{meeting_id}`
8. 狀態轉為 `completed` 後，自動拉取 transcript / summary
9. 用戶查看處理結果並可切換翻譯展示

> 注：API 層將「上傳」與「開始處理」分離，前端 UX 可以合併成一個主按鈕，但內部仍應保留兩步調用，方便重試、診斷與後續擴展。

---

## 7. 頁面詳細規格

### 7.1 上傳頁（`/`）

#### 目標

讓用戶快速創建一個會議任務，並完成文件上傳與處理觸發。

#### 主要區塊

1. 標題區：產品名稱、簡短說明
2. 文件選擇區：拖拽上傳或點選文件
3. 語言提示區：`lang_hint`
4. 開始按鈕：`上傳並開始處理`
5. 提示區：支持格式、大小限制、處理提示

#### 核心操作

- 選擇音頻文件
- 驗證文件格式與大小
- 可選擇語言提示（如普通話、粵語、英文）
- 發起上傳
- 上傳成功後發起處理
- 跳轉到詳情頁

#### 校驗規則

- 文件必填
- 格式限制需與後端一致，前端顯示可支持副檔名，例如 `wav`、`mp3`、`m4a`、`flac`（最終以後端為準）
- 文件大小需有前端上限提示，例如 `<= 500MB` 或按後端配置同步
- 語言提示可選，不填則由後端自動識別

#### 狀態

- 初始態
- 選檔後待提交
- 上傳中
- 處理觸發中
- 失敗態：顯示錯誤原因並可重試
- 成功後跳轉態

---

### 7.2 會議詳情頁（`/meetings/:meetingId`）

#### 目標

為用戶提供單一會議的完整結果查看頁，包括處理狀態、轉錄、翻譯與摘要。

#### 建議結構

1. 頂部信息條
   - `meeting_id`
   - 文件名
   - 當前狀態
   - 時間戳（可選）

2. 處理進度區
   - uploaded / processing / completed / failed
   - loading indicator / progress indicator

3. 結果區
   - Transcript tab
   - Summary tab
   - 可選 Translation toggle

4. 調試區（僅 dev 模式）
   - available_results
   - 原始響應折疊區
   - 可選 alignment diagnostics

#### 詳情頁行為

- 首次進入時先查詢狀態
- 若狀態係 `processing`，定時輪詢
- 若狀態係 `completed`，再拉取 transcript / summary
- 若狀態係 `failed`，展示錯誤訊息與重試入口

#### Transcript 顯示要求

每個段落卡片應展示：

- `speaker`
- `start` / `end`
- `text`
- `translation`（若有）
- `segment_id`（可摺疊為次要信息）

#### Summary 顯示要求

- 摘要主文
- Key points 列表
- Action items 列表
- 可選擇按 owner 分組顯示

---

### 7.3 404 頁

當路由無匹配時顯示：

- 頁面不存在提示
- 返回首頁按鈕
- 若 meetingId 無效，可提示用戶返回上一步

---

## 8. 響應式與可訪問性要求

### 8.1 響應式

首版至少支持：

- 桌面端：1440px / 1280px / 1024px
- 平板：768px
- 手機：375px

#### 佈局原則

- 上傳頁在手機上改為單欄
- Transcript 卡片在窄屏下縱向堆疊
- Summary 區保持可讀性，不應因寬度過窄而溢出

### 8.2 可訪問性（A11y）

- 所有按鈕與表單需有可讀 label
- 文件上傳需支持鍵盤操作
- 狀態提示需可被 screen reader 感知
- 錯誤信息需明確可讀，不只靠顏色區分
- tab 介面需支持鍵盤切換

### 8.3 國際化（i18n）

雖然首版不一定接入完整 i18n 框架，但文案層應避免硬編碼到組件深處。

建議：

- 文案集中管理
- 語言代碼與展示名稱分離
- 保留多語展示能力，至少支援中文界面 + 英文內容顯示

---

## 9. API 接入與資料契約

### 9.1 統一響應格式

按 `docs/api/request_response_schema.md`，業務接口外層應遵循：

```json
{
  "success": true,
  "message": "request succeeded",
  "data": {},
  "error": null
}
```

前端 client 應封裝一層通用解析：

1. 檢查 `success`
2. `success=false` 時拋出標準化錯誤
3. `error.code` 用於 UI 分支判斷
4. `message` 用於 toast 或提示條

### 9.2 建議 API client 形態

`shared/api` 建議至少包含：

- `httpClient.ts`：fetch/axios 基礎封裝
- `meetings.api.ts`：上傳、觸發、查詢狀態、查詢結果
- `contracts.ts`：前後端共享型別與 schema
- `errors.ts`：錯誤碼與可讀文案映射

### 9.3 前端建議請求流程

#### 上傳

1. 組裝 `FormData`
2. 帶入 `file`
3. 可選帶入 `lang_hint`
4. 成功後記錄 `meeting_id`

#### 觸發處理

1. 使用 `meeting_id`
2. 傳遞 `target_lang`
3. 視需要設置 `enable_translation` / `translation_target_lang` / `enable_summary`

#### 查詢狀態

1. 輪詢 `GET /meetings/{meeting_id}`
2. 根據 status 決定是否繼續輪詢
3. `completed` 後停止輪詢並請求結果頁面資料

#### 查詢 transcript / summary

1. 狀態完成後再拉取
2. 若部分結果缺失，顯示對應空態而唔係整頁失敗

### 9.4 建議輪詢規則

- 初始輪詢間隔：3 秒
- 最大輪詢間隔：10 秒（可選指數退避）
- 最大輪詢時長：例如 10 分鐘或可配置
- `failed` 時立即停止輪詢
- 頁面卸載或切頁時中止請求

---

## 10. 語言代碼與字段命名策略

這一節係前後端聯調最容易出現歧義嘅地方，前端必須做「兼容層」，唔好直接把 backend 原始值裸露到 UI。

### 10.1 已知衝突

目前倉庫內存在幾種語言代碼表述：

1. `docs/api/frontend_backend_api_contract.md` 使用：`man`、`can`、`eng`
2. `backend/schemas/transcription.py` 的示例出現：`zh`、`en`、`yue`
3. 某些展示場景可能會用中文名稱，例如「普通話」「粵語」「英文」

### 10.2 前端建議策略

前端應採用以下規則：

1. **wire code（接口層）**：優先按後端接口契約接收 `man/can/eng`
2. **alias code（兼容層）**：同時接受 `zh/en/yue` 等歷史值
3. **display label（展示層）**：永遠顯示本地化名稱，例如「普通話」「粵語」「英文」
4. **內部邏輯**：只使用前端自己的標準化語言枚舉，不直接散落各頁比較字符串

### 10.3 建議映射表

| 接口值 | 兼容值 | 展示名稱 | 備註 |
| --- | --- | --- | --- |
| `man` | `zh` | 普通話 / Mandarin | 首選接口值 |
| `can` | `yue` | 粵語 / Cantonese | 首選接口值 |
| `eng` | `en` | 英文 / English | 首選接口值 |

### 10.4 `translation` 字段策略

前端應以 `translation` 作為首選展示字段。若後端未來改名成 `translated_text`，前端解析層要兼容，避免頁面組件直接依賴字段名。

建議做法：

- API 層：`normalizeTranscriptSegment(raw)`
- UI 層：只讀 `segment.translationText`
- 原始字段名變化由 adapter 承擔

---

## 11. 狀態管理設計

### 11.1 狀態分類

前端狀態大致分為三層：

1. **Server State**：meeting 狀態、transcript、summary
2. **UI State**：tab 選擇、展開/收合、translation toggle
3. **Form State**：上傳文件、語言選項、提交按鈕狀態

### 11.2 推薦處理方式

- Server State：TanStack Query
- UI State：React state / URL state / lightweight store
- Form State：React Hook Form

### 11.3 不建議做法

- 把後端結果全部複製入大型全局 store
- 每個頁面自己維護一套 status 枚舉
- 在 JSX 內寫大量 if/else 做字段轉換

---

## 12. 元件設計規範

### 12.1 基礎元件

`shared/ui` 應包含：

- Button
- Input
- Select
- Tabs
- Card
- Badge
- Alert
- Spinner / Skeleton
- EmptyState
- Modal / Drawer（如需要）

### 12.2 領域元件

`widgets` 或 `features` 層應包含：

- FileDropzone
- UploadSummaryCard
- ProcessingTimeline
- TranscriptSegmentCard
- TranscriptSearchBar
- SummaryKeyPointList
- ActionItemList
- ErrorStatePanel

### 12.3 元件設計原則

1. 元件 props 要清晰、可預期
2. 不要把整個原始 API response 一次塞入底層 UI
3. 複用優先於重寫，但避免過度抽象
4. 可視化元件需支持 loading、empty、error 三種狀態

---

## 13. 測試策略

### 13.1 單元測試

針對以下內容應有單元測試：

- status 映射
- language mapping
- response normalization
- 時間格式化
- segment 分組與排序
- action item parsing

### 13.2 組件測試

針對以下頁面/組件應有組件測試：

- UploadPage
- TranscriptPanel
- SummaryPanel
- ProcessingStatusPanel
- ErrorBanner

### 13.3 Mock 聯調測試

建議用 MSW 模擬：

- 上傳成功
- 上傳失敗
- processing 中
- completed
- failed
- transcript 欄位缺失
- summary 未生成

### 13.4 E2E 測試

建議至少覆蓋：

1. 上傳成功 → 進入詳情頁 → 完成輪詢 → 顯示 transcript / summary
2. API 返回 failed → 顯示錯誤狀態
3. 頁面刷新後仍可憑 meeting_id 恢復狀態
4. 不合法文件格式被前端攔截

---

## 14. 觀測性與除錯

### 14.1 前端日誌

開發階段應記錄：

- request id / meeting_id
- API 錯誤碼
- 輪詢次數與耗時
- 頁面狀態切換

### 14.2 生產環境注意事項

- 唔應直接在 UI 顯示過多內部 debug 信息
- 但可在錯誤提示中保留可追蹤的 reference id
- 對 upload/process 接口返回的 message 只做輕量展示，主判斷依賴 error code

---

## 15. 安全與數據處理要求

1. 不在前端持久化敏感音頻內容
2. 不把原始文件內容放入 localStorage
3. 如果需要記錄最近一次會議，只保存 `meeting_id` 與顯示名稱
4. 文件上傳前先做前端校驗，減少無效請求
5. 所有 API base URL 由環境變量控制，避免硬編碼

---

## 16. 環境變量與配置

建議前端環境變量：

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_POLL_INTERVAL_MS=3000
VITE_POLL_TIMEOUT_MS=600000
VITE_MAX_UPLOAD_SIZE_MB=500
VITE_DEFAULT_TARGET_LANG=man
VITE_ENABLE_MSW=false
```

### 配置原則

- 開發、測試、生產三套配置分離
- 所有可變參數都從環境讀取
- 不同環境可切換 mock / real API

---

## 17. 兩位前端工程師的協作拆分

本項目明確要求由兩位前端工程師並行完成。為避免互相阻塞，建議按「功能邊界 + 模塊邊界」拆分。

### 17.0 角色文檔入口

- 工程師 A 開發手冊：`docs/frontend/developer_a_playbook.md`
- 工程師 B 開發手冊：`docs/frontend/developer_b_playbook.md`

### 17.1 工程師 A：上傳、狀態、應用骨架

#### 負責範圍

1. 應用啟動、路由、全局 provider
2. `shared/api` 基礎 client
3. 上傳頁 UI 與表單驗證
4. 文件校驗、上傳接口調用
5. 觸發處理接口調用
6. 會議狀態輪詢
7. 全局錯誤處理與 toast / alert
8. 開發環境配置、mock 基礎設施

#### 主要交付物

- `httpClient`
- `meetings.api.ts`
- UploadPage
- ProcessingStatusPanel
- ErrorBanner
- polling hook

### 17.2 工程師 B：結果展示、轉錄、摘要

#### 負責範圍

1. Meeting Detail 頁結果區
2. Transcript 展示與搜尋
3. 翻譯顯示切換
4. Summary 展示、Key points、Action items
5. 空態 / 部分結果態 / 失敗態展示
6. 可訪問性與內容排版優化
7. 結果頁測試與視覺一致性

#### 主要交付物

- TranscriptPanel
- TranscriptSegmentCard
- SummaryPanel
- SummaryKeyPointList
- ActionItemList
- language display mapping

### 17.3 共享責任

以下內容由兩人共同維護：

1. `shared/types` / `shared/api/contracts.ts`
2. 語言代碼映射
3. status 枚舉
4. 錯誤碼字典
5. 主要文檔更新

### 17.4 協作規則

1. 任何接口字段變更先改文檔，再改代碼。
2. PR 不能只改 UI 不改型別。
3. 新增頁面前先確認路由和數據來源。
4. 所有共享型別變更都要 cross-review。
5. 互相 review 對方 PR，避免單人閉環。

---

## 18. 開發節奏建議

### Phase 0：契約對齊

- 確認 API 字段與狀態枚舉
- 確認語言代碼標準化策略
- 確認 `translation` 字段名
- 確認文件格式與大小限制

### Phase 1：骨架與上傳流程

- 建立前端工程
- 建立路由與 layout
- 完成上傳頁
- 完成 upload / process API 對接
- 完成基本 mock

### Phase 2：詳情頁與輪詢

- 完成會議狀態頁
- 完成輪詢與錯誤處理
- 完成 transcript / summary 請求

### Phase 3：結果展示打磨

- 完成 transcript 排版
- 完成 summary 結構化展示
- 加入搜索、翻譯切換、空態

### Phase 4：測試與收尾

- 單元測試
- 組件測試
- E2E 測試
- 文檔回補
- 性能與可訪問性修正

---

## 19. 驗收標準

前端首版完成時，應至少滿足：

1. 可以成功上傳音頻文件
2. 可以觸發處理流程
3. 可以看到處理狀態變化
4. `completed` 後可以查看 transcript
5. 可以查看 summary 與 action items
6. 錯誤態有可理解提示
7. 代碼結構清晰，型別完整
8. 測試覆蓋核心流轉
9. 文檔與 API 契約一致

---

## 20. 已知契約風險與待確認事項

### 20.1 待後端補齊的內容

1. 業務路由的正式實作
2. 是否支持文件格式白名單查詢
3. 是否支持進度百分比
4. 是否支持結果部分返回
5. 是否支持重試與重新處理

### 20.2 前端需特別注意的風險

1. 語言代碼存在歷史不一致
2. `translation` / 未來字段改名風險
3. transcript 可能部分片段缺失翻譯
4. summary 可能在 transcript 前或後完成的時序問題
5. 長音頻導致輪詢時間較長，需要 timeout 與重試策略

### 20.3 建議最終統一方向

- 以 `docs/api/frontend_backend_api_contract.md` 作為前後端聯調主契約
- 以 `translation` 作為翻譯展示主字段
- 以 `man/can/eng` 作為 wire code，並兼容 `zh/en/yue`
- 以 `meeting_id` 作為所有詳情頁的主鍵

---

## 21. 實施小結

如果要用一句話概括首版前端策略：

> 用「契約先行 + 分層清晰 + 兩人並行」方式，先做出一個可上傳、可輪詢、可查結果、可測試的會議處理界面，再逐步打磨視覺與高級交互。

---

## 22. 建議下一步

1. 確認前端技術棧
2. 建立 `frontend/` 工程初始化文件
3. 落實 `shared/api` 與 `shared/types`
4. 先做上傳頁與 meeting detail 頁骨架
5. 用 MSW 先把流程跑通，再接真後端

---

## 附錄 A：建議前端核心資料型別

```ts
export type MeetingStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

export type LanguageCode = 'man' | 'can' | 'eng';

export interface ErrorInfo {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface TranscriptSegment {
  segment_id: string;
  start: number;
  end: number;
  speaker: string;
  text: string;
  lang: string;
  translation?: string;
  source_lang?: string;
  target_lang?: string;
  confidence?: number;
}

export interface SummaryData {
  summary: string;
  key_points: string[];
  action_items: Array<{ owner?: string; task: string }>;
}
```

> 註：上述型別應隨後端契約演進而調整，但前端內部應保持穩定的標準化型別，不直接把原始 API response 四散到各頁。

