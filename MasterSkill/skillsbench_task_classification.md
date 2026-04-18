# SkillsBench 任务分类（按你要求的三类）

来源：`SkillsBench.pdf` 的逐任务热力图结果，主要使用 Figure 11（with curated Skills）和 Figure 12（without Skills），对应 PDF 第 21-22 页；任务名顺序来自同页图中行标签。

## 本地复现说明（2026-04-17）

这份文档仍然是在记录**论文里的历史 benchmark 结果**，不是当前本地 harness 的最新通过情况。

需要特别区分两件事：

- 这里的 `With Skills = 0%` 表示论文评测设置下的历史结论
- 它**不自动等于**“今天在修复后的本地执行链路里绝对跑不过”

截至 2026-04-17，本地 `MasterSkill` 已经出现两个重要反例：

- `enterprise-information-search`
  - 论文分类仍然是 `With Skills = 0%`
  - 但在当前本地 harness 下，official real test 已可通过
  - 当前通过主要体现的是执行链路 fidelity / timeout / verifier bootstrap 修复，而不是已有 skill 已经被证明确认有效
- `financial-modeling-qa`
  - 论文分类仍然是 `With Skills = 0%`
  - 但在当前本地 harness 下，official real test 已可通过
  - 并且已经蒸馏出了一个通过 real test 的更紧凑 task-local skill
- `pddl-tpp-planning`
  - 论文分类仍然是 `With Skills = 0%`
  - 但在当前本地 harness 下，official real test 已可通过
  - 并且已经蒸馏出了通过 real test 的 post-pass skill

因此：

- 这份分类文档继续保留论文语境下的历史标签
- 当前本地研发要额外看 run records，而不是只看这里的静态分类

## 我采用的分类规则

论文本身没有给出“完全模型自主可解决 / 不稳定 / 有人类 skill 也解决不了”这三个官方标签，所以这里用一套可复现规则来分：

1. **完全模型自主可解决**
   - `No Skills` 平均通过率 >= 70%
   - 且 `With Skills - No Skills` 的绝对变化 <= 10pp
   - 含义：不用人工写的 skill，模型本身就已经基本能做出来，而且加 skill 也不会明显改变结果。

2. **有人类 skill 也解决不了**
   - `With Skills` 在 7 个 agent-model 配置上的平均通过率 = 0%
   - 含义：在这篇论文的 benchmark 设置里，即使给了 human-curated Skills，所有配置仍然没解出来。
   - 注意：这表示“在该评测设置下仍未解出”，不等于“理论上绝对无解”。

3. **不稳定**
   - 除了上面两类以外的全部任务。
   - 这类任务通常表现为：对模型规模敏感、对 harness 敏感、对有没有 skill 敏感，或者 skill 有时帮忙、有时反而添乱。

## 一个需要提前说明的点

附录 I.8 的文字说明与图 11/12 的逐任务热力图并不完全一致。比如正文明确举了 `taxonomy-tree-merge` 的负增益例子（-39.3pp），这意味着它在 `No Skills` 下并不是 0%。因此我这里**优先按图 11/12 的直接任务级结果**做分类，而不是直接照抄附录 I.8 的那段文字。

## 分类总览

- 完全模型自主可解决：7 个
- 不稳定：60 个
- 有人类 skill 也解决不了：17 个

---

## 1. 完全模型自主可解决（7 个）

| 任务 | No Skills平均通过率 | With Skills平均通过率 | Δ |
|---|---:|---:|---:|
| citation-check | 100.0% | 96.8% | -2.9pp |
| spring-boot-jakarta-migration | 96.8% | 94.0% | -2.8pp |
| powerlifting-coef-calc | 88.3% | 94.0% | +5.7pp |
| pdf-excel-diff | 82.6% | 76.9% | -5.7pp |
| dialogue-parser | 78.9% | 86.0% | +7.1pp |
| lean4-proof | 76.9% | 74.0% | -2.9pp |
| econ-detrending-correlation | 74.0% | 82.6% | +8.6pp |

---

## 2. 不稳定（60 个）

