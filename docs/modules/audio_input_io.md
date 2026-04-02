# audio_input 模块 IO

## 模块职责

`audio_input` 模块负责接收会议音频输入，并输出统一的音频资源描述，供 `asr` 与 `diarization` 作为共同输入使用。

该模块关注的是“音频资源可被后续处理模块稳定消费”，不负责文本识别、说话人识别、翻译或摘要。

## 输入说明

输入应包含：

1. `meeting_id`
2. 音频文件基础信息
3. 存储路径或上传后落盘路径
4. 可选语言提示

建议输入字段：

1. `meeting_id`
2. `file_name`
3. `storage_path`
4. `source_type`
5. `lang_hint`

## 输出说明

输出为统一音频资源描述 `audio_asset`，供下游模块直接引用。

建议输出字段：

1. `meeting_id`
2. `audio_asset.file_name`
3. `audio_asset.storage_path`
4. `audio_asset.source_type`
5. `audio_asset.duration`
6. `audio_asset.sample_rate`
7. `audio_asset.channels`
8. `audio_asset.lang_hint`

## 输入示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "file_name": "weekly_sync.wav",
  "storage_path": "data/raw/mtg_20260402_001/weekly_sync.wav",
  "source_type": "uploaded_file",
  "lang_hint": "zh"
}
```

## 输出示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "status": "completed",
  "data": {
    "audio_asset": {
      "file_name": "weekly_sync.wav",
      "storage_path": "data/raw/mtg_20260402_001/weekly_sync.wav",
      "source_type": "uploaded_file",
      "duration": 1860.52,
      "sample_rate": 16000,
      "channels": 1,
      "lang_hint": "zh"
    }
  },
  "error": null
}
```

## 可能的错误情况

1. 音频文件不存在
2. 文件格式不支持
3. 音频为空或损坏
4. `meeting_id` 缺失
5. 存储路径不可访问

## 与下游 `asr` / `diarization` 的关系说明

`audio_input` 的输出是 `asr` 与 `diarization` 的共同输入来源。

明确约束：

1. `asr` 与 `diarization` 必须基于同一 `audio_asset`
2. `audio_input` 不直接调用下游模块
3. 下游模块不得自行修改 `audio_asset` 的核心标识字段
