# 前端工程師 B 開發手冊（Meeting Detail / Transcript / Summary / UX）

> 角色定位：你係結果展示層 owner，負責令用戶「睇得清、搵得到、讀得舒服、狀態一致」。
>
> 對應總覽文檔：`docs/frontend/frontend_design_overview.md`
>
> 主要協作對象：工程師 A（API / status / polling owner）

## 0. 快速開始（Checklist）

- [ ] 確認 A 輸出的 query hooks 與共享型別
- [ ] 完成 Meeting Detail 頁面信息架構
- [ ] 完成 Transcript 展示（含 translation toggle / search）
- [ ] 完成 Summary 展示（summary / key_points / action_items）
- [ ] 覆蓋 empty/loading/error/partial state
- [ ] 交付可訪問性與核心測試

---

## 1. 目標與責任邊界

## 1.1 你的核心目標

1. 將後端結果轉為可讀、可掃描、可操作的 UI
2. 確保不同狀態下頁面體驗一致
3. 建立 transcript 與 summary 的展示規則
4. 保障可訪問性與結果頁測試質量

## 1.2 你擁有最終決策權（Owner）

- `pages/MeetingDetailPage/`
- `widgets/TranscriptPanel/`
- `widgets/SummaryPanel/`
- `features/search-transcript/`
- `features/toggle-translation/`
- 結果頁展示規則與交互細節

## 1.3 你不可單方面決策（需 A+B 共識）

- `shared/types` 公共型別
- `contracts.ts` response shape
- 錯誤碼字典
- 語言映射標準化策略

---

## 2. 交付清單（Deliverables）

## 2.1 必交付檔案（最少）

```text
frontend/src/
  pages/MeetingDetailPage/
  widgets/TranscriptPanel/
  widgets/SummaryPanel/
  widgets/ActionItemList/
  widgets/TranscriptSegmentCard/
  features/search-transcript/
  features/toggle-translation/
  entities/transcript/
  entities/summary/
  shared/utils/
    language.ts
    timeFormat.ts
```

## 2.2 對外輸出（俾 A / QA / Agent 使用）

- Transcript 顯示規則（排序、分組、字段 fallback）
- Summary 顯示規則（空態、缺字段處理）
- Detail 頁狀態展示矩陣
- 組件可訪問性準則

---

## 3. 執行路線（按依賴排序）

## Phase B0 - 契約消化（Day 1）

- 與 A 對齊 `TranscriptSegment`、`SummaryData` 標準型別
- 固化字段 fallback：`translation` 優先，兼容可能改名
- 對齊語言映射（`man/can/eng` + alias）

**完成標準**

- `entities` 層型別可獨立用於 UI
- 文檔中列清所有 fallback 規則

## Phase B1 - Detail 頁骨架（Day 2）

- 頂部信息條（meeting_id / file_name / status）
- 結果區 tabs（Transcript / Summary）
- loading/empty/error 區塊占位

**完成標準**

- 能接 A 的 status query 並顯示主狀態
- tabs 可鍵盤切換

## Phase B2 - Transcript 模塊（Day 2-3）

- Segment card 設計
- Translation toggle
- Transcript search（按 text / speaker）
- 長列表可讀性優化（分段、sticky header 可選）

**完成標準**

- `completed` 狀態可完整顯示 transcript
- 缺 translation 時不報錯，改顯示「暫無譯文」

## Phase B3 - Summary 模塊（Day 3-4）

- summary 主文本
- key points 列表
- action items 列表（owner 可選）
- 部分缺失字段 UI 降級顯示

**完成標準**

- summary 缺失時可顯示空態，不阻塞 transcript
- action item 無 owner 時仍可正常顯示

## Phase B4 - 可訪問性與測試（Day 4-5）

- 組件測試：TranscriptPanel / SummaryPanel
- 可訪問性檢查：label、aria、focus
- E2E 參與：completed / failed / partial data

**完成標準**

- 結果頁核心交互有測試
- 鍵盤與屏幕閱讀器路徑可用

---

## 4. 展示規則（UI Contract）

## 4.1 Transcript 規則

