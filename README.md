# my-agent

逐步构建可运行的 Agent，分别记录工程进展和学习掌握情况。

当前能力：通过内网 OpenAI 兼容接口调用 `v4.1flash`，在终端流式显示一次中文回答；也可从一句话提取任务名称和优先级，经过本地校验后输出 JSON。尚未加入多轮对话、工具调用或自动重试。

## 运行

需要 Python 3.10+，无第三方依赖。在项目根目录执行：

```bash
cp .env.example .env  # 仅首次配置时执行，已有 .env 请勿覆盖
chmod 600 .env
# 用编辑器在 .env 中填写 OPENAI_API_KEY
python3 -m src.chat '你好，请介绍一下自己。'
```

每次命令发起一次真实模型请求，需要能够访问内网接口。Token 只保存在 `.env`，该文件已被 Git 忽略。不要在命令、日志或提交中粘贴 Token。

程序使用 `stream: true`，从 SSE 事件的 `choices[0].delta.content` 提取增量文本，收到 `[DONE]` 后标记完成。回答写入 stdout，调用状态和错误写入 stderr。流中断时已显示的内容可能不完整，程序会返回非零退出码。

```bash
python3 -m src.chat '只回复：你好' --timeout 30
python3 -m unittest discover -s tests -v
```

`--timeout` 控制网络阻塞等待时间，不是整次生成的总时限。当前 `.env` 解析仅支持简单的 `KEY=value` 和整行注释，不支持变量展开或多行值。

## 已执行验证

- 真实接口：`python3 -m src.chat '请只用一句简短中文介绍你自己。' --timeout 30`，成功返回中文回答并正常结束。
- 真实异常：在内存中将配置的 Token 替换为无效值，接口返回 HTTP 401，程序给出认证失败提示；未修改本地真实 Token。
- 本地 HTTP 协议测试：6 项通过，覆盖请求体、中文 SSE、空 choices、认证失败、损坏事件、非 SSE 响应、流提前结束和缺少 Token。此类测试不替代真实模型验证。

## 任务信息提取

```bash
python3 -m src.structured '高优先级：明天整理面试笔记' --timeout 30
python3 -m src.structured '整理面试笔记' --timeout 30
python3 -m unittest discover -s tests -v
```

输入是一条任务描述；输出只包含 `title`（非空字符串）和 `priority`（低／中／高），未指定优先级时通过 prompt 约定为“中”。成功时 stdout 输出一条 JSON；错误和状态写入 stderr，失败退出码为 1。程序不创建任务或提醒，也不保存数据。

使用非流式请求，在 `finish_reason=stop`、无拒绝且本地校验通过后才输出完整数据。截断、非法 JSON、缺字段、多余字段、空标题及非法优先级均拒绝；不修补模型输出，也不自动重试。

**兼容性实测（2026-11-02）：** 内网接口接受 `json_schema`（含 `strict: true`）及 `json_object`，正常提取均返回合法 JSON；但冲突探测中，Schema 要求整数标题和仅允许“低”，模型仍返回字符串标题和“高”。因此当前接口不能依赖服务端严格约束，实际边界为 prompt 约定加本地校验。程序继续发送 Schema 表达契约，不自动降级；HTTP 400 会明确报错。

**反代源码核对：** 用户确认这是 DeepSeek 网页版反代。按部署记录对应的 [DeeperSeeker `afe8d266d2ba`](https://github.com/AmanCode22/deeperseeker/blob/afe8d266d2ba/app.py)，网页 Chat Completions 分支忽略 `response_format`，所以当前请求携带的 Schema 不生效，不能称为服务端 Structured Outputs；`system` 会被拼成文本提示词。普通非流式响应由反代填写 `finish_reason=stop`，不能据此保证网页上游没有截断。客户端仍保留结束状态检查，但本阶段实际能力为 prompt 提取加本地校验。

真实正常调用分别得到“高”和默认“中”，无效 Token 得到 HTTP 401；本地协议及校验测试覆盖失败路径。这些结果不代表所有输入都能正确提取；本地校验不能验证标题语义或默认优先级是否忠实于原文。

学习状态见 [学习索引](docs/learning/index.md) 和 [当前阶段记录](docs/learning/stage-02-structured-output.md)。
