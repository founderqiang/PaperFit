# PaperFit 架构不足与改进路线图

> 生成日期：2026-04-09  
> 审查范围：agents/, config/, skills/, scripts/, commands/

---

## 执行摘要

PaperFit 是一个采用 Vision-in-the-Loop 闭环架构的 Claude Code 多智能体系统，用于 LaTeX 论文排版质量优化。相较初始评审阶段，系统已经补上了一批可执行组件：状态 schema、runtime CLI、OpenCV 视觉检测、视觉信号聚合、修复器单测、基础 CI 均已落地。

当前核心问题已从“几乎全靠文档驱动”演变为“代码已明显增长，但真相源尚未完全收敛”：部分能力存在双份实现，部分状态字段尚未彻底封口，真实项目 smoke 与 benchmark 仍未进入主验证链。

---

## 架构不足总览

| ID | 类别 | 严重性 | 影响范围 | 修复难度 |
|----|------|--------|----------|----------|
| AG-01 | Agent 串行执行 | HIGH | 性能 | MEDIUM |
| AG-02 | 状态单点故障 | HIGH | 可靠性 | MEDIUM |
| AG-03 | 视觉检测自动化覆盖不足 | HIGH | 准确性 | MEDIUM |
| AG-04 | 测试基准缺失 | MEDIUM | 质量 | LOW |
| AG-05 | 错误恢复弱 | MEDIUM | 可靠性 | MEDIUM |
| AG-06 | 技能非可执行代码 | HIGH | 可维护性 | HIGH |
| AG-07 | 配置分散无验证 | MEDIUM | 可靠性 | LOW |
| AG-08 | 无版本控制/回滚 | MEDIUM | 可用性 | MEDIUM |
| AG-09 | 可观测性不足 | LOW | 调试 | LOW |
| AG-10 | 用户交互不足 | LOW | 体验 | LOW |
| AG-11 | 缺少上下文感知 | LOW | 适用性 | MEDIUM |
| AG-12 | 跨模板迁移风险 | MEDIUM | 可靠性 | MEDIUM |

---

## 详细问题与改进建议

### AG-01: Agent 串行执行，缺乏并行能力

**问题描述：**  
所有 Agent 调用是严格顺序的（order 1→2→3→4→5），无法并行执行独立任务。例如 `rule-engine`（分析.log）和 `layout-detective`（分析页图）可以并行，但当前设计是串行的。

**影响：**
- 每轮迭代时间 = 各 Agent 耗时之和
- 无法利用 Claude Code 的并行 Task 能力

**改进方案：**
```yaml
# config/agent_roles.yaml 改进建议
parallel_groups:
  - name: detection_phase
    agents: [rule-engine, layout-detective]
    condition: always_parallel
  - name: repair_phase
    agents: [code-surgeon, semantic-polish]
    condition: disjoint_defects  # 缺陷不重叠时可并行
```

**优先级：** HIGH  
**预计收益：** 每轮迭代时间减少 40-60%

---

### AG-02: 状态管理是单点故障

**问题描述：**  
`state.json` 损坏或丢失后，整个闭环无法恢复。备份机制只保留 20 个历史版本，长期任务可能丢失关键状态。没有状态版本控制和 schema 验证。

**影响：**
- 系统中断后无法精确恢复
- 错误状态格式可能导致 Agent 解析失败

**改进方案：**
1. 引入状态版本号和 schema 验证：
```python
# scripts/state_manager.py 增强
STATE_SCHEMA = {
    "version": int,
    "task": {"id": str, "created_at": str, "target_pages": list},
    "current_round": int,
    "status": str,  # INIT, RUNNING, DONE, FAILED
    "defect_summary": {...},
    "history": [{"round": int, "changes": [...]}]
}
```

2. 增加状态快照到 Git：
```bash
# 每轮结束后自动提交
git add data/state.json
git commit -m "[state] Round $ROUND snapshot"
```

