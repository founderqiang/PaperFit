# /show-status — 查看当前任务状态与证据链

## 命令描述

显示当前 PaperFit 任务的运行状态，包括迭代轮次、缺陷消除进度、视觉优先级、修复计划摘要及下一步行动。适用于长时间运行任务的中途检查或恢复任务前确认上下文。

## 触发词

/show-status

## 行为

1. **读取 `data/state.json`**（若存在）。
2. **格式化输出**：
   - 项目主文件
   - 任务类型与约束
   - 当前轮次 / 最大轮次
   - `compile_success` / `page_images_rendered`
   - 缺陷摘要（按类别统计）
   - `visual_signals_summary.priority_pages` / `priority_objects`
   - `repair_plan_summary` / `repair_execution_summary`
   - 最近一次门禁决策及下一步行动
   - `artifacts.rule_report` / `crossrefs_report` / `visual_signal_report` / `repair_plan` / `repair_execution_report` / `semantic_patch_report` / `gatekeeper_decision`
3. **若任务已完成**：显示最终门禁状态与相关报告路径。

## 示例

```
/show-status
```

## 调度映射

- 不调用 Agent，直接读取 `state.json` 和诊断报告
