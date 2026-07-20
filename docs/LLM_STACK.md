# LLM_STACK — 主流技术覆盖表

| 技术 | 流程阶段 | 具体实现 | 相对传统改进 |
|---|---|---|---|
| LLM | 推理主路径 | DeepSeek API 统一客户端，失败重试 | API 失败可降级为模拟响应，演示稳定性提升 |
| RoPE/长上下文 | 上下文策略 | 滑动窗口摘要 + 轨迹压缩 | 目标：长任务成功率↑15%，测法见 eval |
| GraphRAG | 知识检索 | 层级 Local + Global Search | 目标：知识召回率↑20% |
| Multi-Agent | 编排协作 | Supervisor + Worker | 目标：任务吞吐量↑30% |
| Function Calling | 工具调用 | 结构化工具 schema | 目标：工具调用成功率↑25% |
| MCP | 工具协议面 | Streamable HTTP `/mcp/call` | 目标：工具调用延迟↓20% |
| 记忆系统 | 状态保持 | 短期轨迹 + 长期 GraphRAG | 目标：长链路任务成功率↑15% |
| SSE 流式输出 | 交互体验 | Agent 过程事件实时推送 | 目标：用户感知延迟↓80% |
| 模型部署 | 可演示交付 | FastAPI + Docker Compose + 阿里云 | 国内可访问 Demo |
| 后训练 | 对齐/微调 | QLoRA DPO | 目标：特定任务成功率↑20% |
| 预训练 | 已关闭 | 复用 Qwen2.5-7B-Instruct | 不写 CPT，降低成本 |

## 硬性清单

- 核心技术 ≥8：DeepSeek API、Qwen2.5-7B-Instruct、LangGraph 风格 Multi-Agent、MCP、层级 GraphRAG、自研错误分析器、自研 DPO 数据生成、SSE 流式、QLoRA DPO、记忆系统。
- 较新栈 ≥3：LangGraph Supervisor+Worker、MCP Streamable HTTP、层级 GraphRAG。
- 自研改进 ≥2：错误分析器、DPO 数据生成器。
