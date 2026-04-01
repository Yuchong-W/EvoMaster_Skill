# DRskill 验证实验记录

## 实验配置

| 参数 | 第一轮 (终止) | 第二轮 |
|------|-------------|--------|
| 任务数 | 86 | 86 |
| 每任务运行次数 (-k) | 5 | 2 (分两批: k=2 + k=1) |
| 超时倍率 (--timeout-multiplier) | 3 | 5 |
| 并发数 (-n) | 8 | 4 |
| 模型 (-m) | claude-opus-4-6 | claude-opus-4-6 |
| Job 目录 (Run 1) | jobs/2026-03-25__12-49-54 | jobs/2026-03-25__20-34-48 |
| Job 目录 (Run 2) | — | jobs/2026-03-26__11-11-46 |

### 第一轮经验
- 8 路并发触发 dmxapi API 限流，agent 陷入 api_retry 指数退避循环
- 43% 的 trials 因 AgentTimeoutError 失败（非真正计算超时）
- 降低并发到 4 路 + 增大超时倍率以缓解

### 第二轮说明
- 原计划 `-k 2` 一次跑完，但 harbor 在完成第一轮 86 trials 后中断
- 补跑第二轮：`-k 1`，Job 目录 `jobs/2026-03-26__11-11-46`
- 两个 job 的结果合并统计

---

## 第二轮合并结果