**优先级：** HIGH  
**预计收益：** 中断恢复时间从小时级降至分钟级

---

### AG-03: 视觉检测自动化已起步，但覆盖仍不足

**问题描述：**  
系统已具备 `scripts/cv_detector.py`、`scripts/detect_column_void.py` 与 `scripts/visual_signal_aggregator.py`，说明 OpenCV 自动化链路已经建立；但视觉阈值仍有部分散落在代码内，个别对象级/跨页缺陷仍主要依赖人工审查与规则拼接。

**影响：**
- 检测速度慢（每页需人工审查）
- 一致性无法保证（不同轮次可能判断不同）
- 无法检测亚像素级问题（如 1-2pt 的溢出）

**改进方案：**
```python
# scripts/cv_detector.py（已存在，需继续扩展）
import cv2
import numpy as np

def detect_whitespace(page_image, threshold=0.20):
    """自动检测页面留白比例"""
    gray = cv2.cvtColor(page_image, cv2.COLOR_RGB2GRAY)
    white_pixels = np.sum(gray > 240)
    total_pixels = gray.size
    return white_pixels / total_pixels

def detect_overflow(page_image, margin_bbox):
    """检测内容是否溢出边界"""
    # 边缘检测 + 轮廓分析
    ...
```

**优先级：** HIGH  
**预计收益：** 检测速度提升 10 倍，准确率提升至 95%+

---

### AG-04: 测试链已建立，但真实 benchmark 与 smoke 仍不足

**问题描述：**  
仓库已包含较完整的 `unittest` 主链、基础 CI、`inject_defects.py` 与 `benchmark_runner.py`。当前不足不再是“完全没有测试”，而是：
- 真实项目 smoke 未进入主 CI
- benchmark 还没有成为日常回归入口
- 测试覆盖虽广，但仍存在“结构检查类脚本最近才接入主链”的收敛问题

**影响：**
- 无法验证修复策略是否有效
- 重构时无法保证向后兼容
- 新增缺陷类型时无法回归测试

**改进方案：**
1. 创建测试语料库：
```
test_corpus/
├── minimal_working/      # 无缺陷样本
├── overflow_samples/     # D 类缺陷样本
├── whitespace_samples/   # A 类缺陷样本
└── float_samples/        # B 类缺陷样本
```

2. 实现基准测试运行器：
```python
# scripts/benchmark_runner.py（已存在，需变为日常回归入口）
def run_benchmark():
    results = []
    for sample in test_corpus:
        defects_before = detect_defects(sample)
        run_fix_layout(sample)
        defects_after = detect_defects(sample)
        results.append({
            "sample": sample.name,
            "elimination_rate": calculate_elimination(defects_before, defects_after)
        })
    return results
```

**优先级：** MEDIUM  
**预计收益：** 每次修改可验证效果，回归测试覆盖率 80%+

---

### AG-05: 错误恢复机制弱

**问题描述：**  
`code-surgeon` 修改失败后只能回滚，没有降级策略。连续 3 轮无进展时仅标注警告，没有自动 escalation 机制。编译失败时缺乏智能诊断（如缺失宏包的自动安装建议）。

**影响：**
- 系统可能在同一问题上反复失败
- 用户需要手动介入才能继续

**改进方案：**
```yaml
# config/error_recovery.yaml（新建）
escalation_policy:
  consecutive_failures: 3
  actions:
    - notify_user: true
    - suggest_manual_review: true
    - fallback_strategy: conservative_mode  # 只修复确定性问题

compile_error_handling:
  missing_package:
    action: suggest_install
    command: "tlmgr install {package_name}"
  undefined_macro:
    action: search_preamble
    fallback: comment_out
```

**优先级：** MEDIUM

---

### AG-06: 技能已部分代码化，但存在重复实现与真相源分裂

