# DRskill — Deep Research + Skill Generator

DRskill 是一个自动化工具链，为 SkillsBench 评测任务生成高质量的 AI Agent Skills。它通过 **Perplexity Deep Research** 进行深度技术检索，再由 **Claude** 将检索结果转化为结构化的 `SKILL.md` 文件，最终注入到任务的 Docker 运行环境中。

---

## 工作原理

```
任务上下文  ──►  Perplexity Deep Research  ──►  Claude Skill Gen  ──►  SKILL.md + Dockerfile
 (instruction.md,       (技术检索报告)            (结构化 skill)         (写入 environment/)
  task.toml, etc.)
```

1. **收集上下文** — 读取任务的 `instruction.md`、`task.toml`、`Dockerfile`、`test_outputs.py` 及环境中的小型文本文件（< 50KB）
2. **Deep Research** — 调用 Perplexity 模型，针对任务所需的库/API/参数/反模式做系统化检索，生成中文技术报告
3. **Skill 生成** — 调用 Claude，基于上下文 + DR 报告输出 1-5 个 skill（JSON 格式），每个 skill 包含 `SKILL.md` 和可选辅助脚本
4. **写入 & 修补** — 将 skill 写入 `environment/skills/`，在 `Dockerfile` 末尾追加 `COPY skills` 指令

---

## 适配指南

> 当前代码高度定制化，以下列出所有需要根据自身环境修改的地方。

### 1. 环境变量

| 变量 | 当前用途 | 你需要做的 |
|------|----------|-----------|
| `OPENAI_API_KEY` | 通过 dmxapi 代理同时访问 Perplexity 和 Claude | 换成你自己的 API key。如果你直接用官方 API，key 格式不同 |
| `OPENAI_BASE_URL` | 当前指向 `https://www.dmxapi.cn`（第三方代理） | 换成你的 API endpoint。如果用官方 Perplexity + Anthropic，需要分别调用两个不同的 base URL，**脚本目前不支持这种双 endpoint 场景**，需要自行拆分 |

### 2. `dr_skill_pipeline.py` 中的硬编码常量（第 29-37 行）

```python
# ── 必须根据你的 API 提供商修改 ──
DR_MODEL = "perplexity-deep-research-ssvip"   # Perplexity 模型名，dmxapi 代理专用名称
SKILL_MODEL = "claude-opus-4-6"               # Claude 模型名，dmxapi 代理专用名称

# ── 可按需调整 ──
DR_TIMEOUT = 600    # Deep Research 超时（秒），Perplexity 搜索慢，不建议调低
SKILL_TIMEOUT = 300 # Claude 生成超时（秒）
MAX_RETRIES = 3     # API 失败自动重试次数
RETRY_DELAY = 30    # 重试间隔（秒）
```

**关键问题**: `DR_MODEL` 和 `SKILL_MODEL` 的名称取决于你用的 API 代理/提供商。例如：
- 如果你用 OpenRouter：模型名可能是 `perplexity/sonar-deep-research` 和 `anthropic/claude-opus-4-6`
- 如果你用官方 API：Perplexity 模型名是 `sonar-deep-research`，但 Anthropic 的 API 格式完全不同（非 OpenAI 兼容），**脚本的 chat completions 调用方式需要改写**

### 3. API 调用格式（第 313-329 行 / 第 402-422 行）

脚本假设 **所有 API 都走 OpenAI 兼容格式**：
- Deep Research 用 `POST /v1/responses`（Responses API 格式）
- Skill 生成用 `POST /v1/chat/completions`（Chat Completions 格式）

如果你的 API 提供商不支持这两种 endpoint，或者你需要分别调用 Perplexity 官方 API 和 Anthropic 官方 API，需要：
- 为两个阶段分别配置 `api_key` 和 `base_url`
- 修改 Anthropic 调用部分为 Messages API 格式

### 4. Dockerfile COPY 路径（第 40-49 行）

```python
SKILL_COPY_LINES = """\
# Copy skills to all agent paths
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
"""
```

这些路径覆盖了多种 AI Agent 的 skills 读取目录。如果你只用其中一种 agent，可以精简；如果你的 agent 有不同的 skills 路径，需要修改。

### 5. SKILL.md 中的硬编码路径（Claude Code Skill 定义）

`SKILL.md` 是供 Claude Code 的 `/DRskill` slash command 使用的技能定义文件，其中所有路径都是硬编码的：

