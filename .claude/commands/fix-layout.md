# /fix-layout — 启动完整 VTO 排版优化

**作用**: 对当前 LaTeX 项目执行完整的视觉排版优化（VTO）闭环

**防呆约束**:
- 用户只需要表达目标，不需要手动执行内部命令
- 直接执行 `paperfit runtime ...` / `paperfit run ...` / `paperfit render ...`
- 不要为了“启动闭环”先去调用任何内部任务管理工具
- 不要调用 `TaskCreate`、`TodoWrite`、`Plan`、`Agent` 之类的任务编排工具来代替实际执行
- 不要在 `/fix-layout` 过程中再自动触发其他斜杠命令
- 如果任务工具 schema 缺失或出现 `InputValidationError`，应立即回退到直接 shell 命令，不要重试任务工具

## 用户入口说明

- `/fix-layout` 是专家快捷入口，不是要求用户理解内部 CLI 的入口。
- 与之对应的普通自然语言，例如“修复这篇论文的排版问题”“尽量不改语义地压到 9 页”，也应能触发同类任务。
- CLI、runtime、scripts 是你的执行层，不是用户的产品接口。

## 工具调用约定

可执行脚本在 **`paperfit-cli` 包内**；在**论文项目根目录**执行，勿假设仓库里自带可运行的 `scripts/`：页图用 `paperfit render <pdf> --output data/pages`，其它用 `paperfit run scripts/<文件> [参数…]`；无全局命令时用 `npx paperfit-cli …` 或 `python3 "$(paperfit root)/scripts/…"`。

## 用法

```
/fix-layout
```

也可以由普通自然语言触发，例如：

```text
用 PaperFit 修复当前论文的排版问题
把这篇论文排到投稿状态，优先修视觉问题
把正文压到 9 页，尽量不要改正文含义
```

## 直接执行入口

首选直接运行：

```bash
paperfit runtime --state data/state.json run-round main.tex --template <TEMPLATE> --target-pages <N>
```

若还未初始化，再先执行：

```bash
paperfit runtime --state data/state.json init-task main.tex --template <TEMPLATE> --target-pages <N>
```

## `column_void` Schema 提示

- `data/reports/column_void_rN.json` 是 `detect_column_void.py` 的**原始报告**
- 原始报告顶层字段使用 `pages[]`
- `by_page[]` 不在原始报告里
- `by_page[]` 只存在于 `data/state.json -> cv_signals_summary.by_page`

如果要直接分析原始报告，应读取：

```json
{
  "page_count": 60,
  "pages": [
    {
      "page_image": "data/pages/xxx.png",
      "columns": {
        "left": {"max_void_ratio": 0.0},
        "right": {"max_void_ratio": 0.0}
      },
      "a5_candidates": []
    }
  ]
}
```

不要写：

```python
data["by_page"]
```

除非你读的是 `data/state.json` 的 `cv_signals_summary`。

## 执行流程

0. **画像（推荐）**：若用户尚未建立 `data/paperfit-portrait.yaml`，可在内部先执行画像构建或刷新；不要把这一步强制变成用户必须再次输入 `/paperfit` 的动作。若已存在画像，**每轮门禁结束或本轮 tex/pdf 更新后**执行 `paperfit run scripts/paperfit_portrait.py refresh` 刷新扫描项与 `state.task.portrait_*`。
1. 识别主 `.tex` 文件（`data/benchmarks/case/*.tex`）
2. 初始化或加载 `state.json`（优先使用 `paperfit runtime --state data/state.json init-task main.tex ...`；双栏论文补 `--column-type double`；若已由 `/paperfit` 写入栏型，以 `state.json` / 画像为准）
3. 每轮优先执行 `paperfit runtime --state data/state.json run-round main.tex --template <TEMPLATE> --target-pages <N>`，统一完成轮次推进、日志解析、crossrefs 提取、页图检查、缺陷摘要推导与 gatekeeper 回写；若需拆步排障，再退回 `start-round` / `mark-compile` / `mark-render` / `gatekeeper`
4. 若是**双栏任务**且本轮已生成页图，再执行 `detect_column_void` + `paperfit runtime --state data/state.json ingest-column-void data/reports/column_void_rN.json` 写入机检摘要
5. 规则引擎检测编译日志错误
6. 排版侦探基于 VTO 分类体系检测视觉缺陷（合并 `machine_signals` 与 VLM）
7. 代码外科医生执行修复
8. 重新编译 → 质量门禁验收（诊断报告用 `config/diagnostic_report.template.md`）
9. 迭代至 DONE 或达到最大轮次

## 错误回退

若 Claude 内部工具报这类错误：

- `InputValidationError`
- `TaskCreate failed`
- `schema was not sent to the API`
- `The required parameter subject is missing`

不要继续尝试内部任务工具，直接执行 shell 命令：

```bash
paperfit runtime --state data/state.json run-round main.tex --template <TEMPLATE> --target-pages <N>
```

如果缺少 `main.tex` / `template` / `target_pages`，先从 `data/paperfit-portrait.yaml` 或 `data/state.json` 读取，再继续。

## 状态管理

- 每轮迭代前自动备份 `data/benchmarks/case` 目录
- 更新 `data/state.json` 状态
- 生成诊断报告 `diagnostic_report_round*.md`

## 调度

- 主调度器：`agents/orchestrator-agent.md`
- 任务类型：`full_vto`
