# 请求响应格式规范

## 前后端统一请求/响应格式

前后端交互建议统一采用如下外层结构：

```json
{
  "success": true,
  "message": "request succeeded",
  "data": {},
  "error": null
}
```

说明：

1. `success`：请求是否成功
2. `message`：简要说明
3. `data`：业务数据
4. `error`：错误对象，成功时为 `null`

## 成功响应格式

```json
{
  "success": true,
  "message": "meeting uploaded successfully",
  "data": {
    "meeting_id": "mtg_20260402_001"
  },
  "error": null
}
```

## 失败响应格式

```json
{
  "success": false,
  "message": "request failed",
  "data": null,
  "error": {
    "code": "MEETING_NOT_FOUND",
    "message": "未找到对应的 meeting_id",
    "details": {
      "meeting_id": "mtg_20260402_001"
    }
  }
}
```

## 上传音频请求格式

上传接口通常使用文件上传能力，配套元数据可参考以下 JSON 语义：

```json
{
  "file_name": "weekly_sync.wav",
  "lang_hint": "zh"
}
```

建议成功响应：

```json
{
  "success": true,
  "message": "meeting uploaded successfully",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "uploaded",
    "file_name": "weekly_sync.wav",
    "storage_path": "data/raw/mtg_20260402_001/weekly_sync.wav"
  },
  "error": null
}
```

## 获取处理结果响应格式

建议用于 `GET /meetings/{meeting_id}`：

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

## transcript 返回格式

建议用于 `GET /meetings/{meeting_id}/transcript`：

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
        "start": 0.00,
        "end": 4.82,
        "speaker": "S1",
        "text": "大家好，我们开始本周例会。",
        "lang": "zh",
        "translation": "Hello everyone, let's begin this week's regular meeting."
      },
      {
        "segment_id": "seg_0002_a",
        "start": 5.10,
        "end": 6.20,
        "speaker": "S1",
        "text": "先同步一下",
        "lang": "zh",
        "translation": "First, let us quickly sync."
      }
    ]
  },
  "error": null
}
```

## summary 返回格式

建议用于 `GET /meetings/{meeting_id}/summary`：

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

## 完整 JSON 示例

以下示例表示一次已处理完成的会议结果查询：

```json
{
  "success": true,
  "message": "meeting status fetched successfully",
  "data": {
    "meeting_id": "mtg_20260402_001",
    "status": "completed",
    "file_name": "weekly_sync.wav",
    "available_results": {
      "transcript": true,
      "translation": true,
      "summary": true
    }
  },
  "error": null
}
```

## 前端展示字段与后端内部字段

### 建议给前端展示的字段

1. `meeting_id`
2. `status`
3. `file_name`
4. `segment_id`
5. `start`
6. `end`
7. `speaker`
8. `text`
9. `lang`
10. `translation`
11. `summary`
12. `key_points`
13. `action_items`

### 建议仅在后端内部使用的字段

1. `storage_path`
2. `sample_rate`
3. `channels`
4. `confidence`
5. 模块级内部日志字段
6. 模型版本或内部调试字段

原则：

1. 前端只获取展示、查询和业务交互所需字段
2. 后端内部处理细节不直接暴露给前端，避免接口耦合过深
