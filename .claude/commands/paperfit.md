# /paperfit — PaperFit 统一自然语言入口

**作用**: `/paperfit` 是 Claude Code 中的 PaperFit 主入口。用户可以直接用自然语言描述任务，例如排版分析、完整修复、模板迁移、长度调整、局部表格修复、视觉检查或状态查询。Agent 负责解析意图、识别主 `.tex`、判断是否需要画像、并自动进入对应的 PaperFit 子流程。

**注意**:
- `/paperfit` 不是单纯的“画像初始化命令”，也不是直接跑项目目录下的 `scripts/paperfit_wizard.py`
- 不要假设论文项目里自带 `scripts/`
- 若需要画像，优先在内部调用 `paperfit run scripts/paperfit_portrait.py ...`
- `/paperfit` 自己就可以完成任务路由，不必强制用户再记忆 `/fix-layout` 等子命令
- 如果用户说“实际有 5 个 table / figure”，这是事实校正，不是期望值
- 内部 CLI、runtime、脚本是执行层，不是用户接口

---

## 用法

```bash
/paperfit <自然语言任务>
```

例如：

```text
/paperfit 对 aaai24_antibody.tex 做排版分析
/paperfit 修复这个项目的排版问题，尽量不要改正文含义
/paperfit 把这篇论文迁移到 CVPR 模板
/paperfit 只检查视觉问题，不改源码
/paperfit 查看当前 PaperFit 状态
```

如果用户说“刷新画像”“重新扫描当前论文画像”“更新画像”，也走这个命令。

---

## 意图路由

`/paperfit` 应优先路由到以下任务类型之一：

- `analyze_layout`：排版分析、摸底、诊断
- `full_vto`：完整闭环修复
- `visual_only`：只做视觉检查
- `repair_table`：表格或少量对象定向修复
- `adjust_length`：页数或长度调整
- `template_migration`：模板迁移
- `status_query`：状态查看
- `undo_last_change`：回滚最近一次自动写回

若用户意图不够明确，默认先做 `analyze_layout`，必要时补充画像与状态初始化。

## 工具调用约定

在**论文项目根目录**执行内部步骤时：

```bash
paperfit run scripts/paperfit_portrait.py build --main <路径> [--template <键名>] --page-budget <口径> --target-pages <N> [--strict] [--max-rounds 10] [--column-type single|double]
paperfit run scripts/paperfit_portrait.py refresh [--main <路径>] [--column-type single|double]
```

若用户纠正扫描数量，可附加：

```bash
paperfit run scripts/paperfit_portrait.py build --main <路径> --page-budget with_refs --target-pages <N> --observed-table-count 5 --count-note "User confirmed scanner under-counted tables"
paperfit run scripts/paperfit_portrait.py refresh --observed-table-count 5 --count-note "User confirmed scanner under-counted tables"
```

无全局 `paperfit` 时：

```bash
npx paperfit-cli run scripts/paperfit_portrait.py ...
```

若必须直接调 Python，只能这样：

```bash
python3 "$(paperfit root)/scripts/paperfit_portrait.py" ...
```

不要把路径解释成**论文项目目录下的脚本**。

---

## 执行流程

### A. 分析或冷启动

当用户请求排版分析，或 `data/paperfit-portrait.yaml` 不存在，或用户明确要求重建画像时：

1. 在对话中确认：
   - 主 `.tex` 路径
   - 模板键名（可省略）
   - 页数口径：`main_body` / `with_refs` / `with_appendix`
   - 目标页数
   - 是否 strict、最大轮数

2. 调用：

```bash
paperfit run scripts/paperfit_portrait.py build --main main.tex --page-budget with_refs --target-pages 9
```

3. 读取并总结：
   - `data/paperfit-portrait.yaml`
   - `data/state.json` 中的画像字段

4. 提示下一步：
   - `/fix-layout`
   - `/check-visual`
   - `/show-status`
   - 或直接继续执行用户已经明确要求的后续任务

### B. 刷新画像

当画像已存在，或用户要求刷新时：

```bash
paperfit run scripts/paperfit_portrait.py refresh
```

若主文件变化，附加 `--main <路径>`。

### C. 其它任务

若用户请求的是完整修复、模板迁移、长度调整、局部表格修复、视觉检查或状态查询：

- 先判断是否需要画像或状态初始化
- 若需要，先在内部执行画像构建/刷新
- 然后直接路由到对应任务，不要求用户重新输入其它斜杠命令
- 在输出中明确当前被路由到的任务类型

---

## 输出结果

- `data/paperfit-portrait.yaml`（若执行了画像步骤）
- `data/state.json`（若初始化或刷新了状态）

应向用户简要说明：
- 当前任务类型
- 主文件
- 模板
- 目标页数
- 页数口径
- 推断栏型
- 扫描值 / 用户校正值 / 生效值（若用户提供了图表数量校正）
- 下一步建议或当前已自动进入的子流程

---

## 与 `paperfit wizard` 的关系

- `paperfit wizard`：纯终端交互式 TUI，偏 CLI 使用
- `/paperfit`：Claude Code 内的统一自然语言入口；必要时背后调用 `paperfit_portrait.py`

两者不是同一入口，不能混用脚本路径。
