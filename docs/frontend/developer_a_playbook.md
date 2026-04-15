# 前端工程師 A 開發手冊（App Shell / Upload / API / Polling）

> 角色定位：你係前端基礎層 owner，負責令整個產品「可啟動、可請求、可輪詢、可報錯」。
>
> 對應總覽文檔：`docs/frontend/frontend_design_overview.md`
>
> 主要協作對象：工程師 B（結果展示 owner）

## 0. 快速開始（Checklist）

- [ ] 鎖定前端技術棧與目錄骨架
- [ ] 建立 `shared/api` 基礎設施（client + contract + error）
- [ ] 完成上傳頁與兩段式流程（upload -> process）
- [ ] 完成 meeting 狀態輪詢（含 timeout / retry / cancel）
- [ ] 提供可被 B 直接接入的 query hooks 與標準型別
- [ ] 交付測試（單測 + 組件測試 + mock 流程）

---

## 1. 目標與責任邊界

## 1.1 你的核心目標

1. 建立可穩定復用的 API 調用層
2. 提供可靠的狀態輪詢與任務生命週期管理
3. 完成 Upload 主流程頁面
4. 為工程師 B 提供穩定、型別化、可測試的資料入口

## 1.2 你擁有最終決策權（Owner）

- `app/` 啟動與 providers
- `shared/api/`（http client, error normalize, request wrapper）
- `features/upload-meeting/`
- `features/start-processing/`
- `features/poll-meeting-status/`
- upload/status 相關測試

## 1.3 你不可單方面決策（需 A+B 共識）

- `shared/types` 的公共 domain 型別
- 語言代碼映射策略（`man/can/eng` 與 `zh/en/yue` 兼容）
- `MeetingStatus` 枚舉
- 錯誤碼顯示文案字典

---

## 2. 交付清單（Deliverables）

## 2.1 必交付檔案（最少）

```text
frontend/src/
  app/
    App.tsx
    providers/
    router/
  shared/api/
    httpClient.ts
    contracts.ts
    errors.ts
    meetings.api.ts
  shared/types/
    meeting.ts
    response.ts
  features/upload-meeting/
    model/
    ui/
    api/
  features/start-processing/
  features/poll-meeting-status/
  pages/UploadPage/
  widgets/ProcessingStatusPanel/
  widgets/ErrorBanner/
```

## 2.2 對外輸出（俾 B 使用）

- `useMeetingStatusQuery(meetingId)`
- `useStartMeetingProcessMutation()`
- `useUploadMeetingMutation()`
- `MeetingStatus` 與 `MeetingMeta` 型別
- `normalizeApiError(error)`

---

## 3. 執行路線（按依賴排序）

## Phase A0 - 契約凍結（Day 1）

- 從 `docs/api/frontend_backend_api_contract.md` 抽出最小可用 contract
- 確認統一 envelope：`success/message/data/error`
- 與 B 對齊 `contracts.ts` 首版

**完成標準**

- `contracts.ts` 可覆蓋 upload/process/status 三接口
- `status` 字段只有：`uploaded/processing/completed/failed`

## Phase A1 - 應用骨架（Day 1-2）

- 路由建立：`/`、`/meetings/:meetingId`
- 初始化 provider：QueryClient、Error Boundary、Toast
- 注入環境變量讀取

**完成標準**

- 本地可進入 upload 頁
- 假資料下可導航至 detail 頁

## Phase A2 - Upload + Process（Day 2-3）

- Upload 表單（文件 + lang_hint）
- 請求序列：`upload` 成功後自動 `process`
- 任一環節失敗可重試

**完成標準**

- 一鍵完成兩段式調用
- 失敗時 UI 顯示對應錯誤碼

## Phase A3 - Polling（Day 3-4）

- 封裝 polling hook
- 支持間隔、超時、頁面卸載中止
- `completed/failed` 立即停止

**完成標準**

- 10 分鐘 timeout 可配置
- 離開頁面不再繼續請求

## Phase A4 - 測試與穩定化（Day 4-5）