| # | 任务名 | Run 1 | Run 2 | 通过率 |
|---|--------|-------|-------|--------|
| 1 | 3d-scan-calc | PASS | PASS | 2/2 |
| 2 | adaptive-cruise-control | PASS | FAIL | 1/2 |
| 3 | azure-bgp-oscillation-route-leak | PASS | FAIL | 1/2 |
| 4 | citation-check | PASS | PASS | 2/2 |
| 5 | civ6-adjacency-optimizer | FAIL | FAIL | 0/2 |
| 6 | court-form-filling | ERROR | PASS | 1/1 |
| 7 | crystallographic-wyckoff-position-analysis | PASS | PASS | 2/2 |
| 8 | dapt-intrusion-detection | FAIL | FAIL | 0/2 |
| 9 | data-to-d3 | PASS | FAIL | 1/2 |
| 10 | dialogue-parser | PASS | PASS | 2/2 |
| 11 | dynamic-object-aware-egomotion | FAIL | FAIL | 0/2 |
| 12 | earthquake-phase-association | PASS | PASS | 2/2 |
| 13 | earthquake-plate-calculation | FAIL | FAIL | 0/2 |
| 14 | econ-detrending-correlation | PASS | PASS | 2/2 |
| 15 | energy-ac-optimal-power-flow | PASS | PASS | 2/2 |
| 16 | energy-market-pricing | PASS | PASS | 2/2 |
| 17 | enterprise-information-search | FAIL | FAIL | 0/2 |
| 18 | exceltable-in-ppt | FAIL | FAIL | 0/2 |
| 19 | exoplanet-detection-period | FAIL | FAIL | 0/2 |
| 20 | financial-modeling-qa | FAIL | FAIL | 0/2 |
| 21 | find-topk-similiar-chemicals | FAIL | FAIL | 0/2 |
| 22 | fix-build-agentops | FAIL | FAIL | 0/2 |
| 23 | fix-build-google-auto | PASS | PASS | 2/2 |
| 24 | fix-druid-loophole-cve | PASS | PASS | 2/2 |
| 25 | fix-erlang-ssh-cve | PASS | PASS | 2/2 |
| 26 | fix-visual-stability | PASS | PASS | 2/2 |
| 27 | flink-query | FAIL | FAIL | 0/2 |
| 28 | flood-risk-analysis | FAIL | FAIL | 0/2 |
| 29 | gh-repo-analytics | FAIL | FAIL | 0/2 |
| 30 | glm-lake-mendota | PASS | PASS | 2/2 |
| 31 | gravitational-wave-detection | PASS | PASS | 2/2 |
| 32 | grid-dispatch-operator | PASS | PASS | 2/2 |
| 33 | hvac-control | PASS | FAIL | 1/2 |
| 34 | invoice-fraud-detection | PASS | FAIL | 1/2 |
| 35 | jax-computing-basics | PASS | PASS | 2/2 |
| 36 | jpg-ocr-stat | FAIL | FAIL | 0/2 |
| 37 | lab-unit-harmonization | FAIL | FAIL | 0/2 |
| 38 | lake-warming-attribution | PASS | PASS | 2/2 |
| 39 | latex-formula-extraction | FAIL | FAIL | 0/2 |
| 40 | lean4-proof | FAIL | PASS | 1/2 |
| 41 | manufacturing-codebook-normalization | ERROR | ERROR | N/A |
| 42 | manufacturing-equipment-maintenance | ERROR | ERROR | N/A |
| 43 | manufacturing-fjsp-optimization | ERROR | ERROR | N/A |
| 44 | mario-coin-counting | FAIL | FAIL | 0/2 |
| 45 | mars-clouds-clustering | PASS | PASS | 2/2 |
| 46 | mhc-layer-impl | ERROR | ERROR | N/A |
| 47 | multilingual-video-dubbing | ERROR | ERROR | N/A |
| 48 | offer-letter-generator | PASS | PASS | 2/2 |
| 49 | organize-messy-files | FAIL | FAIL | 0/2 |
| 50 | paper-anonymizer | FAIL | FAIL | 0/2 |
| 51 | parallel-tfidf-search | PASS | FAIL | 1/2 |
| 52 | pddl-tpp-planning | PASS | PASS | 2/2 |
| 53 | pdf-excel-diff | PASS | FAIL | 1/2 |
| 54 | pedestrian-traffic-counting | FAIL | FAIL | 0/2 |
| 55 | pg-essay-to-audiobook | FAIL | FAIL | 0/2 |
| 56 | powerlifting-coef-calc | PASS | PASS | 2/2 |
| 57 | pptx-reference-formatting | PASS | PASS | 2/2 |
| 58 | protein-expression-analysis | PASS | PASS | 2/2 |
| 59 | python-scala-translation | PASS | PASS | 2/2 |
| 60 | quantum-numerical-simulation | FAIL | FAIL | 0/2 |
| 61 | r2r-mpc-control | PASS | FAIL | 1/2 |
| 62 | react-performance-debugging | FAIL | FAIL | 0/2 |
| 63 | reserves-at-risk-calc | FAIL | FAIL | 0/2 |
| 64 | sales-pivot-analysis | PASS | FAIL | 1/2 |
| 65 | scheduling-email-assistant | ERROR | ERROR | N/A |
| 66 | sec-financial-report | FAIL | FAIL | 0/2 |
| 67 | seismic-phase-picking | FAIL | FAIL | 0/2 |
| 68 | setup-fuzzing-py | PASS | FAIL | 1/2 |
| 69 | shock-analysis-demand | FAIL | FAIL | 0/2 |
| 70 | shock-analysis-supply | ERROR | FAIL | 0/1 |
| 71 | simpo-code-reproduction | PASS | PASS | 2/2 |
| 72 | software-dependency-audit | PASS | PASS | 2/2 |
| 73 | speaker-diarization-subtitles | ERROR | ERROR | N/A |
| 74 | spring-boot-jakarta-migration | ERROR | ERROR | N/A |
| 75 | suricata-custom-exfil | ERROR | ERROR | N/A |
| 76 | syzkaller-ppdev-syzlang | PASS | PASS | 2/2 |
| 77 | taxonomy-tree-merge | PASS | PASS | 2/2 |
| 78 | threejs-structure-parser | FAIL | FAIL | 0/2 |
| 79 | threejs-to-obj | PASS | PASS | 2/2 |
| 80 | travel-planning | PASS | PASS | 2/2 |
| 81 | trend-anomaly-causal-inference | PASS | PASS | 2/2 |
| 82 | video-filler-word-remover | FAIL | FAIL | 0/2 |
| 83 | video-tutorial-indexer | PASS | PASS | 2/2 |
| 84 | virtualhome-agent-planning | ERROR | PASS | 1/1 |
| 85 | weighted-gdp-calc | FAIL | FAIL | 0/2 |
| 86 | xlsx-recover-data | FAIL | FAIL | 0/2 |

---

## 汇总统计

