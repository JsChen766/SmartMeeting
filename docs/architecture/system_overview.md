# 系统总览

## 项目简介

Smart Meeting Assistant 是一个会议内容处理项目，用于将会议音频转为结构化文本、说话人归属、翻译结果与摘要结果，供前端展示与后续扩展使用。

本项目当前采用“前端 + 后端处理层 + 数据目录”的结构，不引入 Tauri 或 Rust，优先围绕 Python + FastAPI 风格后端和前端展示层建立清晰接口。

## 项目目标

1. 建立统一的会议处理链路，从音频输入到摘要输出形成稳定流程。
2. 在模块层明确输入输出边界，降低并行开发成本。
3. 先完成文档驱动的接口定义，再进入编码实现。
4. 为后续支持多语言、模型替换和能力扩展保留结构空间。

## 核心功能范围

当前版本仅覆盖以下能力：

1. 录音转文字（ASR）
2. 说话人分离、文本与说话人时间戳对齐融合、多语言处理
3. 翻译与 LLM 摘要

## 非目标范围

当前阶段明确不做以下内容：

1. 视频会议平台能力
2. 多人视频房间管理
3. 实时音视频通信基础设施
4. 会议日历、会议邀请、账号体系等外围平台功能
5. 部署、运维、CI/CD、数据库迁移等工程化交付内容

## 总体流程说明

系统核心处理流程如下：

`backend ingest -> asr + diarization -> alignment -> translation / summarization -> api/frontend`

流程说明：

1. `backend ingest` 负责接收上传、落盘、转码、规范化音频，并生成统一的音频资源描述。
2. `asr` 基于音频生成 transcript segments。
3. `diarization` 基于同一音频生成 speaker segments。
4. `alignment` 将文本片段与说话人片段按时间戳融合，输出带 speaker 的 transcript。
5. `translation` 基于融合后的 transcript 生成目标语言文本。
6. `summarization` 基于完整 transcript 生成摘要、要点和行动项。
7. `api/frontend` 负责触发处理、查询状态和展示结果。

## 前后端职责划分

### frontend

前端负责：

1. 上传会议音频或提交处理请求
2. 查询任务状态
3. 展示 transcript、翻译结果、摘要结果
4. 向后端传递用户选择的处理参数，例如目标语言

前端不负责：

1. 直接执行 ASR、说话人分离、翻译或摘要算法
2. 决定模块内部处理逻辑
3. 直接操作原始数据目录

### backend

后端负责：

1. 接收上传请求和处理请求
2. 调度各模块执行顺序
3. 管理 meeting_id 和各阶段产物
4. 对外提供统一 API 响应
5. 组织中间结果与最终结果的持久化路径

## `backend/modules` 与 `backend/pipelines` 的区别

### `backend/modules`

用于存放单一能力模块。每个模块只关心自己的输入、输出与局部处理逻辑，例如：

1. `asr`
2. `diarization`
3. `alignment`
4. `translation`
5. `summarization`

模块层强调：

1. 输入输出清晰
2. 职责边界单一
3. 可替换具体实现

### `backend/pipelines`

用于组织跨模块的编排逻辑。pipeline 负责决定：

1. 先执行哪些模块
2. 哪些模块可以并行
3. 模块失败时如何中止或返回状态
4. 如何把中间产物传给下游模块

简化理解：

- `modules` 负责“做什么”
- `pipelines` 负责“按什么顺序把它们串起来”

## `data` 目录的用途

### `data/raw`

用于存放原始输入资源，例如上传的音频文件或其统一落盘副本。

### `data/processed`

用于存放中间处理产物，例如：

1. 后端接入阶段生成的音频描述
2. ASR segments
3. diarization segments
4. alignment 输出

### `data/outputs`

用于存放面向业务消费的最终结果，例如：

1. 最终 transcript
2. 翻译结果
3. 摘要结果
4. 可供 API 返回的聚合 JSON
