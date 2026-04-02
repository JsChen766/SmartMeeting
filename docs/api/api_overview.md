# API 总览

## API 层的职责

API 层负责连接前端与后端处理链路，对外提供统一入口和查询出口。

主要职责包括：

1. 接收文件上传请求
2. 接收处理触发请求
3. 提供任务状态查询
4. 提供 transcript 与摘要结果查询
5. 向前端返回统一格式的成功或失败响应

API 层不负责实现底层 ASR、diarization、translation、summarization 算法本身。

## 前端与后端交互方式说明

前端与后端建议采用标准 HTTP API 方式交互。

基础协作模式如下：

1. 前端上传会议音频
2. 后端生成 `meeting_id` 并返回上传结果
3. 前端根据 `meeting_id` 触发处理任务
4. 前端轮询查询任务状态
5. 任务完成后获取 transcript 与摘要结果

## 三类接口的概念说明

### 文件上传

用于提交会议音频资源，完成会议任务初始化。

### 任务触发

用于明确要求后端开始执行处理流水线。这样可以把“上传成功”和“正式处理”解耦，方便后续扩展参数控制。

### 结果查询

用于获取会议基础信息、处理状态、transcript 和 summary 等结果。

## 建议的处理模式

建议采用：

1. 先上传
2. 后处理
3. 再查询结果

即：

1. `POST /meetings/upload`
2. `POST /meetings/process`
3. `GET /meetings/{meeting_id}`
4. `GET /meetings/{meeting_id}/transcript`
5. `GET /meetings/{meeting_id}/summary`

这种模式的优点：

1. 处理流程更清晰
2. 前端可以独立控制何时开始处理
3. 更适合异步任务型场景

## 状态流转建议

建议使用以下任务状态：

1. `uploaded`
2. `processing`
3. `completed`
4. `failed`

建议含义：

1. `uploaded`：文件已上传，但尚未开始处理
2. `processing`：流水线处理中
3. `completed`：处理完成，可查询结果
4. `failed`：处理失败，可返回错误信息

如需细化，可在内部扩展模块级状态，但对前端优先保持主状态稳定。