### 单轮统计
| 指标 | Run 1 | Run 2 |
|------|-------|-------|
| PASS | 42 | 35 |
| FAIL | 33 | 42 |
| ERROR | 11 | 9 |
| Pass rate (all) | 48.8% | 40.7% |
| Pass rate (excl errors) | 56.0% | 45.5% |

### 合并统计（排除 ERROR 的 trials）
- **总有效 trials: 151** 
- **PASS: 77 / 151 = 50.99%**
- **Both PASS (稳定通过): 32 tasks**
- **Both FAIL (稳定失败): 32 tasks**
- **Split (不稳定, 1 pass 1 fail): 11 tasks**
- **Both ERROR (超时): 9 tasks** (manufacturing-codebook-normalization, manufacturing-equipment-maintenance, manufacturing-fjsp-optimization, mhc-layer-impl, multilingual-video-dubbing, scheduling-email-assistant, speaker-diarization-subtitles, spring-boot-jakarta-migration, suricata-custom-exfil)

### 按稳定性分类
| 类别 | 数量 | 占比 | 任务列表 |
|------|------|------|----------|
| 稳定通过 (2/2) | 32 | 37.2% | 3d-scan-calc, citation-check, crystallographic-wyckoff-position-analysis, dialogue-parser, earthquake-phase-association, econ-detrending-correlation, energy-ac-optimal-power-flow, energy-market-pricing, fix-build-google-auto, fix-druid-loophole-cve, fix-erlang-ssh-cve, fix-visual-stability, glm-lake-mendota, gravitational-wave-detection, grid-dispatch-operator, jax-computing-basics, lake-warming-attribution, mars-clouds-clustering, offer-letter-generator, pddl-tpp-planning, powerlifting-coef-calc, pptx-reference-formatting, protein-expression-analysis, python-scala-translation, simpo-code-reproduction, software-dependency-audit, syzkaller-ppdev-syzlang, taxonomy-tree-merge, threejs-to-obj, travel-planning, trend-anomaly-causal-inference, video-tutorial-indexer |
| 不稳定 (1/2) | 11 | 12.8% | adaptive-cruise-control, azure-bgp-oscillation-route-leak, data-to-d3, hvac-control, invoice-fraud-detection, lean4-proof, parallel-tfidf-search, pdf-excel-diff, r2r-mpc-control, sales-pivot-analysis, setup-fuzzing-py |
| 稳定失败 (0/2) | 31 | 29.1% | civ6-adjacency-optimizer, dapt-intrusion-detection, dynamic-object-aware-egomotion, earthquake-plate-calculation, enterprise-information-search, exceltable-in-ppt, exoplanet-detection-period, financial-modeling-qa, find-topk-similiar-chemicals, fix-build-agentops, flink-query, flood-risk-analysis, gh-repo-analytics, jpg-ocr-stat, lab-unit-harmonization, latex-formula-extraction, mario-coin-counting, organize-messy-files, paper-anonymizer, pedestrian-traffic-counting, pg-essay-to-audiobook, quantum-numerical-simulation, react-performance-debugging, reserves-at-risk-calc, sec-financial-report, seismic-phase-picking, shock-analysis-demand, threejs-structure-parser, video-filler-word-remover, weighted-gdp-calc, xlsx-recover-data |
| ERROR (超时) | 9 | 10.5% | manufacturing-codebook-normalization, manufacturing-equipment-maintenance, manufacturing-fjsp-optimization, mhc-layer-impl, multilingual-video-dubbing, scheduling-email-assistant, speaker-diarization-subtitles, spring-boot-jakarta-migration, suricata-custom-exfil |
| 单次有效 | 3 | 3.5% | court-form-filling (1/1 PASS), shock-analysis-supply (0/1), virtualhome-agent-planning (1/1 PASS) |

---

## Ground-Truth Skills 对照实验

### 配置
| 参数 | 值 |
|------|-----|
| 任务路径 | `skillsbench/tasks/` (87 tasks, 人工构建 skills) |
| 运行次数 | 2 轮 (各 `-k 1`) |
| 超时倍率 (--timeout-multiplier) | 5 |
| 并发数 (-n) | 4 |
| 模型 (-m) | claude-opus-4-6 |
| Job 目录 (Run 1) | jobs/2026-03-27__09-42-10 |
| Job 目录 (Run 2) | jobs/2026-03-29__09-07-59 |

