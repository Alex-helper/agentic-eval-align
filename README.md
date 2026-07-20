# TraceAlign Lab — Agentic Eval & Alignment Platform

Demo URL：部署后填写阿里云公网地址。

一个面向大模型复杂推理任务的自动化评测与对齐优化平台。它通过“评测 Agent + 优化 Agent”闭环，完成 GraphRAG 检索、MCP 工具调用、轨迹错误分析、DPO 数据生成和对照评测。

## 核心能力

- FastAPI + React 可信评测控制台：实时 SSE、Suite A/B、运行历史与导出。
- 5 个内置复杂 Agent 评测任务：`data/samples/`。
- 真实数据上传入口：支持 JSON / JSONL / YAML / CSV / TSV / TXT / MD / 图片 / PDF / DOCX / ZIP，先预览再评测。
- DeepSeek `deepseek-chat` 客户端（`OPENAI_API_KEY` + `OPENAI_BASE_URL`）。
- 真实 MCP HTTP 工具调用（`MCP_BASE_URL`），不可用时显式 fallback。
- 层级 GraphRAG Local + Global Search。
- 自研错误分析器与失败轨迹 DPO 数据生成器（UI 可见 + run 绑定导出）。
- 朴素基线 vs Full Supervisor 同评分器对照。
- QLoRA DPO 微调脚本，复用 `Qwen/Qwen2.5-7B-Instruct`，不做 CPT。
- `python eval.py --mode sample` 输出基线 vs 改进实测报告。

## 快速开始（Windows 一键）

本机默认浏览器（夸克）或 `.bat` 关联可能损坏，**优先双击**：

1. `打开本地网站.vbs`（推荐，强制用 cmd 启动，避免“找不到应用”）
2. 或右键 `start.bat` → 用命令提示符打开

- `start.bat` / `打开本地网站.vbs`：同时启动 **MCP(:8100) + 后端(:8000) + 前端(:3000)**，打印 MCP/Backend 健康状态，并用 **Edge/Chrome** 打开 http://127.0.0.1:3000
- `stop.bat` / `停止服务.vbs`：停止 MCP / 后端 / 前端（8100/8000/3000）
- 若双击 `.bat` 仍提示找不到应用：右键以管理员运行 `scripts\fix_bat_association.bat` 一次

手动启动：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/build_graphrag_index.py
python eval.py --mode sample
uvicorn backend.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

Docker：

```bash
cp .env.example .env
docker-compose up --build
```

## 评测

```bash
python eval.py --mode sample
python eval.py --mode upload --path data/samples/multimodal/tasks.csv
python eval.py --mode upload --path data/samples/multimodal/auth_card.png
```

输出：`evals/METRICS.md`。

## 微调

```bash
python finetune/train_dpo_qlora.py --dry-run
python finetune/train_dpo_qlora.py --data data/dpo_data/dpo_pairs.jsonl
```

## 文档

- `docs/PRD.md`
- `docs/DESIGN.md`
- `docs/ARCHITECTURE.md`
- `docs/PIPELINE.md`
- `docs/LLM_STACK.md`
- `docs/IMPROVEMENTS.md`
- `docs/METRICS.md`
- `docs/DEPLOY.md`

## 指标口径

未实测指标均写为“目标% + 测法”。本地 sample eval 会回填可复现结果到 `evals/METRICS.md`，不编造线上 DAU 或不可复现准确率。