| 行号 | 硬编码内容 | 需要改为 |
|------|-----------|---------|
| 16 | `/home/tanhe/yuchong/skillsbench/` | 你的 SkillsBench 仓库路径 |
| 22 | `/home/tanhe/yuchong/DRskill/scripts/dr_skill_pipeline.py` | 你的脚本路径 |
| 35-65 | 所有命令示例中的绝对路径 | 你的对应路径 |

如果你不使用 Claude Code 的 slash command 功能，可以忽略 `SKILL.md`，直接用命令行即可。

### 6. 任务目录结构约定

脚本假设每个任务目录遵循 SkillsBench 的固定结构：

```
<task-name>/
├── instruction.md          # 必须存在，否则跳过
├── task.toml
├── tests/
│   └── test_outputs.py
└── environment/
    ├── Dockerfile
    └── skills/             # 脚本写入位置
```

如果你的任务目录结构不同（比如没有 `environment/` 子目录，或测试文件不叫 `test_outputs.py`），需要修改 `collect_task_context()` 函数（第 142-199 行）。

### 7. Deep Research Prompt 语言

`build_dr_prompt()` 函数（第 233-310 行）中的 user prompt 是**中文**的。如果你的任务是英文环境或需要英文报告，需要将 prompt 改为英文。system prompt 已经是英文。

---

## 快速适配清单

如果你想最快速地跑起来，按优先级处理：

- [ ] 设置 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`
- [ ] 修改 `DR_MODEL` 和 `SKILL_MODEL` 为你的 API 提供商支持的模型名
- [ ] 确认你的 API 同时支持 `/v1/responses` 和 `/v1/chat/completions` endpoint
- [ ] 确认任务目录结构符合约定（有 `instruction.md`）
- [ ] （可选）修改 `SKILL_COPY_LINES` 中的 agent 路径
- [ ] （可选）修改 `SKILL.md` 中的路径以启用 Claude Code slash command
- [ ] （可选）将 DR prompt 改为英文

---

## 使用方式

### 全量生成

```bash
# Step 1: 初始化工作目录（从 tasks-no-skills 复制到 tasks_to_test）
python3 dr_skill_pipeline.py --init /path/to/tasks-no-skills

# Step 2: 批量生成 skills
python3 dr_skill_pipeline.py --batch /path/to/tasks_to_test
```

### 单任务生成

```bash
python3 dr_skill_pipeline.py /path/to/tasks_to_test/<task-name>

# 或输出到另一目录
python3 dr_skill_pipeline.py /path/to/tasks-no-skills/<task-name> \
  --output-dir /path/to/tasks_to_test
```

### 断点续跑

```bash
python3 dr_skill_pipeline.py --batch /path/to/tasks_to_test \
  --resume-from <task-name>
```

### 不保存 DR 报告

```bash
python3 dr_skill_pipeline.py /path/to/task --no-report
```

## 命令行参数

```
位置参数:
  task_dir                单个任务目录路径

选项:
  --batch TASKS_ROOT      批量处理：指定包含多个任务的父目录
  --init SRC              初始化：将 tasks-no-skills 复制到同级 tasks_to_test
  --output-dir DIR        输出到指定目录（单任务模式）
  --resume-from TASK      从指定任务名开始（批量模式）
  --base-url URL          覆盖 OPENAI_BASE_URL（默认从环境变量读取）
  --no-report             不保存 Deep Research 报告
```

## 输出结构

```
tasks_to_test/<task-name>/
├── instruction.md
├── task.toml
├── tests/
│   └── test_outputs.py
└── environment/
    ├── Dockerfile                  # ← 自动追加 COPY skills
    ├── dr_report/
    │   └── <task-name>_report.md   # Deep Research 报告（除非 --no-report）
    └── skills/
        ├── <skill-1>/
        │   ├── SKILL.md
        │   └── scripts/            # 可选
        └── <skill-2>/
            └── SKILL.md
```

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `OPENAI_API_KEY not set` | 环境变量缺失 | `export OPENAI_API_KEY=...` |
| DR 超时 | Perplexity 搜索慢 / 网络问题 | 自动重试 3 次；可调大 `DR_TIMEOUT` |
| `Failed to parse skills JSON` | Claude 输出格式异常 | 自动重试；持续失败检查模型可用性 |
| Dockerfile 未修补 | 已有 COPY skills 行 | 正常，不会重复添加 |
| 批量中断 | API 限流 / 网络中断 | `--resume-from <下一个任务名>` |

