# 知识点记录（旧版）

当前状态已迁移至 [第一阶段记录](stage-01-llm-api.md)。下方保留迁移前记录，不再更新。

| 知识点 | 状态 | 对应代码 | 待复习原因 |
| --- | --- | --- | --- |
| messages 中 system / user 的作用及请求数据流 | LEARNING | `src/chat.py:stream_chat` | 已首次复述请求流程；system / user 各自作用仍待验收 |
| SSE 增量事件、delta.content 与结束标记 | PRACTICED | `src/chat.py:stream_chat` | 已识别断流风险和 [DONE] 完成标记；经纠正区分完整性、幂等性及安全撤回，增量输出预测仍待验收 |
| 配置与请求错误的处理 | LEARNING | `src/chat.py:load_config`、`main` | 需区分缺少配置、认证失败与网络故障；工程测试不能替代学习验收 |

仅根据用户实际复述和答题更新状态；完整 REVIEW 尚未通过，暂无 MASTERED 知识点。
