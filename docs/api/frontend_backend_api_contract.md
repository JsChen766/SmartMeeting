# 前后端分离接口文档

本文档用于前端与后端分离开发时对齐 HTTP 接口契约。当前后端 `backend/app/main.py` 已实现 `GET /health`；会议上传、处理、结果查询接口仍是建议契约，需要后端按本文档补齐路由实现后才能正式联调。

## 基础信息

- 服务名称：Smart Meeting Assistant API
- 建议本地基础地址：`http://localhost:8000`
- 接口路径前缀：当前无全局 `/api` 前缀
- 请求与响应编码：`UTF-8`
- JSON 请求头：`Content-Type: application/json`
- 文件上传请求头：`Content-Type: multipart/form-data`
- 统一字段命名：`snake_case`
- 时间字段单位：秒，使用 `number`
- 语言代码：使用语言英文名称前三个字母的小写缩写，例如 `man` 普通话 Mandarin，`can` 粤语 Cantonese，`eng` 英文 English

## 统一响应格式

业务接口建议统一使用以下响应结构。系统健康检查接口为了保持轻量，可以直接返回简单对象。

```json
{
  "success": true,
  "message": "request succeeded",
  "data": {},
  "error": null
}
```

失败响应：

```json
{
  "success": false,
  "message": "request failed",
  "data": null,
  "error": {
    "code": "MEETING_NOT_FOUND",
    "message": "meeting_id does not exist",
    "details": {
      "meeting_id": "mtg_20260402_001"
    }
  }
}
```

## 当前已实现接口

### 健康检查

| 项目 | 内容 |
| --- | --- |
| 接口路径 | `/health` |
| 请求类型 | `GET` |
| Content-Type | 无请求体 |
| 当前状态 | 已实现 |

#### 请求参数

无。

#### 成功响应

```json
{
  "status": "ok",
  "service": "smart-meeting-backend"
}
```

#### 前端用途

用于启动页、开发代理或部署探活，确认后端服务是否可访问。

## 建议新增业务接口

### 1. 上传会议音频

| 项目 | 内容 |
| --- | --- |
| 接口路径 | `/meetings/upload` |
| 请求类型 | `POST` |
| Content-Type | `multipart/form-data` |
| 当前状态 | 待实现 |

#### 请求字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | `File` | 是 | 会议音频文件 |
| `lang_hint` | `string` | 否 | 音频语言提示，可选值 `man`、`can`、`eng` |
| `file_name` | `string` | 否 | 前端指定展示文件名；不传时使用上传文件名 |

#### 请求示例

```text
POST /meetings/upload
Content-Type: multipart/form-data

file=<weekly_sync.wav>
lang_hint=man
file_name=weekly_sync.wav
```

#### 成功响应

```json
{
  "success": true,
  "message": "meeting uploaded successfully",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "uploaded",
    "file_name": "weekly_sync.wav",
    "audio_asset": {
      "file_name": "weekly_sync.wav",
      "storage_path": "data/raw/mtg_20260402_001/weekly_sync.wav",
      "source_type": "uploaded_file",
      "duration": 1860.52,
      "sample_rate": 16000,
      "channels": 1,
      "lang_hint": "man"
    }
  },
  "error": null
}
```

#### 常见错误码

| code | 说明 |
| --- | --- |
| `UPLOAD_FILE_MISSING` | 未上传文件 |
| `UPLOAD_FILE_TYPE_UNSUPPORTED` | 文件格式不支持 |
| `UPLOAD_SAVE_FAILED` | 文件保存失败 |

### 2. 触发会议处理

| 项目 | 内容 |
| --- | --- |
| 接口路径 | `/meetings/process` |
| 请求类型 | `POST` |
| Content-Type | `application/json` |
| 当前状态 | 待实现 |

#### 请求字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `meeting_id` | `string` | 是 | 上传接口返回的会议 ID |
| `target_lang` | `string` | 否 | 目标处理语言，默认建议 `man` |
| `enable_translation` | `boolean` | 否 | 是否生成翻译结果，默认建议 `false` |
| `translation_target_lang` | `string` | 否 | 翻译目标语言，`enable_translation=true` 时使用 |
| `enable_summary` | `boolean` | 否 | 是否生成摘要，默认建议 `true` |

#### 请求示例

```json
{
  "meeting_id": "mtg_20260402_001",
  "target_lang": "man",
  "enable_translation": true,
  "translation_target_lang": "eng",
  "enable_summary": true
}
```

#### 成功响应

```json
{
  "success": true,
  "message": "meeting processing started",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "processing"
  },
  "error": null
}
```

#### 常见错误码

| code | 说明 |
| --- | --- |
| `MEETING_NOT_FOUND` | 未找到对应会议 |
| `MEETING_ALREADY_PROCESSING` | 会议正在处理中 |
| `MEETING_ALREADY_COMPLETED` | 会议已处理完成且不允许重复触发 |
| `PROCESS_REQUEST_INVALID` | 请求参数不合法 |

### 3. 查询会议状态

| 项目 | 内容 |
| --- | --- |
| 接口路径 | `/meetings/{meeting_id}` |
| 请求类型 | `GET` |
| Content-Type | 无请求体 |
| 当前状态 | 待实现 |

#### 路径参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `meeting_id` | `string` | 是 | 会议 ID |

#### 成功响应

