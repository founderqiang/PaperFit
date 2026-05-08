# /check-visual — 执行视觉检测

**作用**: 仅执行视觉检测，输出诊断报告，不修改源文件。它是专家快捷入口，对应的普通自然语言请求如“检查这篇论文的视觉排版问题”“先做诊断不要改源码”也应能触发同类任务。

**用户入口说明**:
- 用户不需要手动执行 `paperfit render` 或其它内部命令。
- CLI、runtime、scripts 是 Agent 的内部执行层。
- 最终输出应以视觉问题、页码、严重级别和修复建议为中心，而不是底层命令细节。

## 工具调用约定

可执行脚本在 **`paperfit-cli` 包内**；在**论文项目根目录**执行：`paperfit render …`、`paperfit run scripts/parse_log.py …`；勿假设项目内有 `scripts/render_pages.py`。兜底：`npx paperfit-cli …`、`python3 "$(paperfit root)/scripts/…"`。

## `column_void` Schema 提示

若本轮还会读取 A5 机检结果，注意：

- 原始 `detect_column_void.py` 输出文件：`data/reports/column_void_rN.json`
- 这个文件用 `pages[]`
- `by_page[]` 是 `paperfit run scripts/state_manager.py column-void ...` 合并进 `data/state.json` 后的摘要字段

也就是说：

- 读原始报告：`data["pages"]`
- 读状态摘要：`state["cv_signals_summary"]["by_page"]`

## 用法

```
/check-visual
```

## 执行流程

1. 编译 PDF（如需要）→ 在论文根目录执行 **`paperfit render <输出pdf路径> --output data/pages`**（脚本在全局安装的 `paperfit-cli` 包内，勿使用用户项目下的 `scripts/render_pages.py`）
2. 规则引擎检查编译日志
3. 排版侦探基于 VTO 分类体系识别缺陷
4. 输出结构化诊断报告

## 输出

- 缺陷列表（类别、页码、严重等级、描述）
- 修复建议
- 不修改任何源文件

## 调度

- 规则引擎：`agents/rule-engine-agent.md`
- 排版侦探：`agents/layout-detective-agent.md`
