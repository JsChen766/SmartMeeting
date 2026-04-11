# Smart Meeting Assistant

## 项目简介

Smart Meeting Assistant 是一个面向会议音频处理场景的助手型项目，目标是把会议音频转换为可检索、可翻译、可摘要的结构化结果。本项目不是视频会议平台，不负责多人视频房间、实时视频通话或会议基础设施。

当前核心能力聚焦于三类处理链路：

1. 录音转文字（ASR）
2. 说话人分离 + 对齐融合 + 多语言相关处理
3. 翻译 + LLM 摘要

## 当前目录结构说明

```text
project-root/
├── docs/
│   ├── architecture/
│   ├── api/
│   └── modules/
├── frontend/
│   ├── public/
│   └── src/
├── backend/
│   ├── app/
│   ├── modules/
│   ├── pipelines/
│   ├── schemas/
│   └── utils/
└── data/
    ├── raw/
    ├── processed/
    └── outputs/
```

## docs 文档用途概览

- `docs/architecture/system_overview.md`：说明项目定位、范围、总体分层与数据流。
- `docs/architecture/pipeline_design.md`：说明处理流水线执行顺序、并行关系与中间产物。
- `docs/modules/module_contracts.md`：统一模块输入输出约束、字段命名和错误格式。
- `docs/modules/asr_io.md`：定义 ASR 模块的输入输出。
- `docs/modules/diarization_io.md`：定义说话人分离模块的输入输出。
- `docs/modules/alignment_io.md`：定义文本与说话人时间戳融合规则。
- `docs/modules/translation_io.md`：定义翻译模块的输入输出。
- `docs/modules/summarization_io.md`：定义摘要模块的输入输出。
- `docs/api/api_overview.md`：说明 API 层职责和前后端协作方式。
- `docs/api/endpoints_spec.md`：定义建议接口及其请求响应。
- `docs/api/request_response_schema.md`：统一前后端请求响应格式和展示字段。

## 开发顺序建议

1. 先定 `module_contracts`
2. 再定各模块 IO
3. 再定 API 交互
4. 最后开始编码

## 如何运行后端模块

1. **创建虚拟环境** (Python 3.10):
   ```bash
   cd backend
   py -3.10 -m venv venv
   .\venv\Scripts\activate
   ```

2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

3. **运行测试**:
   ```bash
   python tests/test_nlp.py
   ```

4. **启动 FastAPI 服务**:
   ```bash
   uvicorn app.main:app --reload
   ```
