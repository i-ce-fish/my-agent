# my-agent

逐步构建可运行的 Agent，分别记录工程进展和学习掌握情况。

当前能力：通过内网 OpenAI 兼容接口调用 `v4.1flash`，在终端流式显示一次中文回答；处理缺少配置、认证失败、网络超时、响应格式错误和流提前结束。尚未加入多轮对话、工具调用或自动重试。

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

学习状态见 [学习索引](docs/learning/index.md) 和 [当前阶段记录](docs/learning/stage-01-llm-api.md)。
