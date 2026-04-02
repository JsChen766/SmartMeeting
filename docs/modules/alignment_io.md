# alignment 模块 IO

## 模块职责

`alignment` 模块负责将 `asr_segments` 与 `speaker_segments` 按时间戳融合，输出带说话人归属的 transcript。

该模块的目标是形成稳定可消费的 `speaker-attributed transcript`。

## 输入说明

输入由以下两部分组成：

1. `asr_segments`
2. `speaker_segments`

建议输入字段：

1. `meeting_id`
2. `asr_segments`
3. `speaker_segments`

## 输出说明

输出为 `speaker-attributed transcript`。

每个输出 segment 建议包含：

1. `segment_id`
2. `start`
3. `end`
4. `speaker`
5. `text`
6. `lang`

## 字段说明

1. `segment_id`：沿用 ASR 片段标识，必要时允许拆分生成新标识
2. `start`：融合后片段起始时间，单位秒
3. `end`：融合后片段结束时间，单位秒
4. `speaker`：说话人标识，例如 `S1`
5. `text`：该说话片段对应文本
6. `lang`：该文本片段语言

## 输入示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
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
  ],
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
}
```

## 输出示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "status": "completed",
  "data": {
    "aligned_transcript": [
      {
        "segment_id": "seg_0001",
        "start": 0.00,
        "end": 4.82,
        "speaker": "S1",
        "text": "大家好，我们开始本周例会。",
        "lang": "zh"
      },
      {
        "segment_id": "seg_0002_a",
        "start": 5.10,
        "end": 6.20,
        "speaker": "S1",
        "text": "先同步一下",
        "lang": "zh"
      },
      {
        "segment_id": "seg_0002_b",
        "start": 6.20,
        "end": 9.40,
        "speaker": "S2",
        "text": "上周行动项进度。",
        "lang": "zh"
      }
    ]
  },
  "error": null
}
```

## 时间戳对齐规则说明

建议采用以下规则：

1. 以时间重叠关系为基础进行融合
2. 若一个 ASR 片段完全落在单一 speaker 区间内，则直接赋值该 speaker
3. 若一个 ASR 片段跨越多个 speaker 区间，则允许拆分为多个输出片段
4. 拆分后片段的 `start`、`end` 必须与对应 speaker 区间一致
5. 拆分后 `segment_id` 可在原始 `segment_id` 基础上追加后缀，例如 `_a`、`_b`

## 边界情况说明

### 一个文本段跨多个 speaker

处理建议：

1. 按重叠时间切分文本段
2. 输出多个对齐后的 segment
3. 保证每个 segment 只对应一个 `speaker`

### speaker 区间与 text 区间部分重叠

处理建议：

1. 以重叠区间为准分配 speaker
2. 若重叠比例不足设定阈值，可标记为 `UNKNOWN`
3. 阈值策略由实现层决定，但输出格式保持一致

### speaker 缺失时如何处理

处理建议：

1. 输出 `speaker: "UNKNOWN"`
2. 不丢弃文本内容
3. 保留 `segment_id`、`start`、`end`、`text`、`lang`，确保下游仍可处理
