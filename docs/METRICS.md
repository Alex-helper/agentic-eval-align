# METRICS — 指标对比验证

> 规则：未实测写「目标% + 测法」；实测后由 `python eval.py --mode sample` 或 UI Suite 回填 `evals/METRICS.md`。禁止把静态装饰条当作实测。

| 指标 | 对照 | 改进后 | 变化% | 口径 |
|---|---:|---:|---:|---|
| Agent 任务成功率 | 朴素基线（无检索/无工具） | Full Supervisor | 实测 | naive vs full 同任务同评分器 |
| 工具调用成功率 | — | Full 运行 | 实测 | MCP/fallback 成功返回比例 |
| 知识命中率 | — | Full 运行 | 实测 | GraphRAG 检索命中比例 |
| 首事件延迟 | — | Full/SSE | 实测 | 首个 planning 事件时间 |
| 错误分析时间 | 30 分钟/10条 | 2 分钟/10条 | 目标↓93.3% | 50 条预标注失败轨迹计时 |
| DPO 数据成本 | 2000 元/100对 | 5 元/100对 | 目标↓99.75% | 人工 vs 自动生成成本 |

## 运行产物

每次 Suite/单任务/上传评测都会写入 `data/runs/<run_id>.json`，可导出：

- `/api/runs/{run_id}/export.json`
- `/api/runs/{run_id}/export.md`
- `/api/runs/{run_id}/export.dpo.jsonl`
