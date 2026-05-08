# /show-status — 查看任务状态

**作用**: 显示当前 PaperFit 任务的运行状态、缺陷消除进度、视觉优先级、修复计划摘要和下一步行动；这是当前默认的“摘要 / 解释”入口。

**用户入口说明**:
- `/show-status` 是查询入口，用户不需要理解 `state.json` 的字段结构。
- 输出应优先解释当前任务状态、视觉问题、剩余风险和下一步动作，而不是直接倾倒内部 JSON。
- 若用户用普通自然语言询问“当前 PaperFit 到哪一步了”“还有哪些问题没修完”，也应路由到同类状态查询。

## 工具调用约定

若需读写状态文件以外的包内工具，在论文根目录使用 **`paperfit run scripts/state_manager.py …`**，勿将 `scripts/` 当作用户仓库内路径。

## 用法

```
/show-status
```

也可以由自然语言触发，例如：

```text
查看当前 PaperFit 状态
这篇论文现在还剩哪些排版问题
```

## 执行流程

1. 读取 `data/state.json` 获取当前状态
2. 优先展示 `main_tex`、任务画像、当前轮次 / 最大轮次
3. 显示 `compile_success`、`page_images_rendered`
4. 显示缺陷摘要（已修复/剩余）
5. 显示 `visual_signals_summary.priority_pages`、`priority_objects`
6. 显示 `repair_plan_summary`、`repair_execution_summary`
7. 显示最近一次门禁决策、`next_actions`
8. 显示 `artifacts.rule_report`、`artifacts.crossrefs_report`、`artifacts.visual_signal_report`、`artifacts.repair_plan`、`artifacts.repair_execution_report`、`artifacts.semantic_patch_report`、`artifacts.gatekeeper_decision`

## 输出内容

- 项目主文件
- 任务类型与约束
- 当前轮次 / 最大轮次
- 编译结果与页图渲染状态
- 缺陷摘要（已修复/剩余）
- 视觉重点页与重点对象
- 修复计划摘要与最近执行结果
- 最近一次门禁决策及下一步行动
- 诊断报告路径

## 调度

- 直接读取 `data/state.json` 和诊断报告，不调用 Agent
