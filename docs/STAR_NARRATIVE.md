# STAR_NARRATIVE — 面试讲述稿

## S Situation

大模型应用从单轮问答进入复杂 Agent 任务后，研发团队难以系统评估多步推理、工具调用、状态保持和知识检索的失败原因。传统做法只看成功率，失败轨迹依赖人工逐条审查，后训练偏好数据也需要高成本人工标注。

## T Task

我负责构建一个可演示的网站型平台，交付“评测 → 分析 → 优化 → 再评测”闭环，并用可复现的百分比指标证明相对朴素方案更好。硬性边界：非客服问答、预训练关闭、后训练打开、双通道评测、指标区分实测/目标。

## A Action

1. 用 SDD 先固化 PRD/DESIGN/ARCHITECTURE，避免范围失控。
2. 构建 5 个内置 Agent 任务 + 模拟 API 文档知识图谱；GraphRAG Local 检索 + Global community 摘要。
3. 实现 Naive baseline（无检索/无工具）与 Full Supervisor 对照，共用同一评分器。
4. 将搜索和计算器接到真实 MCP HTTP；不可用时显式 fallback，并在轨迹标记 transport。
5. DeepSeek API 主推理路径，带超时、重试、无 Key 兜底。
6. 自研错误分析器 + DPO 生成器，结果绑定 run_id，前端可见并可导出。
7. 实时 SSE：规划/检索/工具/LLM 事件在执行过程中推送。
8. 运行产物 `data/runs/`：历史、JSON/Markdown/DPO 导出、重跑。
9. QLoRA DPO 脚本复用 Qwen2.5-7B-Instruct，不做 CPT。

## R Result

- 朴素基线 vs Full：`python eval.py --mode sample` 实测基线成功率 0% → full 100%（同 5 任务同评分器），工具成功率 100%，知识命中率 100%，transport=`mcp_http`。
- 错误分析时间：目标↓93.3%（测法：50 条预标注失败轨迹计时）。
- DPO 数据成本：目标↓99.75%（测法：人工 vs 自动生成成本）。
- 工程交付：可信评测控制台 + MCP + GraphRAG + 运行导出，面试官可本地一键打开验证。
