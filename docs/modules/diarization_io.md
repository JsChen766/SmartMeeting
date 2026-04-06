# diarization 模块 IO

## 模块职责

`diarization` 模块负责识别音频中的说话人切换区间，输出 `speaker segments`。

本模块不负责生成文本，只负责回答“在什么时间段是谁在说话”。

## 输入说明

输入基于后端接入阶段准备好的 `audio_asset`。

建议输入字段：

1. `meeting_id`
2. `audio_asset.file_name`
3. `audio_asset.storage_path`
4. `audio_asset.duration`

## 输出说明

输出为 `speaker segments` 列表。

每个 segment 建议包含：

1. `start`
2. `end`
3. `speaker`

## 字段说明

1. `start`：说话区间起始时间，单位秒
2. `end`：说话区间结束时间，单位秒
3. `speaker`：说话人标识，采用 `S1`、`S2` 等统一命名

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
    "speaker_segments": [
      {
        "start": 0.00,
        "end": 6.20,
        "speaker": "S1"
      },
      {
        "start": 6.20,
        "end": 11.40,
        "speaker": "S2"
      }
    ]
  },
  "error": null
}
```

## 错误情况

1. 音频文件不存在
2. 音频时长异常
3. diarization 模型执行失败
4. 无法输出有效 speaker 区间
5. `meeting_id` 缺失或不匹配

## 职责边界说明

说话人分离基于音频，不基于文本。

明确约束：

1. `diarization` 不读取 ASR 文本作为主要输入
2. `diarization` 不输出 `text`
3. 最终 speaker-attributed transcript 由 `alignment` 负责生成