**问题描述：**  
`skills/latex_fixers/*` 已经提供了一批可执行修复函数，不再是纯 Markdown 技能体系；但同类能力同时还存在于 `scripts/*_fixers.py` 中，造成双份实现、测试分散、行为不完全一致的问题。

**影响：**
- 每次修复依赖 Agent 的临场发挥
- 容易引入人为错误
- 无法单元测试修复逻辑

**改进方案：**
```python
# skills/latex_fixers/__init__.py（已存在，需继续收敛）
from .overflow import fix_overfull_hbox
from .whitespace import adjust_paragraph_spacing
from .float import optimize_float_placement

__all__ = [
    "fix_overfull_hbox",
    "adjust_paragraph_spacing",
    "optimize_float_placement",
]

# skills/latex_fixers/overflow.py
def fix_overfull_hbox(tex_content: str, line_number: int) -> str:
    """自动修复指定行的溢出问题"""
    lines = tex_content.split('\n')
    target_line = lines[line_number - 1]
    
    # 策略 1: 插入断词
    if can_hyphenate(target_line):
        return insert_hyphation(tex_content, line_number)
    
    # 策略 2: 添加 emergencystretch
    return add_emergencystretch(tex_content)
```

**优先级：** HIGH  
**预计收益：** 修复成功率从 70% 提升至 95%+

---

### AG-07: 配置验证已存在，但口径仍未完全统一

**问题描述：**  
`scripts/config_validator.py` 已存在，说明“无配置验证”这一问题已被部分修复。当前不足在于：
- 不是所有运行时阈值都真正从配置读取
- 配置 schema 与代码行为仍可能漂移
- 缺少“配置字段被代码消费”的覆盖性验证

**影响：**
- 配置错误难以发现
- 不同配置之间可能存在冲突

**改进方案：**
```python
# scripts/config_validator.py（已存在，需增强消费一致性验证）
import yaml
from pydantic import BaseModel, validator

class LayoutConfig(BaseModel):
    whitespace_threshold: float
    table_width_range: tuple
    
    @validator('whitespace_threshold')
    def check_threshold(cls, v):
        assert 0 < v < 1, "阈值必须在 0-1 之间"
        return v

def validate_all_configs():
    errors = []
    for config_file in CONFIG_FILES:
        try:
            with open(config_file) as f:
                data = yaml.safe_load(f)
            # 根据文件类型选择对应的 schema 验证
            validate_schema(data, config_file)
        except Exception as e:
            errors.append(f"{config_file}: {e}")
    return errors
```

**优先级：** LOW

---

### AG-08: 缺少版本控制和回滚策略

**问题描述：**  
`backup` 目录只保留文件备份，没有 Git 集成。多轮修改后无法整体回滚到某个历史状态。没有 diff 可视化，用户无法直观理解修改内容。

**改进方案：**
```bash
# scripts/git_rollback.sh（新建）
#!/bin/bash
# 列出所有 PaperFit 相关的提交
git log --grep="\[PaperFit\]" --oneline

# 回滚到指定轮次
git revert $(git log --grep="\[PaperFit\] Round $ROUND" -n 1 --format=%H)

# 或显示 diff
git diff $(git log --grep="\[PaperFit\] Round $ROUND" -n 1 --format=%H)^..HEAD
```

**优先级：** MEDIUM

---

### AG-09: 可观测性不足

**问题描述：**  
没有日志记录 Agent 决策过程。没有 metrics 追踪（如每轮缺陷消除率、修复成功率）。没有可视化 dashboard 展示迭代进度。

**改进方案：**
```python
# scripts/metrics_collector.py（新建）
class MetricsCollector:
    def __init__(self):
        self.metrics = {
            "rounds": [],
            "defects_fixed": [],
            "defects_introduced": [],
            "compilation_failures": [],
        }
    
    def record_round(self, round_num, before, after):
        self.metrics["rounds"].append({
            "round": round_num,
            "defects_before": len(before),
            "defects_after": len(after),
            "elimination_rate": (len(before) - len(after)) / len(before)
        })
    
    def generate_report(self):
        # 输出文本摘要或 HTML 报告
        ...
```

