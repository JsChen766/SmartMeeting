# API 接口规格建议

本文档定义建议接口，不代表当前已有实现。接口风格以 FastAPI 风格后端为参考。

## `POST /meetings/upload`

### 用途

上传会议音频并初始化会议任务。

### 请求参数

建议请求包含：

1. 音频文件
2. 可选 `lang_hint`
3. 可选 `file_name`

### 响应字段

成功响应建议返回：

1. `meeting_id`
2. `status`
3. `file_name`
4. `storage_path`

### 常见错误响应

1. 文件缺失
2. 文件格式不支持
3. 上传失败

## `POST /meetings/process`

### 用途

触发指定会议的处理流水线。

### 请求参数

```json
{
  "meeting_id": "mtg_20260402_001",
  "target_lang": "en"
}
```

建议字段：

1. `meeting_id`
2. `target_lang`（可选）

### 响应字段

成功响应建议返回：

1. `meeting_id`
2. `status`
3. `message`

### 常见错误响应

1. `meeting_id` 不存在
2. 会议已在处理中
3. 会议已处理完成且不允许重复触发

## `GET /meetings/{meeting_id}`

### 用途

查询会议任务基础信息与处理状态。

### 请求参数

路径参数：

1. `meeting_id`

### 响应字段

成功响应建议返回：

1. `meeting_id`
2. `status`
3. `file_name`
4. `created_at`
5. `updated_at`
6. `available_results`

### 常见错误响应

1. `meeting_id` 不存在
2. 查询失败

## `GET /meetings/{meeting_id}/transcript`

### 用途

获取会议融合后的 transcript，必要时可包含翻译结果。

### 请求参数

路径参数：

1. `meeting_id`

可选查询参数建议：

1. `include_translation`
2. `target_lang`

### 响应字段

成功响应建议返回：

1. `meeting_id`
2. `status`
3. `transcript`

其中 `transcript` 每项建议包含：

1. `segment_id`
2. `start`
3. `end`
4. `speaker`
5. `text`
6. `lang`
7. `translation`（可选）

### 常见错误响应

1. 会议不存在
2. transcript 尚未生成
3. 会议处理未完成

## `GET /meetings/{meeting_id}/summary`

### 用途

获取会议摘要结果。

### 请求参数

路径参数：

1. `meeting_id`

### 响应字段

成功响应建议返回：

1. `meeting_id`
2. `status`
3. `summary`
4. `key_points`
5. `action_items`（可选）

### 常见错误响应

1. 会议不存在
2. summary 尚未生成
3. 会议处理未完成

## 接口设计补充说明

### 风格建议

1. 上传接口与处理接口分离
2. 查询接口使用 `GET`
3. 所有接口统一返回 `meeting_id`
4. 所有错误响应使用统一 `error` 结构

### 与模块层的关系

API 不直接暴露内部模块细节，但其返回字段应可映射到模块产物：

1. transcript 对应 `alignment` 或 `translation` 输出
2. summary 对应 `summarization` 输出
3. 状态字段映射 pipeline 执行状态