| 任务 | No Skills平均通过率 | With Skills平均通过率 | Δ |
|---|---:|---:|---:|
| mario-coin-counting | 2.9% | 88.3% | +85.4pp |
| sales-pivot-analysis | 0.0% | 85.4% | +85.4pp |
| flood-risk-analysis | 2.9% | 79.8% | +76.9pp |
| sec-financial-report | 0.0% | 74.1% | +74.1pp |
| protein-expression-analysis | 17.1% | 91.1% | +74.0pp |
| offer-letter-generator | 14.2% | 85.4% | +71.2pp |
| earthquake-plate-calculation | 11.4% | 82.6% | +71.2pp |
| manufacturing-fjsp-optimization | 0.0% | 68.3% | +68.3pp |
| dapt-intrusion-detection | 25.6% | 88.3% | +62.6pp |
| software-dependency-audit | 8.6% | 68.3% | +59.8pp |
| simpo-code-reproduction | 0.0% | 57.0% | +57.0pp |
| lake-warming-attribution | 14.2% | 68.4% | +54.1pp |
| manufacturing-equipment-maintena | 0.0% | 48.4% | +48.4pp |
| exceltable-in-ppt | 19.9% | 59.8% | +39.9pp |
| data-to-d3 | 11.4% | 48.4% | +37.0pp |
| energy-market-pricing | 31.3% | 68.4% | +37.0pp |
| mars-clouds-clustering | 57.0% | 94.0% | +37.0pp |
| glm-lake-mendota | 54.1% | 91.1% | +37.0pp |
| weighted-gdp-calc | 0.0% | 34.2% | +34.2pp |
| pptx-reference-formatting | 31.4% | 65.5% | +34.1pp |
| 3d-scan-calc | 57.0% | 88.3% | +31.3pp |
| lab-unit-harmonization | 51.1% | 80.7% | +29.6pp |
| grid-dispatch-operator | 34.2% | 62.6% | +28.5pp |
| fix-druid-loophole-cve | 34.2% | 62.6% | +28.4pp |
| threejs-structure-parser | 14.2% | 34.2% | +20.0pp |
| adaptive-cruise-control | 20.0% | 37.0% | +17.1pp |
| civ6-adjacency-optimizer | 5.5% | 20.3% | +14.8pp |
| court-form-filling | 28.5% | 42.7% | +14.2pp |
| hvac-control | 48.4% | 62.7% | +14.2pp |
| fix-erlang-ssh-cve | 34.2% | 48.4% | +14.2pp |
| dynamic-object-aware-egomotion | 0.0% | 11.4% | +11.4pp |
| threejs-to-obj | 54.1% | 65.5% | +11.4pp |
| invoice-fraud-detection | 20.0% | 31.3% | +11.4pp |
| manufacturing-codebook-normaliza | 2.9% | 11.4% | +8.6pp |
| travel-planning | 39.9% | 48.4% | +8.6pp |
| syzkaller-ppdev-syzlang | 45.6% | 54.1% | +8.6pp |
| jax-computing-basics | 42.7% | 51.3% | +8.5pp |
| python-scala-translation | 14.3% | 22.8% | +8.5pp |
| setup-fuzzing-py | 11.7% | 19.3% | +7.6pp |
| azure-bgp-oscillation-route-leak | 0.0% | 5.7% | +5.7pp |
| fix-build-agentops | 2.9% | 8.5% | +5.7pp |
| pedestrian-traffic-counting | 7.0% | 11.0% | +4.0pp |
| r2r-mpc-control | 17.1% | 20.0% | +2.9pp |
| virtualhome-agent-planning | 14.2% | 17.1% | +2.9pp |
| video-tutorial-indexer | 34.2% | 37.0% | +2.8pp |
| paper-anonymizer | 11.4% | 14.2% | +2.8pp |
| fix-build-google-auto | 8.5% | 8.6% | +0.0pp |
| flink-query | 11.4% | 11.4% | +0.0pp |
| suricata-custom-exfil | 5.7% | 5.7% | +0.0pp |
| jpg-ocr-stat | 2.9% | 2.9% | +0.0pp |
| multilingual-video-dubbing | 28.5% | 28.5% | +0.0pp |
| find-topk-similiar-chemicals | 2.9% | 1.4% | -1.5pp |
| earthquake-phase-association | 42.7% | 39.9% | -2.8pp |
| parallel-tfidf-search | 68.3% | 65.5% | -2.8pp |
| pg-essay-to-audiobook | 51.3% | 48.4% | -2.8pp |
| crystallographic-wyckoff-positio | 59.5% | 55.0% | -4.5pp |
| organize-messy-files | 25.7% | 17.1% | -8.5pp |
| exoplanet-detection-period | 31.3% | 20.0% | -11.4pp |
| trend-anomaly-causal-inference | 75.4% | 62.6% | -12.8pp |
| energy-ac-optimal-power-flow | 22.8% | 8.6% | -14.2pp |

---

## 3. 有人类 skill 也解决不了（17 个）

| 任务 | No Skills平均通过率 | With Skills平均通过率 | Δ |
|---|---:|---:|---:|
| taxonomy-tree-merge | 39.1% | 0.0% | -39.1pp |
| video-filler-word-remover | 11.4% | 0.0% | -11.4pp |
| financial-modeling-qa | 5.7% | 0.0% | -5.7pp |
| enterprise-information-search | 0.0% | 0.0% | +0.0pp |
| gh-repo-analytics | 0.0% | 0.0% | +0.0pp |
| speaker-diarization-subtitles | 0.0% | 0.0% | +0.0pp |
| pddl-tpp-planning | 0.0% | 0.0% | +0.0pp |
| gravitational-wave-detection | 0.0% | 0.0% | +0.0pp |
| shock-analysis-supply | 0.0% | 0.0% | +0.0pp |
| shock-analysis-demand | 0.0% | 0.0% | +0.0pp |
| seismic-phase-picking | 0.0% | 0.0% | +0.0pp |
| latex-formula-extraction | 0.0% | 0.0% | +0.0pp |
| scheduling-email-assistant | 0.0% | 0.0% | +0.0pp |
| reserves-at-risk-calc | 0.0% | 0.0% | +0.0pp |
| react-performance-debugging | 0.0% | 0.0% | +0.0pp |
| quantum-numerical-simulation | 0.0% | 0.0% | +0.0pp |
| xlsx-recover-data | 0.0% | 0.0% | +0.0pp |

## 备注

- `scheduling-email-assistant` 在附录的失败分析里带有明显环境/鉴权问题，零通过率不一定完全是“能力不足”，但在 benchmark 的当前设置下结果确实是 `With Skills = 0%`。
- `react-performance-debugging` 还伴随 verifier timeout 问题；这里仍按最终任务级结果分类。
- 图中的少数任务名在版面上被截断了，我保留了图里的原写法，以便与你看到的 PDF 一一对应。
