# PIPELINE — LLM 全链路流程

| 阶段 | 具体实现 | 产物 |
|---|---|---|
| 数据/知识 | 模拟 API 文档知识图谱与 5 个 Agent 任务 | `data/knowledge_graph/`, `data/samples/` |
| 预训练 | 关闭 CPT，复用 `Qwen/Qwen2.5-7B-Instruct` | 权重引用 |
| 后训练 | QLoRA DPO，数据来自失败轨迹 | `finetune/`, `data/dpo_data/` |
| GraphRAG | 层级 Local + Global Search | `data/graphrag_index/index.json` |
| Multi-Agent | Supervisor + Evaluator + Optimizer | `backend/agents/` |
| Function Calling/MCP | 搜索、计算器结构化 schema + Streamable HTTP | `mcp_servers/` |
| 记忆 | 短期轨迹 + 长期检索知识 | `backend/memory/` |
| LLM 推理/RoPE | DeepSeek API，滑动窗口摘要策略 | `backend/llm_client.py` |
| 流式输出 | SSE 事件流 + 前端三态 UI | `backend/stream_handler.py`, `frontend/` |
| 部署 | Docker Compose + 阿里云/Nginx | `docker-compose.yml`, `docs/DEPLOY.md` |
| 评测 | sample/upload 双通道共用 pipeline | `eval.py`, `evals/METRICS.md` |

## 运行命令

```bash
python scripts/build_graphrag_index.py
python eval.py --mode sample
uvicorn backend.main:app --reload
```