```json
{
  "success": true,
  "message": "meeting status fetched successfully",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "completed",
    "file_name": "weekly_sync.wav",
    "created_at": "2026-04-02T21:10:00+08:00",
    "updated_at": "2026-04-02T21:18:00+08:00",
    "available_results": {
      "transcript": true,
      "translation": true,
      "summary": true
    }
  },
  "error": null
}
```

#### 状态枚举

| status | 说明 |
| --- | --- |
| `uploaded` | 音频已上传，尚未开始处理 |
| `processing` | 后端处理链路执行中 |
| `completed` | 处理完成，可查询结果 |
| `failed` | 处理失败 |

### 4. 获取转录结果

| 项目 | 内容 |
| --- | --- |
| 接口路径 | `/meetings/{meeting_id}/transcript` |
| 请求类型 | `GET` |
| Content-Type | 无请求体 |
| 当前状态 | 待实现 |

#### 路径参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `meeting_id` | `string` | 是 | 会议 ID |

#### 查询参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `include_translation` | `boolean` | 否 | 是否包含译文 |
| `target_lang` | `string` | 否 | 译文目标语言 |

#### 请求示例

```text
GET /meetings/mtg_20260402_001/transcript?include_translation=true&target_lang=eng
```

#### 成功响应

```json
{
  "success": true,
  "message": "transcript fetched successfully",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "completed",
    "transcript": [
      {
        "segment_id": "seg_0001",
        "start": 0.0,
        "end": 4.82,
        "speaker": "S1",
        "text": "大家好，我们开始本周例会。",
        "lang": "man",
        "source_lang": "man",
        "target_lang": "eng",
        "translation": "Hello everyone, let's begin this week's regular meeting."
      }
    ],
    "alignment_diagnostics": {
      "unknown_duration_rate": 0.0,
      "speaker_coverage_ratio": 1.0,
      "gap_count": 0.0,
      "unknown_duration_sec": 0.0,
      "total_aligned_duration_sec": 4.82,
      "segment_count": 1.0,
      "unknown_count": 0.0
    }
  },
  "error": null
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `segment_id` | `string` | 文本片段 ID；跨说话人拆分时可出现 `_a`、`_b` 后缀 |
| `start` | `number` | 片段开始时间，单位秒 |
| `end` | `number` | 片段结束时间，单位秒 |
| `speaker` | `string` | 说话人，格式为 `S1`、`S2`，无法判断时为 `UNKNOWN` |
| `text` | `string` | 原文文本 |
| `lang` | `string` | 原文语言 |
| `source_lang` | `string` | 翻译源语言；无翻译时可省略 |
| `target_lang` | `string` | 翻译目标语言；无翻译时可省略 |
| `translation` | `string` | 译文；无翻译时可省略 |

### 5. 获取摘要结果

| 项目 | 内容 |
| --- | --- |
| 接口路径 | `/meetings/{meeting_id}/summary` |
| 请求类型 | `GET` |
| Content-Type | 无请求体 |
| 当前状态 | 待实现 |

#### 路径参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `meeting_id` | `string` | 是 | 会议 ID |

#### 成功响应

```json
{
  "success": true,
  "message": "summary fetched successfully",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "completed",
    "summary": "本次会议完成了例会开场，并开始同步上周行动项进度。",
    "key_points": [
      "会议已正式开始。",
      "议题首先聚焦于上周行动项进度同步。"
    ],
    "action_items": [
      {
        "owner": "S2",
        "task": "补充上周行动项的详细进度说明"
      }
    ]
  },
  "error": null
}
```

#### 常见错误码

| code | 说明 |
| --- | --- |
| `MEETING_NOT_FOUND` | 未找到对应会议 |
| `SUMMARY_NOT_READY` | 摘要尚未生成 |
| `MEETING_NOT_COMPLETED` | 会议处理尚未完成 |

## 建议数据模型

### `AudioAsset`

```json
{
  "file_name": "weekly_sync.wav",
  "storage_path": "data/raw/mtg_20260402_001/weekly_sync.wav",
  "source_type": "uploaded_file",
  "duration": 1860.52,
  "sample_rate": 16000,
  "channels": 1,
  "lang_hint": "man"
}
```

### `TranscriptSegment`

```json
{
  "segment_id": "seg_0001",
  "start": 0.0,
  "end": 4.82,
  "speaker": "S1",
  "text": "大家好，我们开始本周例会。",
  "lang": "man",
  "confidence": 0.97
}
```

### `Summary`

```json
{
  "summary": "本次会议完成了例会开场，并开始同步上周行动项进度。",
  "key_points": [
    "会议已正式开始。",
    "议题首先聚焦于上周行动项进度同步。"
  ],
  "action_items": [
    {
      "owner": "S2",
      "task": "补充上周行动项的详细进度说明"
    }
  ]
}
```

## 前端联调建议

1. 开发初期先调用 `GET /health` 判断后端可用性。
2. 业务页面按 `上传 -> 触发处理 -> 轮询状态 -> 获取 transcript/summary` 的流程开发。
3. 轮询 `GET /meetings/{meeting_id}` 时，建议在 `status=completed` 后再请求 transcript 和 summary。
4. 前端展示层只依赖 `meeting_id`、`status`、`file_name`、`transcript`、`summary`、`key_points`、`action_items` 等业务字段。
5. `storage_path`、`sample_rate`、`channels`、`confidence`、`alignment_diagnostics` 可作为调试或详情页字段，普通用户界面不必默认展示。
