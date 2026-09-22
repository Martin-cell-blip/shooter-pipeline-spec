# 同类项目调研与吸收记录（迭代 2，2026-09-23）

在 GitHub 与论文里找"把补丁说明变成结构化改动、并对 LLM 产出做机器校验"的同类工作。下面按"它做了什么 → 我们缺什么 → 本次吸收了什么 / 为什么没吸收"记录。只吸收读过源码或文档、且能在本仓库落成测试的机制。

## 1. bamsemats/dota-patch-intelligence（TypeScript，0 star，2026-09 仍在更新）— 最接近的同类

Dota 2 补丁说明 → 结构化平衡事实 → 英雄特征向量，带对真实胜率的事后校准。

| 它的机制 | 出处 | 我们的对应 | 本次处置 |
|---|---|---|---|
| **四态分类**：NUMERIC（正则抽 old/new，不用 LLM）/ KNOWN_SEMANTIC（本体短语匹配）/ PARTIALLY_CLASSIFIED（关键词交集，置信 0.5）/ UNKNOWN（进人工队列） | `docs/CLASSIFICATION_ARCHITECTURE.md` | 我们整段原文直接喂 LLM，NUMERIC 层没有确定性基线 | **吸收** → `pipeline/preclassify.py`。用官方页面全部 68 条真实条目做语料：56 条 NUMERIC 全部解析，含 `to X (Up from Y)`、`0.065s`、`12.5% per second`、`(6v6)` 等形态；`compare` 新增 `numeric_vs_regex_mismatch`——模型的 from/to 与正则不一致即验收失败 |
| **语义本体 + 人工覆盖登记**：`semantic_tags.json`（tag / matchPatterns / impactAreas）、`manual_overrides.json`（rawNote / classificationType / reason） | `research-output/ontology/` | 非数值行每次都落 unmapped；我们的 `decisions.yaml` 相当于 overrides，但没有回填成可复用的本体 | **吸收** → `spec/ontology.yaml`（6 个标签：AUDIO_ONLY / VISUAL_ONLY / ANIMATION_ADDED / CAMERA_CONTROL / INTERACTION_RULE / RELATIVE_ONLY_CHANGE），并写明扩展路径＝decisions 先判、再回填本体 |
| **金标数据集 + 精确率/召回率门槛 + 验证日志**：数值精确率 ≥ 98%，任何 parser/prompt 改动必须全量重跑，结果按引擎版本存 `validation-logs/` | `docs/VALIDATION.md` | 有金标与逐例 compare，没有汇总指标、没有按 prompt 版本留痕 | **吸收** → `pipeline/evaluate.py`：汇总 numeric_precision / numeric_recall / unmapped_handling，日志文件名含提案格式文本的 sha8（＝引擎版本） |
| **校准回归门**：先测基线准确率 → 改权重 → 重跑 → 低于基线就回滚并 exit 1 | `apps/scripts/regressionGate.ts` | CI 只保证金标 0 FAIL，不比较"这次 prompt 改完模型提取变差了没" | **吸收**（改造）→ `evaluate.py --gate`：与上一条日志比，任一指标或任一案例变差 → exit 1。不做自动回滚（我们的"权重"是 prompt 文本，回滚＝git revert，交人） |
| **事实锚定 + "规则律师"二审 + 确定性事实检查脚本**（LLM 提到不存在的技能 → CRITICAL） | `docs/MECHANICAL_VALIDATION.md` | 已有：改动前快照即事实锚定；`apply` 路径不存在 → FAIL；审核 Agent 即零上下文二审 | 不重复吸收，记为已覆盖 |
| **对真实胜率的经验校准**（Empirical Truth Score） | `docs/WINRATE_CALIBRATION.md` | 无对局数据 | **不吸收**：本仓库不判平衡结果，只判提取与配置一致性；写进边界 |

## 2. NFAsylum/balance-studio（Python，2026）— LLM 协作平衡框架

"LLM 出方案 → 确定性模拟 → 指标 + LLM 评审 → 再提案"，明确把可信部分（模拟）做成 LLM-free。

| 它的机制 | 本次处置 |
|---|---|
| **约束即数据**：`constraint_engine.py` 的 kind + params（range / sum_of_fields / forbidden_combo / required_tag / unique_across_set） | **部分吸收**：range 与 sum 我们已有（F1、F3）；补 `unique_across_set` → `F8_unique_ids`（重复 id 会让路径寻址静默取第一个）。forbidden_combo / required_tag 依赖标签体系，暂无对应字段，不加 |
| **三顶帽子**：Designer / SubjectiveJudge / Iterator 各自独立协议，可换成 Fake 做测试 | 与我们"执行 / 审核 / 人"三角色同构；它的 Fake LLM 做法值得下一轮借（现在测试全靠离线 mock 的是校验器，Agent 层没有 Fake） |
| 事件溯源 + 分支 + 时间旅行 | 不吸收：我们的历史在 git 与 runs/ |

## 3. drg-tools/drg-weapons-calculator（Java，Deep Rock Galactic 武器计算器）

| 它的机制 | 本次处置 |
|---|---|
| **Average Overkill**（击杀那一发浪费的伤害）、Breakpoints、Sustained DPS 的多开关口径（含/不含弱点、精度、护甲） | **吸收 overkill** → `metrics.overkill`，并写进 R9 记录：等离子剑 65→60 对 250 血，overkill 10→50，一眼看出"离断点只剩 10 点"。Sustained DPS 多开关口径与我们"固定场景"的取舍不同（我们刻意只留一个口径），不吸收 |
| 弹药效率、护甲浪费 | 场景无护甲，不吸收 |

## 4. Adonis-galaxy/RuleSmith（arXiv 2602.06232）— 多智能体 LLM 自博弈 + 贝叶斯优化做平衡

| 它的机制 | 本次处置 |
|---|---|
| LLM 当玩家自博弈，胜率差作为平衡指标，贝叶斯优化在规则空间搜索，输出可解释的参数调整 | **不吸收**：它回答"该改成多少"，本仓库只回答"改动是否被正确提取、是否越过硬规则、是否需要人看"。两者可以串联（它出提案、我们校验），记为后续方向 |

## 5. 其他看过但价值有限

- Meme-Theory/stellaris-wiki-mcp：补丁条目方向枚举 buff / nerf / rework / fix / add / remove——比我们的 buff / nerf / ambiguous 细，`ontology.yaml` 的 `kind` 字段借了 add / rework / cosmetic 三种。
- leonhe9029/game-analytics-capstone：按胜率做 ±3% 的假设性调整模拟——依赖对局数据，不吸收。
- fbis251/overwatch_feed_generator 等 Overwatch 补丁抓取项目：只做 RSS/展示，无分类与校验。
- aws-samples/sample-specship 等 spec-driven agent 工作流：通用软件工程流程，与本仓库"规范 → 执行 → 校验 → 审核 → 人签"同构，无游戏数据层面的机制可借。

## 本次迭代的边界

- 吸收的都是**确定性、可测试**的机制；没有引入任何新的模型调用。
- 68 条真实语料里 UNKNOWN 剩 ≤ 4 条（长句音效说明等），按 Dota 项目的路径它们应进人工队列后回填本体——这是 `ontology.yaml` 的第一批待办。
- 精确率/召回率门槛（0.98 / 0.95 / 0.90）借的是 Dota 项目的量级，n 太小（9 案例）只作 REVIEW 提示；回归门比较的是相对上一条日志的变差，这才是硬门。
