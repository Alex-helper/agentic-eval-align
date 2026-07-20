# PRD — Agentic 评测与对齐优化平台

## 1. 产品定位

一个面向大模型复杂推理任务的自动化评测与对齐优化平台。它不是客服/问答系统，而是让“评测 Agent”和“优化 Agent”协同工作，围绕多步推理、工具调用、知识检索和失败轨迹形成“评测 → 分析 → 数据生成 → 后训练 → 再评测”的闭环。

## 2. 用户与痛点

- 用户：算法工程师、AI 应用开发者、Agent 产品研发人员。
- 主场景：评估和提升模型在需要多步推理、工具调用、状态保持的 Agent 任务上的表现。
- 痛点：
  1. 复杂 Agent 任务只看成功率，难以定位失败步骤。
  2. 失败轨迹人工审查慢，难以批量产出改进数据。
  3. DPO 偏好数据构建成本高，后训练闭环难落地。
  4. 工具协议、知识检索、记忆、流式体验常被 Demo 化，没有统一评测流水线。

## 3. MVP 功能

1. 内置 5 个 Agent 评测任务，可一键运行，并支持 naive vs full A/B Suite。
2. 支持上传多格式/多模态评测数据（JSON/JSONL/CSV/TSV/YAML/TXT/MD/图片/PDF/DOCX/ZIP），先预览再评测，本地处理。
3. GraphRAG 对知识图谱执行 Local + Global Search（检索命中 + community 摘要）。
4. Supervisor + Worker 风格编排；朴素基线与完整流水线对照。
5. MCP Streamable HTTP 工具服务真实接入；不可用时显式 fallback 本地工具并标记 transport。
6. DeepSeek/OpenAI-compatible LLM 客户端，带超时、重试、模拟兜底。
7. 实时 SSE：规划/检索/工具/LLM 事件在执行过程中推送，而非事后回放。
8. 自研轨迹错误分析器输出结构化错误报告，并在 UI 可见。
9. 自研失败轨迹 DPO 数据生成器输出 chosen/rejected，并绑定 run_id 可导出。
10. `eval.py --mode sample` 与 UI Suite 共用评分器，输出基线 vs 改进实测报告。
11. 运行产物 `data/runs/`：历史、详情、JSON/Markdown/DPO JSONL 导出与重跑。
12. QLoRA DPO 微调脚本与数据目录落地。

## 4. 功能黑名单

- 不做客服、通用问答、知识库聊天。
- 不编造线上 DAU、真实准确率或不可复现大盘数字。
- 不做 CPT 预训练；复用 `Qwen/Qwen2.5-7B-Instruct` checkpoint。
- 不把用户上传数据传到第三方存储；仅本地评测。
- 不把静态装饰百分比冒充实测结果。
- MVP 不要求真实 GPU 完成微调权重产出，但必须提供可运行脚本、数据格式和权重引用路径。

## 5. 端到端 LLM 工程流程

1. 数据/知识构建：`data/knowledge_graph/` 与 `data/samples/`。
2. 预训练关闭：复用 `Qwen/Qwen2.5-7B-Instruct`。
3. 后训练：失败轨迹 → DPO JSONL → QLoRA 脚本。
4. GraphRAG：Local search + Global community summary。
5. Multi-Agent：Naive baseline vs Full Supervisor。
6. MCP HTTP 工具调用，失败显式 fallback。
7. 记忆：短期轨迹 + 长期检索。
8. LLM：DeepSeek API。
9. 实时 SSE 流式事件。
10. 运行产物与导出：`data/runs/`。
11. 评测：`eval.py` / Suite API 写 `evals/METRICS.md`。
12. 文档交付。

## 6. 验收标准

- `start.bat` 同时启动 MCP / 后端 / 前端。
- 页面可一键运行 5 任务 A/B，显示逐项 baseline/current、真实变化% 与 run_id。
- MCP 工具轨迹显示 `mcp_http` 或明确 `fallback_local`。
- 首个 SSE 规划事件在任务完成前到达。
- 失败任务可见 ErrorReport 与 DPO，并可导出该 run。
- UI 与 `python eval.py --mode sample` 成功率一致；静态装饰百分比不得冒充实测。
- 指标表区分「实测」与「目标」。