**优先级：** LOW

---

### AG-10: 用户交互设计不足

**问题描述：**  
用户无法在中途介入调整策略（如"优先修复表格，图表下轮处理"）。没有解释模式（Explainable AI）说明为什么某个修改被建议。多轮迭代后输出冗长，缺少摘要模式。

**改进方案：**
```markdown
# commands/fix-layout.md 增强
## 交互命令
- `/paperfit-priority` - 调整修复优先级
- `/paperfit-explain` - 解释当前修改的原因
- `/paperfit-summary` - 输出本轮修改摘要
- `/paperfit-undo` - 回滚上一轮修改
```

**优先级：** LOW

---

### AG-11: 缺少上下文感知

**问题描述：**  
不同学科论文（CS vs 生物 vs 物理）有不同排版惯例，但系统使用统一规则。没有领域特定的配置（如数学公式密集 vs 图表密集的论文）。

**改进方案：**
```yaml
# config/domain_profiles.yaml（新建）
cs_theory:
  characteristics: [dense_math, few_figures]
  relaxed_rules:
    - allow_two_column_tables
    - allow_small_font_in_math
  strict_rules:
    - no_page_overflow

biology_experimental:
  characteristics: [many_figures, wide_tables]
  relaxed_rules:
    - allow_landscape_tables
    - allow_figure_grouping
```

**优先级：** LOW

---

### AG-12: 跨模板迁移风险高

**问题描述：**  
`template-migrator` 需要同时修改 documentclass、图表尺寸、宏包等多个位置。一处修改遗漏可能导致编译失败。没有原子性保证（要么全部成功，要么全部回滚）。

**改进方案：**
```python
# skills/template_migrator.py（新建）
class TemplateMigrator:
    def __init__(self):
        self.changes = []
        self.backup = None
    
    def migrate(self, from_template, to_template):
        self.backup = create_backup()
        try:
            self.change_documentclass(to_template)
            self.adjust_column_width(to_template)
            self.update_packages(to_template)
            self.verify_compilation()  # 验证编译
            return True
        except Exception as e:
            self.rollback()  # 原子性回滚
            raise e
```

**优先级：** MEDIUM

---

## 实施优先级

### Phase 1 (立即实施，1-2 周)
1. **AG-02** - 状态管理增强收尾（尤其是 `artifacts.*` 真相源封口）
2. **AG-04** - 将真实 smoke / benchmark 前移到主验证体系
3. **AG-06** - 收敛重复 fixer 实现，明确 canonical implementation

### Phase 2 (短期，2-4 周)
1. **AG-07** - 配置消费一致性验证
2. **AG-05** - 错误恢复机制
3. **AG-08** - 原子回滚与 Git/快照集成

### Phase 3 (中期，1-2 月)
1. **AG-01** - Agent 并行执行
2. **AG-03** - 扩大 CV 自动检测覆盖
3. **AG-12** - 原子性模板迁移

### Phase 4 (长期，2-3 月)
1. **AG-09** - 可观测性（metrics + dashboard）
2. **AG-10** - 用户交互增强
3. **AG-11** - 领域特定配置

---

## 附录：相关文件索引

| 文件 | 问题 | 改进建议 |
|------|------|----------|
| `agents/orchestrator-agent.md` | AG-01 | 增加并行组定义 |
| `agents/layout-detective-agent.md` | AG-03 | 集成 CV 检测结果 |
| `scripts/state_manager.py` | AG-02 | 增加 schema 验证 |
| `skills/*/SKILL.md` | AG-06 | 补充 Python 实现 |
| `config/*.yaml` | AG-07 | 统一验证入口 |

---

**生成命令：** `ECC:ARCHITECTURE-REVIEW`  
**审查人：** Claude Code  
**下次审查日期：** 2026-05-09
