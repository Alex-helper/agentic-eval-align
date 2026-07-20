# DESIGN — Web Demo 设计规范

## 1. 视觉方向

- 关键词：研究实验室、轨迹可视化、可信评测、闭环优化。
- 第一屏作为一个完整组合：品牌名、平台定位、一个 CTA 组、实时轨迹预览。
- 避免：客服聊天气质、默认白底 dashboard、紫色渐变、卡片堆叠、过多统计条。

## 2. 色彩与字体

- Display font：`Space Grotesk`。
- Body font：`IBM Plex Sans`。
- CSS 变量：
  - `--ink: #111827`
  - `--muted: #5b6475`
  - `--paper: #f7f3e8`
  - `--signal: #0f766e`
  - `--signal-2: #f97316`
  - `--line: rgba(17, 24, 39, 0.16)`

## 3. 页面结构

1. Hero：品牌“TraceAlign Lab”作为最大视觉信号；一句话说明；运行内置案例 CTA；上传真实评测 CTA；全宽轨迹背景。
2. Evaluation Console：选择内置任务或上传 JSON，触发 SSE。
3. Trace Stream：展示 planning/running/success/error 三态事件。
4. Metrics Panel：显示基线、改进后、变化百分比、测法。
5. Pipeline Strip：展示数据 → GraphRAG → Agent → MCP → DPO → 评测。

## 4. 三态 UI

- Loading：轨迹行骨架 + “Agent 正在规划/调用工具/写报告”。
- Empty：提示选择内置案例或上传 JSON。
- Error：展示后端错误、重试按钮、保留已完成轨迹。

## 5. 动效

- 轨迹行按 SSE 事件渐入。
- Hero 背景的知识节点缓慢漂移。
- 指标变化条按百分比扩展。

## 6. 验收标准

- 桌面与移动端首屏均保持品牌优先，不变成通用 dashboard。
- 运行中、无数据、错误三态在前端可见。
- 不使用 hero 卡片和漂浮徽章覆盖主视觉。
