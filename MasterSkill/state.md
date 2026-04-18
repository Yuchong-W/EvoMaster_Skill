# MasterSkill 项目状态文档

## 项目概述

**MasterSkill** 是一个基于 Benchmark 驱动的技能发现系统。给定基础模型和 benchmark（如 SkillsBench），系统通过迭代研究，发现帮助模型超越 SOTA 的外部技能。

**关键约束**: 模型权重不变，技能是外部工具带描述，模型可调用。

**目标**: Base Model + Skills > SOTA on the full benchmark

---

## 2026-04-17 最新状态

### 会话恢复入口

- 重启会话后优先看：
  - [session_resume.md](/home/yuchong/auto-research-team/MasterSkill/session_resume.md)
- 这份文件记录了：
  - 当前已完成的 pre-evolution baseline
  - 哪两个 baseline 结果是 stale、需要补跑
  - Docker 恢复后的第一条命令
  - 下一步比较实验该怎么继续

### 已验证结果

- `enterprise-information-search`
  - 本地 official real test 已稳定通过
  - `base_attempt` 仍可通过
  - post-pass 优化现在也已经蒸馏出两个本地 official real-test passing skill：
    - `enterprise-direct-evidence-answer`
    - `enterprise-direct-answer-minimal`
  - 当前更优的第二轮 skill 已记录到真实收益：
    - `duration 406.82s -> 343.18s`
    - `tokens 1394607 -> 1033712`
- `financial-modeling-qa`
  - 本地 official real test 已通过
  - pass 后已经成功蒸馏出一个更紧凑、可复用的 task-local skill：
    - `financial-modeling-pairwise-match-delta`
- `pddl-tpp-planning`
  - 本地 official real test 已通过
  - `base_attempt` 可通过
  - post-pass skill 现在也已经成功蒸馏并被系统接受：
    - `pddl-tpp-batch-fastpath`
  - 当前记录到的真实收益：
    - `duration 148.58s -> 131.10s`
    - 输出 artifacts 与 bundled checker / linter 一致通过

### 当前系统能力

- 可以直接从 repo 根目录用 `python3 run_local.py --task <task_id>` 运行
- 现在已经有纯净基线模式：
  - `python3 run_local.py --task <task_id> --pre-evolution-baseline`
  - 这个模式会禁止 `base_attempt` 读取 task-local bundled skills
  - 并且在 base attempt 后直接停止，不进入复用、研究、Judger 或 post-pass
- hard case 的环境链路不再容易死在：
  - `apt-get update` 无限挂起
  - verifier 预热失败直接终止整条 real test
  - 基础 attempt 预算过短导致的假阴性
- post-pass optimization 已经从“一次性压缩尝试”升级成“带失败反馈的多轮优化”
- Judger / artifact 链路现在会优先暴露小型输出成品：
  - execution log 里先展示 output artifacts，再展示执行叙述
  - Judger 会同时看到 execution result 的开头和结尾，而不是只看前 3000 字

### 仍然存在的核心问题

- 目前最强的 skill 贡献证据，已经从“只看 pass/fail”扩展到：
  - 是否在固定预算下减少超时风险
  - 是否减少 token / runtime
  - 是否把超长 task-local skill 压缩成更短但仍可 passing 的 solve path
- 当前仍然存在的核心问题是：
  - Docker daemon 当前不稳定，导致剩余两个 baseline task 还没补完
  - `react-performance-debugging` 和 `taxonomy-tree-merge` 的 pre-evolution 记录目前是 stale，需要在 Docker 恢复后重跑
  - `enterprise-information-search` 的 task-required `tokens` 字段仍然是 task-level numeric helper，不是模型 runtime 的真实 usage telemetry
  - 部分候选 skill 仍会因为 skill 文本膨胀而增加 `skill_md_size`，需要继续压缩 prompt 负担
  - 还需要把这种“pass 后继续优化并正式接受收益”的路径复制到更多 hard tasks

### 对论文分类的解释