- 單元測試：error normalize、status guard、polling 控制
- 組件測試：UploadPage、ErrorBanner
- MSW 模擬 upload/process/status

**完成標準**

- 核心路徑測試通過
- 可以穩定輸出 `meetingId` 供 B 使用

---

## 4. 技術規範（必守）

## 4.1 API 封裝規範

1. 任何頁面不得直接 `fetch('/meetings/...')`
2. 所有請求都走 `shared/api/httpClient.ts`
3. envelope 驗證失敗要拋標準錯誤
4. 請求取消使用 `AbortController`

## 4.2 錯誤處理規範

- 先判斷 `error.code`，再展示 message
- 對已知錯誤碼提供可操作文案（例如「重新上傳」「重試」）
- 未知錯誤統一 fallback：`UNKNOWN_ERROR`

## 4.3 狀態機規範

合法狀態流：

`uploaded -> processing -> completed`

`uploaded -> processing -> failed`

禁止 UI 自行創造狀態字串。

---

## 5. 與工程師 B 的介面契約

## 5.1 你要提供的穩定 API（不可輕易破壞）

- `getMeetingStatus(meetingId)`
- `useMeetingStatusQuery(meetingId, options)`
- `meetingStatusToUiState(status)`
- `ApiError` 統一型別

## 5.2 變更協議

如果你要改 `contracts.ts`：

1. 先更新文檔
2. 開 PR 並 `@B` 必審
3. 在 PR 描述中列明 breaking change
4. 提供 migration note

---

## 6. 測試責任矩陣

| 測試項 | 你負責 | B 負責 | 備註 |
| --- | --- | --- | --- |
| upload 流程 | Yes | No | A owner |
| process 觸發 | Yes | No | A owner |
| status polling | Yes | No | A owner |
| transcript 顯示 | No | Yes | B owner |
| summary 顯示 | No | Yes | B owner |
| 共享 contract | Yes | Yes | cross-review |

---

## 7. PR 模板（A 專用）

```markdown
## 背景
- 需求：
- 影響範圍：

## 變更內容
- [ ] app/router/provider
- [ ] shared/api
- [ ] upload/process flow
- [ ] polling

## 契約變更
- [ ] 無
- [ ] 有（已更新 docs + 通知 B）

## 測試
- [ ] 單元測試
- [ ] 組件測試
- [ ] MSW 模擬

## 風險
- 

## 回滾方案
- 
```

---

## 8. Agent 協作模式（對 agent 友好）

## 8.1 任務卡格式（每次只派一張）

```yaml
task_id: A-POLL-001
owner: frontend-dev-a
goal: Implement polling hook with timeout and cancellation
inputs:
  - docs/frontend/frontend_design_overview.md
  - docs/frontend/developer_a_playbook.md
outputs:
  - frontend/src/features/poll-meeting-status/model/useMeetingPolling.ts
acceptance:
  - stops on completed/failed
  - stops on unmount
  - timeout configurable
tests:
  - unit test for stop conditions
```

## 8.2 推薦 agent prompt 模板

```text
你係 SmartMeeting 前端工程師 A 助手。
請只改動 polling 相關文件，不要變更 transcript/summary UI。
必須遵守 shared/api 契約，不可直接在 page 層發 request。
完成後列出：改動文件、風險、測試覆蓋、未決問題。
```

---

## 9. 常見風險與處置

1. **上傳成功但 process 失敗**：保留 `meeting_id`，提供「只重試 process」按鈕
2. **輪詢超時**：停止自動輪詢，提供手動刷新
3. **語言代碼不一致**：只在 adapter 層兼容，不在 UI 分支硬判斷
4. **後端暫未提供路由**：MSW 先打通前端流程，切換真 API 時只替換 base URL

---

## 10. 完成定義（Definition of Done）

- [ ] UploadPage 可完成 upload + process
- [ ] meeting status polling 穩定，能中止、能超時
- [ ] A 向 B 輸出穩定 query hooks + 型別
- [ ] 主要錯誤碼有可理解提示
- [ ] 測試覆蓋核心流程
- [ ] 文檔已更新，B 已 review