### 单轮结果
| 指标 | GT Run 1 | GT Run 2 |
|------|----------|----------|
| PASS | 27 | 22 |
| FAIL | 51 | 56 |
| ERROR | 9 | 9 |
| Pass rate (excl errors) | 27/78 = 34.6% | 22/78 = 28.2% |

### GT Run 2 差异分析
- PASS→FAIL 翻转: 10 tasks (3d-scan-calc, adaptive-cruise-control, dapt-intrusion-detection, econ-detrending-correlation, exceltable-in-ppt, flood-risk-analysis, software-dependency-audit, syzkaller-ppdev-syzlang, threejs-to-obj, video-tutorial-indexer)
- FAIL→PASS 翻转: 5 tasks (fix-druid-loophole-cve, fix-visual-stability, sales-pivot-analysis, threejs-structure-parser, weighted-gdp-calc)
- **原因**: 非 API 问题（两轮 api_retry 频率相似），主要是任务本身的不确定性

---

## No-Skills Baseline 实验

### 配置
| 参数 | 值 |
|------|-----|
| 任务路径 | `skillsbench/tasks-no-skills/` (86 tasks, 无 skills) |
| 运行次数 (-k) | 1 |
| 超时倍率 (--timeout-multiplier) | 5 |
| 并发数 (-n) | 4 |
| 模型 (-m) | claude-opus-4-6 |
| Job 目录 | jobs/2026-03-28__13-26-52 |

### 结果
- **PASS: 20** (23.3%)
- **FAIL: 57** (66.3%)
- **ERROR: 9** (10.5%, AgentTimeoutError 23, RuntimeError 4, ValueError 1, RewardFileNotFoundError 2)
- **Pass rate (excl errors): 20/77 = 26.0%**

---

## 三方总对比（最终版，GT 含 2 轮数据）

### Trial-level（所有有效 trial 合并计算）
| 指标 | DRskill (2轮) | Ground-Truth (2轮) | No-Skills (1轮) |
|------|--------------|-------------------|-----------------|
| Pass rate (excl errors) | 77/152 = **50.7%** | 49/156 = **31.4%** | 20/77 = **26.0%** |

### Task-level（best of 2: 至少一次通过即算 PASS）
| 指标 | DRskill | Ground-Truth | No-Skills |
|------|---------|-------------|-----------|
| PASS tasks | 45/77 = **58.4%** | 32/78 = **41.0%** | 20/77 = **26.0%** |

### 逐任务完整对比（5 列）