- `skillsbench_task_classification.md` 里的零通过分类仍然是历史 benchmark 报告结论
- 当前本地结果不应改写那份历史分类
- 但它已经说明：至少一部分 zero-pass task 之前同时受到了 harness fidelity、verifier bootstrap、timeout budget 的影响

---

## 核心架构

### 目录结构

```
MasterSkill/
├── agents/           # 四大 Agent: Searcher, Analyzer, Critic, Reflector
├── core/            # 核心类型定义和配置
├── judge/           # Judger 评估系统 + Feedback 格式
├── memory/          # 三层 Memory 系统
├── proposer/        # QuickProposer 快速修复
├── runner/          # BenchmarkRunner 主控 + DockerExecutor
├── skill/           # Skill 创建和仓库管理
└── main.py          # 入口
```

---

## 控制流（完整）

### 入口: `BenchmarkRunner.run_benchmark()`

```python
for task_id in unsolved_tasks:
    status = run_task(task_id)
```

### 主循环: `BenchmarkRunner.run_task(task_id)`

```
Step 1: Model 尝试任务
    ↓ fail
Step 2: Analyzer 分析弱点
    ↓
Step 3: 尝试复用已有 Skills (试探性复用)
    → 若成功 → SOLVED
    ↓ 全部失败
Step 4: Research Team 构建新 Skill
    ↓
Step 5: QuickProposer / Judger 循环 (最多 4 次 real_test_failures)

    ┌─────────────────────────────────────────────────────┐
    │  while real_test_failures < 4:                     │
    │                                                   │
    │  [A] judger_result = evaluate(skill, criteria)    │
    │       ↓                                           │
    │  ┌─ judger PASS ──────────────────────────────┐    │
    │  │  real_test_result = run_real_test(skill) │    │
    │  │  ↓                                        │    │
    │  │  ┌─ real_test PASS ──→ SOLVED ─────────┐ │    │
    │  │  │                                     │ │    │
    │  │  └─ real_test FAIL ──→ failures++,     │ │    │
    │  │                      criteria=stricter,│ │    │
    │  │                      continue           │ │    │
    │  └─────────────────────────────────────────┘    │
    │       ↓                                          │
    │  ┌─ judger FAIL ──────────────────────────────┐  │
    │  │  QuickProposer 循环 (最多 3 次)            │  │
    │  │  propose_fix() → 再次 evaluate()          │  │
    │  │  ↓                                        │  │
    │  │  ┌─ judger PASS ──→ break ──────────────┐ │  │
    │  │  └─ judger FAIL (3次后) ──→ Research ───┘ │  │
    │  │           ↓                                 │  │
    │  │  judger_research_triggers++               │  │
    │  │  ↓                                         │  │
    │  │  ┌─ triggers >= 2 ──→ Reflector ─────────┐ │  │
    │  │  │  (judger_too_strict? 调整 criteria)   │ │  │
    │  │  └───────────────────────────────────────┘ │  │
    │  │  Research new skill                       │  │
    │  │  (保持 judger_research_triggers 不重置)   │  │
    │  └─────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────┘
    ↓ 4 次 real_test_failures
ABANDONED
```

### 关键计数器行为

| 事件 | `real_test_failures` | `judger_research_triggers` |
|------|----------------------|---------------------------|
| 初始化 | 0 | 0 |
| real_test 失败 | +1 | **不变** (不重置!) |
| QuickProposer 3次后仍 FAIL | 不变 | +1 |
| judger PASS (到达 real_test) | 不变 | **重置为 0** |
| Reflector 触发后 | 不变 | 重置为 0 |
| Research 创建新 skill | 不变 | **不变** (不重置!) |

**重要**: `judger_research_triggers` 只在两种情况重置:
1. Judger 实际通过（到达 real_test）
2. Reflector 触发后

---

## Memory 三层架构

### Layer 1: Shallow Memory (`ShallowMemory`)
- **内容**: Skill 仓库 (SKILL.md 格式) + 每任务 trace 历史
- **路径**: `data_dir/shallow/`
- **访问**: Searcher, SkillCreator 完全访问
- **作用**: 快速 Skill 复用，调试追踪

