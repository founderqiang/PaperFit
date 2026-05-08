# PaperFit vs Everything Claude Code — 20 维度架构对比分析

> 对比基准：**everything-claude-code** (v1.10.0, 140K+ stars, 170+ contributors)  
> 分析对象：**PaperFit** (v1.0, 单开发者，垂直领域专用)  
> 生成日期：2026-04-09

---

## 执行摘要

| 维度 | ECC 得分 | PaperFit 得分 | 差距 |
|------|----------|---------------|------|
| **综合成熟度** | 9.5/10 | 4.0/10 | **-5.5** |

ECC 是一个**通用型、生产级、跨平台**的 Agent 增强系统，经过 10+ 个月高强度迭代和 170+ 贡献者检验。PaperFit 是**垂直领域、文档驱动、单平台**的专用系统，尚未在实际项目上运行。

**关键差距**：
1. ECC 有完整的 Hooks 系统（14 种事件类型），PaperFit 仅有 1 个权限配置
2. ECC 有 997+ 内部测试 + CI 流水线，PaperFit 测试是 stub
3. ECC 支持 6+ IDE/平台（Claude Code/Cursor/Codex/Kiro/OpenCode），PaperFit 仅支持 Claude Code
4. ECC 有状态存储和迁移机制，PaperFit 的 state.json 是单点故障

---

## 20 维度详细对比

### 1. 架构设计 (Architecture Design)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 架构模式 | 分层 + 事件驱动 | 顺序管道 | ECC 解耦更优 |
| Agent 数量 | 38+ | 6 | ECC 覆盖更广 |
| Skill 数量 | 156+ | 7 | ECC 可复用性更强 |
| 配置分离 | 独立 config 目录 | YAML 分散配置 | 两者相当 |
| 扩展性 | 插件 marketplace | 无插件系统 | **ECC 胜** |

**PaperFit 不足：**
- Agent 之间无直接通信机制，所有信息通过 orchestrator 中转
- 没有事件驱动架构，无法响应外部事件（如文件修改、编译完成）
- 没有插件系统，无法扩展第三方技能

**改进建议：**
```yaml
# 建议架构改进
event_bus:
  events:
    - COMPILE_SUCCESS
    - VISUAL_DEFECT_DETECTED
    - REPAIR_COMPLETED
    - QUALITY_GATE_PASSED
  subscribers:
    COMPILE_SUCCESS: [rule-engine, layout-detective]
    REPAIR_COMPLETED: [quality-gatekeeper]
```

---

### 2. 便易性 (Ease of Use)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 安装方式 | npm plugin + shell script | 手动 clone | ECC 更便捷 |
| 配置向导 | 交互式 wizard | 无向导 | **ECC 胜** |
| 多语言支持 | 12 种 + 7 种文档翻译 | 仅中文 | ECC 更友好 |
| 选择性安装 | manifest 驱动 | 全量安装 | ECC 更灵活 |
| 进度反馈 | 实时状态面板 | 无反馈 | **ECC 胜** |

**PaperFit 不足：**
- 没有交互式安装向导，用户需手动配置依赖
- 执行 `/fix-layout` 后无进度反馈，用户不知道当前处于哪一步
- 没有选择性安装，所有组件必须一次性安装

**改进建议：**
```bash
# 添加交互式安装脚本
./install.sh --interactive
# 或
npm install -g paperfit-cli
paperfit init
```

---

### 3. Hooks 系统

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| Hook 类型 | 14 种事件 | 0 种 | **ECC 完胜** |
| Hook 数量 | 12+ 活跃 hooks | 0 | |
| 事件覆盖 | sessionStart/End, before/after Shell/File/MCP, subagent, stop | 无 | |
| 跨平台 | Cursor + Kiro + Claude Code | 仅 Claude Code | |
| 安全钩子 | 秘密检测、git bypass 拦截 | 无 | |

**ECC Hooks 完整列表：**
```json
{
  "sessionStart": ["load context", "detect environment"],
  "sessionEnd": ["persist state", "evaluate patterns"],
  "beforeShellExecution": ["block git bypass", "tmux blocker"],
  "afterShellExecution": ["PR URL logging", "build analysis"],
  "afterFileEdit": ["auto-format", "tsc check", "console.log warning"],
  "beforeMCPExecution": ["audit logging"],
  "afterMCPExecution": ["result logging"],
  "beforeReadFile": ["warn .env/.key"],
  "beforeSubmitPrompt": ["detect secrets (sk-, ghp_)"],
  "subagentStart": ["observability logging"],
  "subagentStop": ["completion logging"],
  "beforeTabFileRead": ["block secrets"],
  "afterTabFileEdit": ["auto-format"],
  "preCompact": ["save state"],
  "stop": ["console.log audit"]
}
```

