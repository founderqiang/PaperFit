# /fix-layout

对当前 LaTeX 论文运行完整 PaperFit VTO 闭环。

## Workflow

1. 识别主 `.tex`、模板和目标页数。
2. 若尚未初始化，先建立或刷新 `data/state.json`。
3. 优先运行：

```bash
paperfit runtime --state data/state.json run-round main.tex --template <TEMPLATE> --target-pages <N>
```

4. 检查编译、渲染、视觉缺陷和门禁结果。
5. 必须看页图后再判断是否通过。

## Guardrails

- 不要只停留在分析阶段。
- 不要为了调度而绕过实际执行。
- 只在必要时退回到 `paperfit render` 或 `paperfit run scripts/...` 做定向排障。