### Layer 2: Task Experience (`TaskExperienceMemory`)
- **内容**: 每任务最多 2 条经验记录
- **路径**: `data_dir/task_experience/task_experiences.json`
- **访问**: Analyzer, Reflector 可写
- **作用**: 记录成功/失败原因，避免重复尝试

### Layer 3: Meta Memory (`MetaMemoryStore`)
- **内容**: 跨任务元知识，有效/无效方法
- **路径**: `data_dir/meta/meta_memory.json`
- **Key 格式**: `problem_type::domain::problem_modeling`
- **访问**: Analyzer, Reflector 可写
- **作用**: 迁移学习，指导新任务

### 内存 Key 生成
```python
def _make_key(problem_type, domain, modeling):
    return f"{problem_type.value}::{domain}::{modeling}"
```

---

## Agent 职责

### Searcher
- **Memory 访问**: 所有层
- **职责**: 独家搜索，避免重复工作
- **输出**: search_summary + 建议方向

### Analyzer
- **Memory 访问**: 仅浅层 trace
- **职责**: 分析失败原因，防止草率归因
- **输出**: problem_type_refinement, suggested_directions, root_cause

### Critic
- **Memory 访问**: 无 (仅比较新旧提交)
- **职责**: 防止"磨洋工"，检查本质区别
- **验收标准** (满足任一即可):
  - 新方法引入
  - 更清晰的形式化
  - 代码实现
  - 关键数据含义澄清
  - 工程细节指定
  - 详细 API 使用说明

### Reflector
- **触发条件**: `judger_research_triggers >= 2` (连续 2 次 Research 触发且无 judger pass)
- **职责**: 自省 Judger 是否过于严格
- **诊断**: `judger_too_strict` 或 `skill_inadequate`

### QuickProposer
- **范围**: 表面修复 (措辞、细节)
- **限制**: 不能修改核心方法
- **迭代**: 最多 3 次

### Judger
- **评估对象**: Skill **执行结果**，不是 Skill 本身
- **成本**: ≈ Real test，但返回更丰富诊断
- **设计原则**: 严格但公平
  - 假阳性 (wrong passed): **必须避免** - 浪费 real test
  - 假阴性 (correct blocked): 可接受 - 浪费一次迭代
- **评估标准**:
  1. 约束违反? (必须阻止)
  2. 格式/缺失输出? (关键则阻止)
  3. 方法根本错误? (必须阻止)
  4. 事实错误? (关键事实阻止)
  5. 非阻塞问题? (记录但允许)

---

## 关键类型定义

### ProblemType
```python
class ProblemType(str, Enum):
    KNOWLEDGE = "knowledge_bottleneck"  # 专业知识瓶颈
    TOOL = "tool_bottleneck"            # 工具使用复杂度
```

### TaskStatus
```python
class TaskStatus(str, Enum):
    UNSOLVED = "unsolved"
    SOLVED = "solved"
    ABANDONED = "abandoned"
```

### JudgerFeedback
```python
@dataclass
class JudgerFeedback:
    passed: bool  # 注意: Python 属性名是 passed，但 JSON key 是 "pass"
    score: float
    blocking_issues: list[BlockingIssue]
    non_blocking_concerns: list[NonBlockingConcern]
    positive_signals: list[str]
    confidence: float
    recommendation: str  # proceed_to_real_test | keep_improving | abandon
```

---

## 配置文件

### Config 默认值 (`core/types.py`)
```python
max_real_test_failures: int = 4
max_quick_proposer_iterations: int = 3
max_research_triggers_same_judger: int = 2
max_task_experience_entries: int = 2
```

---

## 已发现并修复的 Bug

### 1. Python 关键字冲突 (已修复)
- **问题**: `JudgerFeedback.pass` 使用 Python 关键字 `pass` 作为属性名
- **影响**: 语法错误，`judger_result.pass` 无法访问
- **修复**: 重命名为 `passed`，JSON key 保持 `"pass"` 兼容

