# /migrate-template — 跨模板排版迁移

**作用**: 将论文从原模板迁移至目标模板，自动处理图表尺寸、页数、宏兼容性等问题。它是专家快捷入口；普通自然语言如“把这篇论文迁移到 CVPR 模板”也应能触发同类任务。

**用户入口说明**:
- 用户只需要描述迁移目标，不需要手动编排内部 CLI。
- CLI、runtime、scripts 是 Agent 的内部执行层。
- 模板迁移完成后，必须回到视觉闭环重新验收。

## 工具调用约定

闭环中的编译与页图渲染使用 **`paperfit run scripts/compile.sh`**（或 `latexmk`）与 **`paperfit render`**，见 `CLAUDE.md` 运行时边界一节。

## 用法

```
/migrate-template
```

也可以由自然语言触发，例如：

```text
用 PaperFit 把这篇论文迁移到 CVPR 模板
把当前论文从 AAAI 模板迁到 ICLR，并尽量保持版面稳定
```

## 执行流程

1. 识别当前模板与目标模板，必要时补充最少量澄清
2. 加载模板配置（`config/templates.yaml`）
3. 替换 `\documentclass` 和宏包
4. 调用 `template-migrator` 处理图表和兼容性
5. 启动 VTO 闭环（Category E 优先）
6. 输出迁移报告与视觉验收结果

## 调度

- 执行器：`agents/orchestrator-agent.md`
- 技能：`skills/template-migrator/SKILL.md`
- 任务类型：`template_migration`
