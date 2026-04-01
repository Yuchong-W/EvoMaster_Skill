---
name: DRskill
description: |
  为 SkillsBench 任务生成 Deep Research 驱动的 skills。
  当用户说 /DRskill 时触发。支持：全量生成、单任务生成、断点续跑。
  流程：复制 tasks-no-skills → 调用 Perplexity Deep Research → 调用 Claude 生成 skills → 写入文件 → 修改 Dockerfile。
---

# DRskill — Deep Research + Skill Generator

为 SkillsBench 任务从零生成高质量 skills，无需参考 ground-truth skills。

## 前置条件

- 环境变量 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 已设置
- SkillsBench 仓库在 `/home/tanhe/yuchong/skillsbench/`
- Python 3.10+

## 核心脚本

```
/home/tanhe/yuchong/DRskill/scripts/dr_skill_pipeline.py
```

## 使用方式

用户可能以以下方式调用：

### 1. 全量流程（推荐）

当用户说 "运行全部" 或 "生成所有任务的 skills" 时，按顺序执行：

**Step 1: 初始化 tasks_to_test**
```bash
python3 /home/tanhe/yuchong/DRskill/scripts/dr_skill_pipeline.py \
  --init /home/tanhe/yuchong/skillsbench/tasks-no-skills \
  --output-dir /home/tanhe/yuchong/skillsbench/tasks_to_test
```
这会复制 tasks-no-skills 到 tasks_to_test，并清空已有 skills 内容。

**Step 2: 批量生成 skills**
```bash
python3 /home/tanhe/yuchong/DRskill/scripts/dr_skill_pipeline.py \
  --batch /home/tanhe/yuchong/skillsbench/tasks_to_test
```
对每个任务依次执行：收集上下文 → Perplexity Deep Research → Claude 生成 skills → 写入文件 → 修改 Dockerfile。

**Step 3: 验证**
```bash
harbor run -p /home/tanhe/yuchong/skillsbench/tasks_to_test -a claude-code -m 'anthropic/claude-opus-4-5' -k 5
```

### 2. 单任务生成

```bash
python3 /home/tanhe/yuchong/DRskill/scripts/dr_skill_pipeline.py \
  /home/tanhe/yuchong/skillsbench/tasks_to_test/<task-name>
```

### 3. 断点续跑

如果批量运行中断，从指定任务恢复：
```bash
python3 /home/tanhe/yuchong/DRskill/scripts/dr_skill_pipeline.py \
  --batch /home/tanhe/yuchong/skillsbench/tasks_to_test \
  --resume-from <task-name>
```

## 执行指南

当用户调用 /DRskill 时：

1. **确认环境变量**：检查 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 是否已设置
2. **询问范围**：用户想处理全部任务还是指定任务？
3. **检查 tasks_to_test 是否已存在**：如果已存在且用户想重新开始，先删除再重建；如果想继续，使用 `--resume-from`
4. **执行对应命令**：使用上面的命令模板
5. **监控进度**：脚本会输出每个任务的处理状态，包括成功/失败/跳过
6. **报告结果**：完成后汇总成功率，提示用户运行 harbor 验证

## 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| DR 模型 | `perplexity-deep-research-ssvip` | Deep Research 搜索 |
| Skill 生成模型 | `claude-opus-4-6` | 生成 SKILL.md |
| DR 超时 | 600s | Perplexity 搜索较慢 |
| Skill 超时 | 300s | Claude 生成 |
| 重试次数 | 3 | API 失败自动重试 |
| 重试间隔 | 30s | 指数退避 |

## 输出结构

每个任务处理后的目录结构：
```
tasks_to_test/<task-name>/
├── environment/
│   ├── Dockerfile          # 已追加 COPY skills 行
│   └── skills/
│       ├── <skill-1>/
│       │   ├── SKILL.md
│       │   └── scripts/    # 可选
│       └── <skill-2>/
│           └── SKILL.md
├── instruction.md
├── task.toml
└── tests/
```

Deep Research 报告保存在：
```
tasks_to_test/<task-name>/dr_report.md
```