| # | 任务名 | DRskill R1 | DRskill R2 | GT R1 | GT R2 | No-Skills |
|---|--------|-----------|-----------|-------|-------|-----------|
| 1 | 3d-scan-calc | PASS | PASS | PASS | FAIL | PASS |
| 2 | adaptive-cruise-control | PASS | FAIL | PASS | FAIL | FAIL |
| 3 | azure-bgp-oscillation-route-leak | PASS | FAIL | FAIL | FAIL | FAIL |
| 4 | citation-check | PASS | PASS | PASS | PASS | FAIL |
| 5 | civ6-adjacency-optimizer | FAIL | FAIL | FAIL | FAIL | FAIL |
| 6 | court-form-filling | ERROR | PASS | FAIL | FAIL | FAIL |
| 7 | crystallographic-wyckoff-position-analysis | PASS | PASS | PASS | PASS | FAIL |
| 8 | dapt-intrusion-detection | FAIL | FAIL | PASS | FAIL | FAIL |
| 9 | data-to-d3 | PASS | FAIL | FAIL | FAIL | FAIL |
| 10 | dialogue-parser | PASS | PASS | PASS | PASS | PASS |
| 11 | dynamic-object-aware-egomotion | FAIL | FAIL | FAIL | FAIL | FAIL |
| 12 | earthquake-phase-association | PASS | PASS | PASS | PASS | PASS |
| 13 | earthquake-plate-calculation | FAIL | FAIL | FAIL | FAIL | FAIL |
| 14 | econ-detrending-correlation | PASS | PASS | PASS | FAIL | PASS |
| 15 | energy-ac-optimal-power-flow | PASS | PASS | FAIL | FAIL | FAIL |
| 16 | energy-market-pricing | PASS | PASS | FAIL | FAIL | PASS |
| 17 | enterprise-information-search | FAIL | FAIL | FAIL | FAIL | FAIL |
| 18 | exceltable-in-ppt | FAIL | FAIL | PASS | FAIL | FAIL |
| 19 | exoplanet-detection-period | FAIL | FAIL | FAIL | FAIL | FAIL |
| 20 | financial-modeling-qa | FAIL | FAIL | FAIL | FAIL | FAIL |
| 21 | find-topk-similiar-chemicals | FAIL | FAIL | FAIL | FAIL | FAIL |
| 22 | fix-build-agentops | FAIL | FAIL | FAIL | FAIL | FAIL |
| 23 | fix-build-google-auto | PASS | PASS | FAIL | FAIL | FAIL |
| 24 | fix-druid-loophole-cve | PASS | PASS | FAIL | PASS | PASS |
| 25 | fix-erlang-ssh-cve | PASS | PASS | FAIL | FAIL | PASS |
| 26 | fix-visual-stability | PASS | PASS | FAIL | PASS | PASS |
| 27 | flink-query | FAIL | FAIL | FAIL | FAIL | FAIL |
| 28 | flood-risk-analysis | FAIL | FAIL | PASS | FAIL | FAIL |
| 29 | gh-repo-analytics | FAIL | FAIL | FAIL | FAIL | FAIL |
| 30 | glm-lake-mendota | PASS | PASS | PASS | PASS | PASS |
| 31 | gravitational-wave-detection | PASS | PASS | PASS | PASS | PASS |
| 32 | grid-dispatch-operator | PASS | PASS | FAIL | FAIL | PASS |
| 33 | hvac-control | PASS | FAIL | PASS | PASS | PASS |
| 34 | invoice-fraud-detection | PASS | FAIL | FAIL | FAIL | FAIL |
| 35 | jax-computing-basics | PASS | PASS | FAIL | FAIL | PASS |
| 36 | jpg-ocr-stat | FAIL | FAIL | FAIL | FAIL | FAIL |
| 37 | lab-unit-harmonization | FAIL | FAIL | FAIL | FAIL | FAIL |
| 38 | lake-warming-attribution | PASS | PASS | FAIL | FAIL | FAIL |
| 39 | latex-formula-extraction | FAIL | FAIL | FAIL | FAIL | FAIL |
| 40 | lean4-proof | FAIL | PASS | PASS | PASS | FAIL |
| 41 | manufacturing-codebook-normalization | ERROR | ERROR | ERROR | ERROR | ERROR |
| 42 | manufacturing-equipment-maintenance | ERROR | ERROR | ERROR | ERROR | ERROR |
| 43 | manufacturing-fjsp-optimization | ERROR | ERROR | ERROR | ERROR | ERROR |
| 44 | mario-coin-counting | FAIL | FAIL | PASS | PASS | FAIL |
| 45 | mars-clouds-clustering | PASS | PASS | PASS | PASS | PASS |
| 46 | mhc-layer-impl | ERROR | ERROR | ERROR | ERROR | ERROR |
| 47 | multilingual-video-dubbing | ERROR | ERROR | ERROR | ERROR | ERROR |
| 48 | offer-letter-generator | PASS | PASS | PASS | PASS | FAIL |
| 49 | organize-messy-files | FAIL | FAIL | FAIL | FAIL | FAIL |
| 50 | paper-anonymizer | FAIL | FAIL | FAIL | FAIL | FAIL |
| 51 | parallel-tfidf-search | PASS | FAIL | PASS | PASS | PASS |
| 52 | pddl-tpp-planning | PASS | PASS | FAIL | FAIL | FAIL |
| 53 | pdf-excel-diff | PASS | FAIL | FAIL | FAIL | FAIL |
| 54 | pedestrian-traffic-counting | FAIL | FAIL | FAIL | FAIL | FAIL |
| 55 | pg-essay-to-audiobook | FAIL | FAIL | FAIL | FAIL | FAIL |
| 56 | powerlifting-coef-calc | PASS | PASS | PASS | PASS | PASS |
| 57 | pptx-reference-formatting | PASS | PASS | PASS | PASS | FAIL |
| 58 | protein-expression-analysis | PASS | PASS | PASS | PASS | FAIL |
| 59 | python-scala-translation | PASS | PASS | FAIL | FAIL | FAIL |
| 60 | quantum-numerical-simulation | FAIL | FAIL | FAIL | FAIL | FAIL |
| 61 | r2r-mpc-control | PASS | FAIL | FAIL | FAIL | FAIL |
| 62 | react-performance-debugging | FAIL | FAIL | FAIL | FAIL | FAIL |
| 63 | reserves-at-risk-calc | FAIL | FAIL | FAIL | FAIL | FAIL |
| 64 | sales-pivot-analysis | PASS | FAIL | FAIL | PASS | FAIL |
| 65 | scheduling-email-assistant | ERROR | ERROR | ERROR | ERROR | ERROR |
| 66 | sec-financial-report | FAIL | FAIL | FAIL | FAIL | FAIL |
| 67 | seismic-phase-picking | FAIL | FAIL | FAIL | FAIL | FAIL |
| 68 | setup-fuzzing-py | PASS | FAIL | FAIL | FAIL | FAIL |
| 69 | shock-analysis-demand | FAIL | FAIL | FAIL | FAIL | FAIL |
| 70 | shock-analysis-supply | FAIL | FAIL | FAIL | FAIL | FAIL |
| 71 | simpo-code-reproduction | PASS | PASS | FAIL | FAIL | FAIL |
| 72 | software-dependency-audit | PASS | PASS | PASS | FAIL | FAIL |
| 73 | speaker-diarization-subtitles | ERROR | ERROR | ERROR | ERROR | ERROR |
| 74 | spring-boot-jakarta-migration | ERROR | ERROR | ERROR | ERROR | ERROR |
| 75 | suricata-custom-exfil | ERROR | ERROR | ERROR | ERROR | ERROR |
| 76 | syzkaller-ppdev-syzlang | PASS | PASS | PASS | FAIL | PASS |
| 77 | taxonomy-tree-merge | PASS | PASS | PASS | PASS | PASS |
| 78 | threejs-structure-parser | FAIL | FAIL | FAIL | PASS | FAIL |
| 79 | threejs-to-obj | PASS | PASS | PASS | FAIL | PASS |
| 80 | travel-planning | PASS | PASS | FAIL | FAIL | FAIL |
| 81 | trend-anomaly-causal-inference | PASS | PASS | PASS | PASS | PASS |
| 82 | video-filler-word-remover | FAIL | FAIL | FAIL | FAIL | FAIL |
| 83 | video-tutorial-indexer | PASS | PASS | PASS | FAIL | FAIL |
| 84 | virtualhome-agent-planning | ERROR | PASS | FAIL | FAIL | FAIL |
| 85 | weighted-gdp-calc | FAIL | FAIL | FAIL | PASS | FAIL |
| 86 | xlsx-recover-data | FAIL | FAIL | FAIL | FAIL | FAIL |

> 注: video-silence-remover 仅存在于 tasks/ 不在 tasks_to_test/tasks-no-skills 中，未列入对比。

### 结论

**DRskill 生成的 skills 显著优于人工构建的 ground-truth skills 和无 skills 基线：**

| 对比维度 | DRskill | Ground-Truth | No-Skills |
|----------|---------|-------------|-----------|
| Trial-level pass rate | **50.7%** | 31.4% | 26.0% |
| Task-level best-of-2 | **58.4%** | 41.0% | 26.0% |

- **DRskill vs GT**: trial-level 高 19.3pp，task-level 高 17.4pp
- **GT vs No-Skills**: trial-level 高 5.4pp
- **DRskill vs No-Skills**: trial-level 高 24.7pp
- 9 个任务在所有条件下均 ERROR（超时），为基础设施限制而非 skill 问题
- GT Run 2 比 Run 1 下降 6.4pp（34.6%→28.2%），经分析为任务不确定性而非 API 问题
