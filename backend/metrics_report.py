from __future__ import annotations

from backend.models import EvalResult, SuiteMetrics, TaskCompare


def score_task(
    *,
    task_source_format: str,
    expected: dict,
    answer: str,
    answer_parts: list[str],
    knowledge: list,
    llm_content: str,
) -> tuple[bool, float, bool]:
    """Shared scorer for naive and full pipelines."""
    expected_keyword = str(expected.get("keyword", "")).lower()
    knowledge_hit = bool(knowledge)
    if task_source_format in {"text", "markdown", "pdf", "docx", "image"} or task_source_format.startswith("zip:"):
        success = bool(answer_parts) and bool(llm_content)
    else:
        success = bool(answer_parts) and (
            not expected_keyword or expected_keyword in answer.lower() or knowledge_hit
        )
    score = 1.0 if success else 0.35
    return success, score, knowledge_hit


def aggregate_metrics(results: list[EvalResult]) -> SuiteMetrics:
    n = max(1, len(results))
    success_rate = sum(1 for r in results if r.success) / n
    avg_score = sum(r.score for r in results) / n
    tool_rate = sum(1 for r in results if r.tool_success) / n
    knowledge_rate = sum(1 for r in results if r.knowledge_hit) / n
    avg_total = sum(r.timings.total_ms for r in results) / n
    avg_first = sum(r.timings.first_event_ms for r in results) / n
    return SuiteMetrics(
        task_count=len(results),
        baseline_success_rate=0.0,
        current_success_rate=success_rate,
        success_rate_delta_pct=0.0,
        baseline_avg_score=0.0,
        current_avg_score=avg_score,
        tool_success_rate=tool_rate,
        knowledge_hit_rate=knowledge_rate,
        avg_total_ms=avg_total,
        avg_first_event_ms=avg_first,
    )


def compare_pipelines(baseline: list[EvalResult], current: list[EvalResult]) -> tuple[list[TaskCompare], SuiteMetrics]:
    by_base = {r.task_id: r for r in baseline}
    by_cur = {r.task_id: r for r in current}
    compares: list[TaskCompare] = []
    for task_id in sorted(set(by_base) | set(by_cur)):
        b = by_base.get(task_id)
        c = by_cur.get(task_id)
        if not b or not c:
            continue
        compares.append(
            TaskCompare(
                task_id=task_id,
                baseline=b,
                current=c,
                improved=c.score > b.score or (c.success and not b.success),
                delta_score=round(c.score - b.score, 4),
            )
        )
    base_rate = sum(1 for r in baseline if r.success) / max(1, len(baseline))
    cur_rate = sum(1 for r in current if r.success) / max(1, len(current))
    delta_pct = ((cur_rate - base_rate) / base_rate * 100.0) if base_rate > 0 else (100.0 if cur_rate > 0 else 0.0)
    metrics = SuiteMetrics(
        task_count=len(compares),
        baseline_success_rate=base_rate,
        current_success_rate=cur_rate,
        success_rate_delta_pct=round(delta_pct, 1),
        baseline_avg_score=sum(r.score for r in baseline) / max(1, len(baseline)),
        current_avg_score=sum(r.score for r in current) / max(1, len(current)),
        tool_success_rate=sum(1 for r in current if r.tool_success) / max(1, len(current)),
        knowledge_hit_rate=sum(1 for r in current if r.knowledge_hit) / max(1, len(current)),
        avg_total_ms=sum(r.timings.total_ms for r in current) / max(1, len(current)),
        avg_first_event_ms=sum(r.timings.first_event_ms for r in current) / max(1, len(current)),
    )
    return compares, metrics


def pct_change(baseline: float, improved: float, higher_is_better: bool = True) -> str:
    if baseline == 0:
        if improved == 0:
            return "0.0%"
        return "↑∞" if higher_is_better else "↓∞"
    delta = (improved - baseline) / baseline * 100
    if not higher_is_better:
        delta = (baseline - improved) / baseline * 100
    arrow = "↑" if (delta >= 0 if higher_is_better else delta >= 0) else "↓"
    # Use absolute formatting with correct arrow from signed delta for higher_is_better
    if higher_is_better:
        arrow = "↑" if improved >= baseline else "↓"
        value = abs((improved - baseline) / baseline * 100)
    else:
        arrow = "↓" if improved <= baseline else "↑"
        value = abs((baseline - improved) / baseline * 100)
    return f"{arrow}{value:.1f}%"


def format_delta_pct(delta_pct: float) -> str:
    arrow = "↑" if delta_pct >= 0 else "↓"
    return f"{arrow}{abs(delta_pct):.1f}%"


def render_metrics_md(
    *,
    results: list[EvalResult],
    compares: list[TaskCompare] | None = None,
    metrics: SuiteMetrics | None = None,
) -> str:
    if metrics is None:
        metrics = aggregate_metrics(results)
    rows = [
        (
            "Agent 任务成功率",
            f"{metrics.baseline_success_rate:.0%}" if compares else "朴素基线",
            f"{metrics.current_success_rate:.0%}",
            format_delta_pct(metrics.success_rate_delta_pct) if compares else "实测",
            "naive vs full 同任务同评分器",
        ),
        (
            "工具调用成功率",
            "—",
            f"{metrics.tool_success_rate:.0%}",
            "实测",
            "工具 transport 成功返回比例",
        ),
        (
            "知识命中率",
            "—",
            f"{metrics.knowledge_hit_rate:.0%}",
            "实测",
            "GraphRAG/检索命中比例",
        ),
        (
            "平均端到端耗时",
            "—",
            f"{metrics.avg_total_ms:.0f}ms",
            "实测",
            "Supervisor timings.total_ms",
        ),
        (
            "首事件延迟",
            "—",
            f"{metrics.avg_first_event_ms:.0f}ms",
            "实测",
            "SSE first planning event",
        ),
        ("错误分析时间", "30 分钟/10条", "2 分钟/10条", "目标↓93.3%", "50 条预标注失败轨迹计时"),
        ("DPO 数据成本", "2000 元/100对", "5 元/100对", "目标↓99.75%", "人工成本 vs 自动生成成本"),
    ]
    body = [
        "# METRICS — Eval Output",
        "",
        f"- 样本数：{metrics.task_count}",
        f"- 实测成功率（full）：{metrics.current_success_rate:.0%}",
    ]
    if compares:
        body.append(f"- 朴素基线成功率：{metrics.baseline_success_rate:.0%}")
        body.append(f"- 成功率变化：{format_delta_pct(metrics.success_rate_delta_pct)}")
    body.extend(["", "| 指标 | 传统基线/对照 | 改进后 | 变化% | 测法 |", "|---|---:|---:|---:|---|"])
    body.extend(f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows)
    body.append("")
    body.append("## Task Results")
    for r in results:
        body.append(
            f"- `{r.task_id}` [{r.pipeline}]: success={r.success}, score={r.score:.2f}, "
            f"transport={r.tool_transport}, knowledge_hit={r.knowledge_hit}"
        )
    if compares:
        body.append("")
        body.append("## A/B Compare")
        for item in compares:
            body.append(
                f"- `{item.task_id}`: baseline={item.baseline.success}/{item.baseline.score:.2f} → "
                f"full={item.current.success}/{item.current.score:.2f} (Δscore={item.delta_score})"
            )
    body.append("")
    body.append("> 标注「目标」的行尚未做人工对照实验；标注「实测」的行由本地 eval/suite 回填。")
    return "\n".join(body)
