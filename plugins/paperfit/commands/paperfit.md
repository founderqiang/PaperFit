# /paperfit

PaperFit 的统一自然语言入口。

## Use When

- 需要做排版分析
- 需要完整修复版面
- 需要只看视觉缺陷
- 需要模板迁移、页数控制、表格修复或状态查询

## Workflow

1. 在论文项目根目录工作。
2. 先按自然语言理解用户意图，不要求用户再记内部 CLI。
3. 需要时自动调用 `paperfit` CLI、runtime 和包内脚本。
4. 优先复用 `~/.codex/skills/paperfit/` 里的技能与约束。

## Guardrails

- 不要把 `paperfit` CLI 暴露成用户主接口。
- 不要在没有看页图的情况下宣称版面已经修好。
- 不要用 `\resizebox` 或 `\scalebox` 粗暴压表格。
