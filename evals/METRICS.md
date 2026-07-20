# METRICS — Eval Output

- 样本数：6
- 实测成功率（full）：100%
- 朴素基线成功率：0%
- 成功率变化：↑100.0%

| 指标 | 传统基线/对照 | 改进后 | 变化% | 测法 |
|---|---:|---:|---:|---|
| Agent 任务成功率 | 0% | 100% | ↑100.0% | naive vs full 同任务同评分器 |
| 工具调用成功率 | — | 100% | 实测 | 工具 transport 成功返回比例 |
| 知识命中率 | — | 100% | 实测 | GraphRAG/检索命中比例 |
| 平均端到端耗时 | — | 1718ms | 实测 | Supervisor timings.total_ms |
| 首事件延迟 | — | 0ms | 实测 | SSE first planning event |
| 错误分析时间 | 30 分钟/10条 | 2 分钟/10条 | 目标↓93.3% | 50 条预标注失败轨迹计时 |
| DPO 数据成本 | 2000 元/100对 | 5 元/100对 | 目标↓99.75% | 人工成本 vs 自动生成成本 |

## Task Results
- `sample_auth_recovery` [full]: success=True, score=1.00, transport=mcp_http, knowledge_hit=True
- `sample_invoice_calculation` [full]: success=True, score=1.00, transport=mcp_http, knowledge_hit=True
- `sample_search_filter` [full]: success=True, score=1.00, transport=mcp_http, knowledge_hit=True
- `sample_workflow_state` [full]: success=True, score=1.00, transport=mcp_http, knowledge_hit=True
- `sample_risk_review` [full]: success=True, score=1.00, transport=mcp_http, knowledge_hit=True
- `sample_complex_multi_hop` [full]: success=True, score=1.00, transport=mcp_http, knowledge_hit=True

## A/B Compare
- `sample_auth_recovery`: baseline=False/0.20 → full=True/1.00 (Δscore=0.8)
- `sample_complex_multi_hop`: baseline=False/0.20 → full=True/1.00 (Δscore=0.8)
- `sample_invoice_calculation`: baseline=False/0.20 → full=True/1.00 (Δscore=0.8)
- `sample_risk_review`: baseline=False/0.20 → full=True/1.00 (Δscore=0.8)
- `sample_search_filter`: baseline=False/0.20 → full=True/1.00 (Δscore=0.8)
- `sample_workflow_state`: baseline=False/0.20 → full=True/1.00 (Δscore=0.8)

> 标注「目标」的行尚未做人工对照实验；标注「实测」的行由本地 eval/suite 回填。