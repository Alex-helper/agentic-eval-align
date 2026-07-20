# ARCHITECTURE — Agentic Eval Align

## 1. 技术栈

- Backend：FastAPI, Pydantic, httpx, SSE。
- Frontend：React + Vite + TypeScript。
- LLM：DeepSeek `deepseek-chat`，OpenAI-compatible API。
- Agent：Supervisor + Naive baseline；事件回调驱动实时 SSE。
- Tools：Function Calling Schema + MCP HTTP（fallback 本地）。
- Retrieval：层级 GraphRAG Local + Global Search。
- Memory：短期执行轨迹 + 长期 GraphRAG 知识。
- Artifacts：`data/runs/` 运行产物与导出。
- Finetune：Qwen/Qwen2.5-7B-Instruct + QLoRA DPO。
- Deploy：Docker Compose + 本地 start.bat（MCP/Backend/Frontend）。

## 2. 目录结构

```text
backend/
  main.py
  llm_client.py
  mcp_client.py
  stream_handler.py
  suite.py
  metrics_report.py
  runs.py
  agents/
  memory/
  ingest/
frontend/src/
  main.tsx
  types.ts
  components/   # RunControls, SuiteTable, TraceTimeline, ErrorReport, DPO, RunHistory, Export
finetune/
data/samples|knowledge_graph|graphrag_index|dpo_data|runs/
evals/
mcp_servers/
tests/
docs/
```

## 3. AI 调用机制

1. API 输入通过 FastAPI 校验；上传入口走 `backend/ingest` 多模态解析器统一成 `Task`。
2. Suite/单任务可选择 Naive baseline 或 Full Supervisor。
3. Full 路径：短期记忆 → GraphRAG Local+Global → MCP HTTP 工具 → LLM → 评分 → 失败则 ErrorReport/DPO。
4. MCP 通过 `MCP_BASE_URL` 调用 `/mcp/call`；失败时 fallback 本地工具并在轨迹标记 `transport`。
5. Supervisor 以事件回调实时推送，SSE 在执行过程中发事件（非事后回放）。
6. 每次运行写入 `data/runs/` 产物，含配置快照、轨迹、指标、DPO pairs。

## 3.1 多模态上传支持

| 类型 | 扩展名 | 处理方式 |
|------|--------|----------|
| 结构化任务 | `.json` `.jsonl` `.yaml` `.yml` | 解析为 Task 列表 |
| 表格任务 | `.csv` `.tsv` | 每行转一条 Task |
| 文本文档 | `.txt` `.md` | 全文作为 instruction |
| 图片 | `.png` `.jpg` `.jpeg` `.webp` `.gif` | base64 + 视觉消息 / 文本摘要 |
| PDF | `.pdf` | 抽取文本页内容 |
| Word | `.docx` | 抽取段落文本 |
| 压缩包 | `.zip` | 递归解析内部文件 |

## 4. 数据模型

- Task / MediaAttachment
- EvalResult + StageTiming + tool_transport
- RunArtifact / TaskCompare / SuiteMetrics
- ErrorReport / DPOPair（含 run_id）

## 5. 绝不能破坏的约束

- 评测双通道必须共用同一条 eval/scoring pipeline。
- 任何「实测」数字必须可由 `eval.py` 或 Suite API 复现。
- 目标指标必须标注「目标」。
- 上传数据仅本地处理。
- DeepSeek API key 只能来自环境变量。
- MCP 不可用时必须显式 fallback，禁止伪装成 MCP 成功。

## 6. 验收标准

- `/api/evaluate/suite`、`/api/runs`、`/api/evaluate/stream` 可用。
- MCP health 在 `/api/health` 可见。
- `eval.py --mode sample` 与 Suite 输出同一口径成功率。
