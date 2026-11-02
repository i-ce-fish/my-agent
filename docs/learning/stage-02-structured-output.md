# 第二阶段：任务信息结构化提取

## 阶段目标和应用场景

从一句任务描述提取 `title` 和 `priority`，让程序消费经过校验的数据；区分 JSON 合法、字段合规与语义正确。不涉及任务持久化、提醒、多轮、工具调用或自动重试。

## 迭代记录

- 2026-11-02：用户确认最小范围；新增 `src/structured.py` 和 `tests/test_structured.py`，复用配置读取，以非流式请求和本地校验实现任务提取。
- 2026-11-02：真实调用及本地测试通过，发现服务端未强制 Schema；用户完成流程复述及 Level 1 小测，并通过本地校验语义边界验收，待其余核心 REVIEW 与功能验收确认。
- 本轮收尾：用户独立提出批量测试、通过率及新数据测试防止过拟合，并识别客户端超时与重复生成风险；用户要求暂停反代专题、跳过简单与重复问题，继续项目主线。

## 知识点

| 名称 | 状态 | 代码位置 | 备注 |
| --- | --- | --- | --- |
| prompt、JSON mode 与严格 Schema 的边界 | LEARNING | `src/structured.py:TASK_SCHEMA`、`SYSTEM_PROMPT` | 用户说明为网页版反代；部署版本源码的网页分支忽略 response_format，本阶段实际为 prompt 提取加本地校验 |
| 模型输出的本地校验与语义边界 | MASTERED | `src/structured.py:parse_task` | 用户独立判断原文“低”而输出“高”仍被接受；已补充本地也检查类型和枚举，但不核对原文语义 |
| 完成状态、拒绝与输出时机 | PRACTICED | `src/structured.py:extract_task`、`main` | Level 1 length 小测通过；反代 stop 语义 REVIEW 未通过：知道存在不确定性，但仍认为可视为上游未截断，需复核固定 stop 丢失结束原因的边界 |
| 固定评测样本与泛化验证 | MASTERED | 暂无评测代码 | 用户提出百组样本统计通过率、使用新数据测试防止过拟合；独立测试集不参与调参的规则已补充 |
| 超时诊断与有限重试 | PRACTICED | `src/structured.py:extract_task`（无重试） | 用户区分客户端与中转超时，指出重复生成风险并提出次数上限；总时间预算已补充，未实现自动重试 |

## 关键实验结论与待办

- 同一句高优先级任务：旧版本返回自然语言并声称“记下了”，实际没有保存；新版本输出经过校验的两个字段，也不保存任务。
- `json_schema` 和 `json_object` 均被接口接受；冲突 Schema 要求整数标题及仅允许“低”，响应却为字符串标题和“高”，不能依赖服务端严格结构约束。
- 用户澄清使用 DeepSeek 网页版反代。按本地部署记录对应的 DeeperSeeker `afe8d266d2ba` 源码：网页 Chat Completions 分支不转发 `response_format`、`temperature`、`max_tokens`、`top_p`、`stop`；system 内容经 `build_prompt` 拼成文本，不能假定原生角色优先级。
- 该版本 `format_response` 将普通非流式响应的 `finish_reason` 填为 `stop`，工具调用填为 `tool_calls`，没有在这里映射原始长度截断原因。此前 length 小测是通用协议防御逻辑，不能声称当前内网真实返回过 length，也不能凭 stop 排除全部截断。
- 源码依据：[app.py](https://github.com/AmanCode22/deeperseeker/blob/afe8d266d2ba/app.py)、[plugin_helper.py](https://github.com/AmanCode22/deeperseeker/blob/afe8d266d2ba/plugin_helper.py)、[functions.py](https://github.com/AmanCode22/deeperseeker/blob/afe8d266d2ba/functions.py)。本轮仅核对源码与修正文档，未修改客户端或线上服务。
- 正常描述得到“高”，未指定优先级得到“中”；真实无效 Token 返回 HTTP 401；本地测试拒绝非法 JSON、字段错误、截断及拒绝响应。
- 共 14 项测试通过（新增 8 项）；全量运行有旧流式模块的资源关闭警告，单独运行旧测试可复现，新增模块单独运行无此警告；未改动旧模块。
- 当前仅对一个任务提取两个字段；“未指定优先级时为中”依赖 prompt，程序未做语义复核；未测量成功率、成本和延迟。
- 工程成果已验证，用户完成流程复述和小测；本地校验语义边界及泛化评测思路已 MASTERED，其余状态见表。功能验收的查看确认及全部核心 REVIEW 尚未完成，阶段不标为已完成；保留待办可继续开发。
- 反代专题按用户要求暂缓，不作为继续主线的阻塞项；后续只针对未验证的工程取舍、失败边界和迁移场景验收，跳过简单和已验收问题。
- 阶段最终收尾时仍需用户先写一分钟项目叙述，AI 再补充；不由 AI 代写用户成果。