1. 默認按 `start` 升序
2. 每段顯示 `speaker + time range + text`
3. `translation` 開關關閉時隱藏譯文區
4. 片段缺 `speaker` 時 fallback `UNKNOWN`
5. `segment_id` 作次要信息，可折疊

## 4.2 Summary 規則

1. `summary` 有值就顯示正文
2. `key_points` 空陣列就顯示空態文案
3. `action_items` 空陣列就顯示「暫無行動項」
4. 無論 summary 是否存在，都不能阻塞整頁渲染

## 4.3 狀態展示矩陣

| meeting status | 頂部標記 | Transcript | Summary | 操作建議 |
| --- | --- | --- | --- | --- |
| uploaded | 已上傳 | disabled | disabled | 等待開始處理 |
| processing | 處理中 | loading | loading | 自動刷新 |
| completed | 已完成 | show data | show data | 可搜尋/切換 |
| failed | 失敗 | error state | error state | 返回重試 |

---

## 5. 與工程師 A 的介面契約

## 5.1 你依賴 A 的能力

- `useMeetingStatusQuery`
- `useMeetingTranscriptQuery`
- `useMeetingSummaryQuery`
- 標準化 `ApiError`

## 5.2 你要反饋 A 的需求

1. query 回傳型別需穩定
2. loading/error 字段命名需一致
3. polling 停止條件需可預測
4. 錯誤碼需可映射 UI 行為

---

## 6. 測試責任矩陣

| 測試項 | A 負責 | 你負責 | 備註 |
| --- | --- | --- | --- |
| UploadPage | Yes | No | A owner |
| Polling hook | Yes | No | A owner |
| MeetingDetailPage | No | Yes | B owner |
| TranscriptPanel | No | Yes | B owner |
| SummaryPanel | No | Yes | B owner |
| shared contracts | Yes | Yes | cross-review |

---

## 7. PR 模板（B 專用）

```markdown
## 背景
- 需求：
- 影響範圍：

## 變更內容
- [ ] detail page
- [ ] transcript
- [ ] summary
- [ ] search/translation toggle

## 契約變更
- [ ] 無
- [ ] 有（已通知 A + 更新文檔）

## 測試
- [ ] 組件測試
- [ ] 可訪問性檢查
- [ ] E2E 路徑覆蓋

## UX 風險
- 

## 截圖/錄屏
- 
```

---

## 8. Agent 協作模式（對 agent 友好）

## 8.1 任務卡格式（每次只派一張）

```yaml
task_id: B-TRANSCRIPT-002
owner: frontend-dev-b
goal: Implement transcript panel with translation toggle and empty states
inputs:
  - docs/frontend/frontend_design_overview.md
  - docs/frontend/developer_b_playbook.md
outputs:
  - frontend/src/widgets/TranscriptPanel/index.tsx
  - frontend/src/features/toggle-translation/model/useTranslationToggle.ts
acceptance:
  - renders speaker/start/end/text
  - handles missing translation
  - keyboard-accessible toggle
tests:
  - component tests for empty/loading/with-data
```

## 8.2 推薦 agent prompt 模板

```text
你係 SmartMeeting 前端工程師 B 助手。
請只改動 detail/transcript/summary 相關文件，不要調整 upload 或 api client。
所有顯示邏輯要處理 empty/loading/error/partial data。
完成後列出：改動文件、可訪問性處理、測試覆蓋、需 A 配合項目。
```

---

## 9. 常見風險與處置

1. **部分結果先到**：先渲染可用區塊，另一區顯示 loading/empty
2. **translation 字段缺失**：採用 fallback 文案，不拋錯
3. **speaker 缺失或 UNKNOWN**：統一 badge 樣式，避免版面跳動
4. **長 transcript 可讀性差**：加入搜索、分段、視覺層級
5. **A 的契約調整影響 UI**：要求 migration note，先改 adapter 再改 UI

---

## 10. 完成定義（Definition of Done）

- [ ] Meeting Detail 頁可按狀態正確渲染
- [ ] Transcript 與 Summary 支持完整/缺失/空態
- [ ] translation toggle + search 可用
- [ ] 主要結果元件有組件測試
- [ ] 可訪問性基本要求達標
- [ ] 文檔同步更新，A 已 review

