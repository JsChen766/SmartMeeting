# summarization 模块 IO

## 模块职责

`summarization` 模块负责基于完整 transcript 生成会议摘要结果。

输出至少包含：

1. `summary`
2. `key_points`

可选包含：

1. `action_items`

## 输入说明

输入应为完整 transcript，而不是单纯原始音频。

建议输入字段：

1. `meeting_id`
2. `aligned_transcript`
3. `target_lang`（可选，表示摘要输出语言）

## 输出说明

建议输出字段：

1. `meeting_id`
2. `summary`
3. `key_points`
4. `action_items`（可选）

## 输入示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "target_lang": "zh",
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
}
```

## 输出示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "status": "completed",
  "data": {
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

## 错误情况

1. transcript 输入为空
2. transcript 片段不完整
3. 摘要模型执行失败
4. 输出摘要为空
5. 指定输出语言不支持

## 职责边界说明

摘要模块输入是完整 transcript，而不是单纯原始音频。

明确约束：

1. `summarization` 不直接处理音频
2. `summarization` 不负责 speaker 识别
3. `summarization` 不负责文本翻译以外的中间融合逻辑
4. 若需要使用译文做摘要，应由 pipeline 明确传入对应 transcript
