# asr 模块 IO

## 模块职责

`asr` 模块负责将音频内容转换为文本片段，输出 `transcript segments`。

本模块只负责文本内容识别，不负责说话人识别。

## 输入说明

输入基于 `audio_input` 输出的 `audio_asset`。

建议输入字段：

1. `meeting_id`
2. `audio_asset.file_name`
3. `audio_asset.storage_path`
4. `audio_asset.lang_hint`

## 输出说明

输出为 `transcript segments` 列表。

每个 segment 建议包含：

1. `segment_id`
2. `start`
3. `end`
4. `text`
5. `lang`
6. `confidence`（可选）

## 字段说明

1. `segment_id`：文本片段唯一标识，例如 `seg_0001`
2. `start`：文本片段起始时间，单位秒
3. `end`：文本片段结束时间，单位秒
4. `text`：识别出的原文文本
5. `lang`：该文本片段的语言
6. `confidence`：可选，表示识别置信度

## 输入示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "audio_asset": {
    "file_name": "weekly_sync.wav",
    "storage_path": "data/raw/mtg_20260402_001/weekly_sync.wav",
    "source_type": "uploaded_file",
    "duration": 1860.52,
    "sample_rate": 16000,
    "channels": 1,
    "lang_hint": "zh"
  }
}
```

## 输出示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "status": "completed",
  "data": {
    "asr_segments": [
      {
        "segment_id": "seg_0001",
        "start": 0.00,
        "end": 4.82,
        "text": "大家好，我们开始本周例会。",
        "lang": "zh",
        "confidence": 0.97
      },
      {
        "segment_id": "seg_0002",
        "start": 5.10,
        "end": 9.40,
        "text": "先同步一下上周行动项进度。",
        "lang": "zh",
        "confidence": 0.95
      }
    ]
  },
  "error": null
}
```

## 错误情况

1. 音频资源不存在
2. 音频无法解码
3. ASR 模型处理失败
4. 输出片段为空
5. `meeting_id` 与音频资源不匹配

## 职责边界说明

`asr` 负责文本内容，不负责 speaker 识别。

明确约束：

1. `asr` 不输出 `speaker`
2. `speaker` 字段由 `diarization` 与 `alignment` 链路补充
3. 如果需要说话人归属，必须依赖下游 `alignment` 输出