### 2. judger_research_triggers 错误重置 (已修复)
- **问题**: real_test 失败时重置为 0，导致 Reflector 永远无法触发
- **影响**: 同一 skill 卡在 judger 时无法自省
- **修复**: 移除该重置，只在 judger pass 或 Reflector 后重置

### 3. Criteria 未传递 (已修复)
- **问题**: `build_judger_criteria()` 返回的 criteria 从未传给 `evaluate()`
- **影响**: stricter criteria 不生效
- **修复**: `evaluate()` 增加 `criteria` 参数，实现传递

### 4. Criteria 格式不匹配 (已修复)
- **问题**: Reflector 后传入 `judger_feedback_history` 而非 `failure_record`
- **影响**: `build_judger_criteria` 中 `type == "real_test_failed_after_judger_pass"` 永远不匹配
- **修复**: 传入空列表（looser standards）或正确格式

### 5. 重复类型定义 (已修复)
- **问题**: `JudgerFeedback` 在 `core/types.py` 和 `judge/feedback.py` 都有定义
- **影响**: 不一致，`feedback.py` 版本有 `BlockingIssue` 类型
- **修复**: 删除 `core/types.py` 中的定义，统一使用 `judge/feedback.py`

### 6. TODO 占位符 (已修复)
- **问题**: 多处使用 `"TODO"` 字符串作为 domain/modeling
- **影响**: Memory 匹配失效，经验无法积累
- **修复**: 使用 `context.domain`, `context.problem_modeling` 真实值

---

## 当前 TODO (未实现)

暂无。所有 TODO 已实现。

---

## 设计决策记录

### Decision 1: Judger 严格度
- **选项**: Lenient (BE LENIENT) vs Strict (Be strict but fair)
- **选择**: Strict but fair
- **理由**: 避免假阳性浪费 real test 资源
- **参考**: SkillsBench 发现自生成技能 -1.3pp，说明不严格筛选会损害性能

### Decision 2: Reflector 触发阈值
- **选项**: 3 次 vs 2 次
- **选择**: 2 次
- **理由**: 更激进自省，避免在错误方向上浪费过多迭代
- **条件**: 连续 2 次 Research 触发且无 judger pass

### Decision 3: Memory 查询实现
- **实现**: 在 `_research_new_skill` 中调用:
  - `_get_previously_tried_methods()`: 查 trace 历史
  - `_get_ineffective_methods()`: 查 meta memory 无效方法
  - `_get_effective_methods()`: 查 meta memory 有效方法
- **理由**: Research 时需要上下文，避免重复尝试

### Decision 4: Transferability 估算
```python
if problem_type == KNOWLEDGE: return "high"
if domain in ("code_generation", "tool_use"): return "medium"
if "specific" in modeling: return "low"
return "medium"
```

---

## 与其他系统对比

| 系统 | 输入 | Skill 来源 | 验证器 |
|------|------|-----------|--------|
| AutoSOTA | Paper | Generated | 实验评估 |
| AI Scientist | 研究方向 | Generated | Paper review |
| EvoSkills | Task | Generated | Surrogate Verifier |
| **MasterSkill** | Benchmark | Research Team + QuickProposer | Judger (result-based) |

---

## 技术栈

- **图引擎**: langgraph, langchain
- **向量存储**: chromadb
- **工具**: arxiv, pymupdf
- **网络**: httpx, networkx
- **配置**: pyyaml

---

## 使用方式

### 运行 Benchmark
```python
from MasterSkill.runner import BenchmarkRunner
from MasterSkill.core.config import load_config

config = load_config(skillsbench_root="/path/to/skillsbench")
runner = BenchmarkRunner(config)
results = runner.run_benchmark()
```

### 配置 API Key
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

---

## Git 信息

- **Remote**: https://github.com/Yuchong-W/EvoMaster_Skill
- **Branch**: main (local: master)
- **提交者**: Yuchong-W <yuchong-23@mails.tsinghua.edu.cn>
