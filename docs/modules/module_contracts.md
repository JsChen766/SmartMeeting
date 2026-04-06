# 模块契约统一规范

## 统一规则

所有后端模块必须遵循以下规则：

1. 只关注本模块职责范围内的输入与输出
2. 输入输出使用统一的 JSON 描述格式
3. 所有模块都必须接收并返回 `meeting_id`
4. 模块之间通过显式字段对接，不依赖隐式上下文
5. 不在本模块内直接修改其他模块的内部逻辑或实现细节

## JSON 输入输出约定

所有模块统一使用 JSON 作为输入输出描述格式。即使底层处理对象是音频文件或模型结果，对接层也必须有对应 JSON 元数据结构。

建议顶层基础结构：

```json
{
  "meeting_id": "mtg_20260402_001",
  "status": "completed",
  "data": {},
  "error": null
}
```

说明：

1. `meeting_id`：会议处理链路唯一标识
2. `status`：当前模块处理状态
3. `data`：模块有效输出
4. `error`：错误信息，成功时为 `null`

## 字段命名规范

统一使用 `snake_case`。

推荐字段命名方式：

1. 标识类：`meeting_id`、`segment_id`
2. 时间类：`start`、`end`、`duration`
3. 语言类：`lang`、`source_lang`、`target_lang`
4. 路径类：`storage_path`、`file_name`
5. 状态类：`status`

避免混用：

1. `meetingId`
2. `speakerId`
3. `start_time`
4. `begin`

## 时间字段规范

所有时间字段统一使用“秒”为单位，采用数值类型表示，可保留小数。

示例：

```json
{
  "start": 12.34,
  "end": 18.90
}
```

## `meeting_id` 贯穿要求

`meeting_id` 必须贯穿所有模块与 API 响应，用于：

1. 标识同一次会议处理任务
2. 关联中间产物与最终产物
3. 前端轮询或查询结果
4. 排查错误与日志定位

## speaker 命名规范

统一采用 `S1`、`S2`、`S3` 形式。

规范要求：

1. 由 diarization 或 alignment 输出统一编号
2. 不直接暴露底层模型原始标签，如 `speaker_0`
3. 当 speaker 无法确定时，允许使用 `UNKNOWN`

## lang 命名建议

语言字段推荐使用简洁语言码：

1. `zh`：普通话中文
2. `en`：英文
3. `yue`：粤语

如果后续扩展，应继续保持短码一致性，避免同一语言混用多种写法。

## 错误返回格式规范

统一错误结构如下：

```json
{
  "meeting_id": "mtg_20260402_001",
  "status": "failed",
  "data": null,
  "error": {
    "code": "ASR_AUDIO_NOT_FOUND",
    "message": "未找到对应音频资源",
    "details": {
      "storage_path": "data/raw/mtg_20260402_001/original.wav"
    }
  }
}
```

字段说明：

1. `code`：稳定可枚举的错误码
2. `message`：给开发协作与日志使用的错误说明
3. `details`：可选附加上下文

## 模块职责边界

各模块边界如下：

1. 后端接入阶段负责音频接收、转码与规范化描述
2. `asr` 负责文本识别，不负责 speaker 识别
3. `diarization` 负责 speaker 时间片段识别，不负责文本生成
4. `alignment` 负责按时间戳融合文本与 speaker
5. `translation` 负责基于融合 transcript 生成译文
6. `summarization` 负责基于完整 transcript 生成摘要

统一原则：

1. 模块只负责自己的输入输出
2. 模块不得直接改写其他模块的内部实现
3. 上下游协作依赖契约字段，不依赖模块内部状态
