# /repair-table — 修复表格

**作用**: 针对指定表格或当前论文中的表格问题执行修复闭环。它是专家快捷入口；普通自然语言如“修 Table 2 太挤的问题”也应能触发同类任务。

**用户入口说明**:
- 用户只需要描述哪张表有问题，或直接说明“修表格”。
- 不要要求用户手动执行 `paperfit render`、`compile.sh` 或其它内部命令。
- 表格修复必须以视觉可读性和结构完整性为主，而不是靠暴力缩放过关。

## 工具调用约定

验证阶段在论文根目录使用 **`paperfit run scripts/compile.sh`** / **`paperfit render`**，勿假设项目内存在包级 `scripts/`。

## 用法

```
/repair-table
```

也可以由自然语言触发，例如：

```text
用 PaperFit 修复这篇论文的表格问题
修一下 Table 2，当前太挤而且列宽不平衡
```

## 执行流程

1. 定位指定表格或自动识别主要表格问题
2. 分析表格溢出、一致性、列宽和可读性问题
3. 重构列格式、调整列间距、必要时改用更合适的表格布局策略
4. 重新编译并回到视觉验证

## 调度

- 代码外科医生：`agents/code-surgeon-agent.md`
- 技能：`skills/overflow-repair/`、`skills/consistency-polisher/`
