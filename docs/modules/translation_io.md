# translation 模块 IO

## 模块职责

`translation` 模块负责基于融合后的 transcript 生成目标语言译文。

该模块必须保留原文内容，并在输出中新增翻译字段。

## 输入说明

输入基于 `alignment` 输出的 `aligned_transcript`。

建议输入字段：

1. `meeting_id`
2. `target_lang`
3. `aligned_transcript`

## 输出说明

输出在原有 transcript 基础上保留原文，并新增翻译相关字段。

建议每个输出 segment 包含：

1. `segment_id`
2. `start`
3. `end`
4. `speaker`
5. `text`
6. `lang`
7. `source_lang`
8. `target_lang`
9. `translation`

## 字段说明

1. `source_lang`：原文语言
2. `target_lang`：目标语言
3. `translation`：译文内容

## 输入示例 JSON

```json
{
  "meeting_id": "mtg_20260402_001",
  "target_lang": "en",
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
    "translated_transcript": [
      {
        "segment_id": "seg_0001",
        "start": 0.00,
        "end": 4.82,
        "speaker": "S1",
        "text": "大家好，我们开始本周例会。",
        "lang": "zh",
        "source_lang": "zh",
        "target_lang": "en",
        "translation": "Hello everyone, let's begin this week's regular meeting."
      },
      {
        "segment_id": "seg_0002_a",
        "start": 5.10,
        "end": 6.20,
        "speaker": "S1",
        "text": "先同步一下",
        "lang": "zh",
        "source_lang": "zh",
        "target_lang": "en",
        "translation": "First, let us quickly sync."
      }
    ]
  },
  "error": null
}
```

## 错误情况

1. `aligned_transcript` 为空
2. 目标语言缺失
3. 翻译模型执行失败
4. 源语言无法识别或不支持
5. 输出译文为空

## 职责边界说明

`translation` 基于融合后的 transcript 处理。

明确约束：

1. 不直接处理原始音频
2. 不重新识别 speaker
3. 不改写原始 `text`
4. 仅在原 transcript 基础上追加翻译字段