**PaperFit 不足：**
- `.claude/settings.json` 仅配置了 `allow: [Bash]`，无任何 hooks
- 没有 PostToolUse hooks（格式化、类型检查）
- 没有 Stop hooks（最终验证）
- 没有 PreToolUse hooks（参数验证、大小限制）

**改进建议：**
```json
{
  "permissions": {
    "allow": ["Bash", "Write", "Edit"]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "python scripts/validate_tex.py \"$FILE_PATH\"",
        "description": "Validate LaTeX syntax after edit"
      }
    ],
    "Stop": [
      {
        "command": "python scripts/compile.sh && echo 'Build OK'",
        "description": "Final compilation verification"
      }
    ]
  }
}
```

---

### 4. 测试与评测 (Testing & Evals)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 测试数量 | 997+ passing | 0 (stubs) | **ECC 完胜** |
| CI 流水线 | GitHub Actions (matrix) | 无 | |
| 测试覆盖 | agents/skills/commands/hooks | 无 | |
| 评测基准 | eval-harness skill | inject_defects.py (stub) | |
| 回归测试 | 每次 PR 强制运行 | 无 | |

**ECC CI 配置：**
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    node: ['18.x', '20.x', '22.x']
    pm: [npm, pnpm, yarn, bun]
```

**PaperFit 不足：**
- `scripts/inject_defects.py` 是空壳（仅 219 行，无实际逻辑）
- `scripts/benchmark_runner.py` 是空壳（仅 246 行）
- 没有 CI 流水线，无法自动化验证修改
- 没有单元测试验证 Agent 行为

**改进建议：**
```python
# scripts/validation_scaffold.py（示意）
import pytest
from agents.rule_engine import RuleEngine

def test_overfull_detection():
    log_content = r"Overfull \hbox (10.5pt too wide)"
    engine = RuleEngine()
    defects = engine.detect(log_content)
    assert len(defects) == 1
    assert defects[0]['category'] == 'D1'
```

---

### 5. 状态管理 (State Management)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 存储方式 | SQLite + JSON | 仅 JSON | ECC 更可靠 |
| Schema 验证 | JSON Schema + migrations | 无验证 | **ECC 胜** |
| 版本控制 | state version + git | 仅 backup 目录 | |
| 查询能力 | SQL queries | 点号访问 | |
| 持久化 | session 级 + 跨会话 | 仅跨会话 | |

**ECC State Store Schema：**
```json
{
  "$schema": "schemas/state-store.schema.json",
  "version": 2,
  "fields": {
    "id": "string",
    "created_at": "timestamp",
    "session_id": "string",
    "installed_components": ["array"],
    "metrics": "object"
  }
}
```

**PaperFit 不足：**
- `state_manager.py` 无 schema 验证，损坏后无法自动修复
- 没有状态版本控制，无法追踪结构变更
- 备份仅保留 20 个，长期任务可能丢失关键历史
- 没有 Git 集成，无法整体回滚到某个状态

**改进建议：**
```python
# scripts/state_manager.py 增强
import jsonschema

STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "current_round": {"type": "integer", "minimum": 0},
        "status": {"type": "string", "enum": ["INIT", "RUNNING", "DONE", "FAILED"]}
    },
    "required": ["version", "current_round", "status"]
}

def validate_state(state: dict) -> bool:
    jsonschema.validate(state, STATE_SCHEMA)
```

---

### 6. 跨平台支持 (Cross-Platform)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 支持平台 | 6+ (Claude Code/Cursor/Codex/Kiro/OpenCode/Gemini) | 1 (Claude Code) | **ECC 完胜** |
| IDE 集成 | .cursor/ + .kiro/ + .opencode/ | 仅 .claude/ | |
| 配置同步 | 多平台统一 schema | 无 | |
| 文档翻译 | 7 种语言 | 仅中英 | |

**ECC 目录结构：**
```
.agents/        # Claude Code
.cursor/        # Cursor IDE
.kiro/          # Kiro IDE
.opencode/      # OpenCode
.codex/         # OpenAI Codex
```

**PaperFit 不足：**
- 仅支持 Claude Code，无法在 Cursor 或其他平台使用
- 没有 IDE 特定的 hooks 和 rules
- 文档仅中英双语，国际化程度低

---

### 7. 安全与合规 (Security & Compliance)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 秘密检测 | beforeSubmitPrompt hook (sk-, ghp_, AKIA) | 无 | **ECC 胜** |
| MCP 审计 | beforeMCPExecution | 无 MCP 支持 | |
| Git 保护 | block-no-verify hook | 无 | |
| 文件访问控制 | beforeTabFileRead | 无 | |
| 安全扫描 | AgentShield 集成 (102 rules) | 无 | |

**PaperFit 不足：**
- 没有秘密检测，用户可能无意中提交 API 密钥
- 没有文件访问控制，可能读取敏感文件
- 没有 Git bypass 保护

**改进建议：**
```python
# scripts/pre_tool_use.py（新建）
import re

SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{32}', 'OpenAI API Key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
]

def check_for_secrets(content: str) -> list:
    findings = []
    for pattern, name in SECRET_PATTERNS:
        if re.search(pattern, content):
            findings.append(f"Detected {name}")
    return findings
```

---

### 8. 可观测性 (Observability)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 日志记录 | session 级 + agent 级 | 无 | **ECC 胜** |
| Metrics | cost tracking, token usage | 无 | |
| Dashboard | PM2 + web UI | 无 | |
| 会话导出 | sessions command | 无 | |
| Agent 追踪 | subagent start/stop logs | 无 | |

**ECC 可观测性工具：**
```bash
/sessions          # 查看历史会话
/cost-audit        # 追踪 token 消耗
/harness-audit     # 检查 harness 配置
```

**PaperFit 不足：**
- 没有 Agent 决策日志，无法追溯为什么某个修改被建议
- 没有 metrics 追踪（如每轮缺陷消除率、修复成功率）
- 没有可视化 dashboard 展示迭代进度

---

### 9. 技能实现 (Skill Implementation)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 实现方式 | 可执行代码 + Markdown | 仅 Markdown | **ECC 胜** |
| 技能数量 | 156+ | 7 | |
| 技能路由 | marketplace.json | config/vto_taxonomy.yaml | |
| 动态加载 | 支持 | 无 | |
| 技能测试 | 每个 skill 有测试 | 无 | |

**PaperFit 问题：**
所有 `SKILL.md` 是文档，不是代码：
```markdown
# skills/overflow-repair/SKILL.md
## 修复策略
1. 段落溢出：断词、emergencystretch
2. 表格溢出：tabular→tabularx
```

**ECC 做法：**
```javascript
// skills/e2e-testing/index.js
module.exports = {
  run: async (page) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();
  }
}
```

---

### 10. 配置管理 (Configuration)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 配置文件 | 集中 + 分散混合 | 仅分散 YAML | ECC 更优 |
| 配置验证 | JSON Schema | 无验证 | **ECC 胜** |
| 配置迁移 | migrations.js | 无 | |
| 热加载 | 支持 | 无 | |

**PaperFit 配置文件：**
```
config/vto_taxonomy.yaml   # 缺陷分类
config/layout_rules.yaml   # 阈值
config/writing_rules.yaml  # 写作规则
config/templates.yaml      # 模板参数
config/agent_roles.yaml    # Agent 职责
```

**问题：** 5 个 YAML 文件分散，没有统一入口和验证

---

### 11. 文档质量 (Documentation)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 文档语言 | 7 种 | 2 种 (中英) | ECC 更广泛 |
| 文档结构 | /docs + /skills 内嵌 | /docs 单文件 | ECC 更系统 |
| 代码示例 | 每个 skill 有示例 | 伪代码为主 | |
| 更新频率 | 随版本同步 | 静态 | |

**ECC 文档结构：**
```
docs/
├── en-US/
├── zh-CN/
├── ja-JP/
├── ko-KR/
└── pt-BR/
```

---

### 12. 版本控制与发布 (Versioning & Release)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 版本管理 | SemVer + CHANGELOG | 无 | **ECC 胜** |
| 发布流程 | GitHub Releases + npm | 无 | |
| 回滚机制 | git revert + state migrations | 仅 backup 目录 | |
| 兼容性保证 | break changes 标注 | 无 | |

---

### 13. 错误恢复 (Error Recovery)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 降级策略 | 有 (conservative_mode) | 仅回滚 | **ECC 胜** |
| Escalation | 连续失败通知用户 | 仅警告 | |
| 智能诊断 | 缺失包自动建议 | 无 | |

**PaperFit 不足：**
- `code-surgeon` 修改失败后只能回滚，没有降级策略
- 连续 3 轮无进展时仅标注警告，没有 escalation

---

### 14. 并行与性能 (Parallelization & Performance)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| Agent 并行 | 支持 (cascade method) | 顺序执行 | **ECC 胜** |
| Git worktree | 支持 | 无 | |
| 模型路由 | Haiku/Sonnet/Opus 选择 | 固定 | |

**PaperFit 不足：**
- 所有 Agent 调用是严格顺序的（order 1→2→3→4→5）
- `rule-engine` 和 `layout-detective` 可以并行，但设计是串行的

---

### 15. 用户交互 (User Interaction)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 交互命令 | 24+ commands | 6 commands | ECC 更丰富 |
| 进度反馈 | 实时状态 | 无 | **ECC 胜** |
| 解释模式 | 有 (Explainable AI) | 无 | |
| 摘要模式 | 有 | 无 | |

---

### 16. 持续学习 (Continuous Learning)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 模式提取 | instinct-based learning | 无 | **ECC 胜** |
| 技能进化 | skill-evolution foundation | 静态 SKILL.md | |
| 会话学习 | 从历史会话提取 | 无 | |

---

### 17. 社区与生态 (Community & Ecosystem)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 贡献者 | 170+ | 1 | **ECC 完胜** |
| Stars | 140K+ | 0 (未公开) | |
| PRs 合并 | 30+ | 0 | |
| Marketplace | GitHub App + npm | 无 | |

---

### 18. 依赖管理 (Dependency Management)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 包管理 | npm/pnpm/yarn/bun | pip 隐式依赖 | ECC 更规范 |
| 版本锁定 | package-lock.json | 无 requirements.txt | **ECC 胜** |
| 自动安装 | install.sh 处理 | 手动 | |

**PaperFit 不足：**
- 没有 `requirements.txt`，依赖不透明
- Poppler 等系统级依赖需手动安装

---

### 19. 代码质量 (Code Quality)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| Linting | ESLint + Prettier | 无 | **ECC 胜** |
| Type checking | TypeScript | 无类型 (Python) | |
| Code review | beforeSubmitPrompt hook | 无 | |
| 提交规范 | Conventional Commits | 无规范 | |

---

### 20. 垂直领域深度 (Domain Depth)

| 方面 | ECC | PaperFit | 评价 |
|------|-----|----------|------|
| 通用性 | 全领域 | LaTeX 排版专用 | PaperFit 更专注 |
| 领域知识 | 通用模式 | VTO 缺陷分类体系 | **PaperFit 胜** |
| 多模态能力 | 文本为主 | 视觉+ 源码+日志+PDF | **PaperFit 胜** |
| 闭环迭代 | 无 | Vision-in-the-Loop | **PaperFit 胜** |

**PaperFit 优势：**
- ECC 是通用框架，PaperFit 在 LaTeX 排版领域有更深知识
- PaperFit 的 Vision-in-the-Loop 闭环是 ECC 没有的设计
- VTO 缺陷分类体系（5 类 17 种）是领域特定的创新

---

## 差距汇总

| 维度 | 差距 | 优先级 | 预计修复工时 |
|------|------|--------|-------------|
| Hooks 系统 | -14 | CRITICAL | 40h |
| 测试与评测 | -997 tests | CRITICAL | 60h |
| 状态管理 | -Schema/-SQLite | HIGH | 20h |
| 安全合规 | -Secret detection | HIGH | 16h |
| 跨平台 | -5 platforms | MEDIUM | 30h |
| 技能实现 | -Python 库 | HIGH | 50h |
| 并行执行 | -Agent parallel | MEDIUM | 24h |
| 可观测性 | -Metrics/-Logs | LOW | 16h |
| 配置验证 | -Schema 验证 | LOW | 8h |
| 版本控制 | -CI/-Release | MEDIUM | 20h |
| 错误恢复 | -Escalation | MEDIUM | 12h |
| 文档 | -5 languages | LOW | 40h |
| 依赖管理 | -requirements.txt | LOW | 2h |
| 代码质量 | -Linting | LOW | 8h |
| 用户交互 | -Progress UI | LOW | 16h |

**总差距：** PaperFit 在 20 个维度中，15 个落后于 ECC，5 个领先（垂直领域深度相关）

---

## 建议实施路线

### Phase 0 (立即, 1 周)
1. 添加 `requirements.txt`
2. 添加 Hooks 系统（至少 PostToolUse + Stop）
3. 添加状态 Schema 验证

### Phase 1 (短期, 2-4 周)
1. 实现测试脚手架（20+ 核心测试）
2. 技能 Python 化（overflow-repair 等）
3. 添加秘密检测钩子
4. 添加进度反馈机制

### Phase 2 (中期, 1-2 月)
1. 添加 CI 流水线
2. 实现 Agent 并行执行
3. SQLite 状态存储
4. 错误恢复机制

### Phase 3 (长期, 2-3 月)
1. 跨平台支持（Cursor 优先）
2. 可观测性 dashboard
3. 多语言文档

---

## 结论

PaperFit 作为一个垂直领域专用系统，在 **Vision-in-the-Loop 闭环设计** 和 **VTO 缺陷分类体系** 上有独特创新，这是 ECC 没有的。但在 **工程化成熟度**（Hooks、测试、状态管理、安全、跨平台）上落后 ECC 约 5-10 分（满分 10 分）。

**核心建议：** 保持领域深度优势，补齐工程化短板。优先实施 Phase 0+1（约 100 小时），可将成熟度提升至 6.5/10。
