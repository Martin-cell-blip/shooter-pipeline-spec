# shooter-pipeline-spec

把射击游戏生产管线里的一段，写成 **Agent 可执行、机器可校验**的规范。

场景：一次平衡性补丁。输入是包含改动前后数值的补丁原文、改动前快照与 schema，输出是配置改动提案；校验器检查提取与应用，由独立审核环节检查方向和依据，最后留给人签字。数据带出处与日期。第 5 步输入隔离与验收要求见 [执行 Agent 契约](docs/EXECUTION_AGENT_CONTRACT.md)。

## 现状

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | 仓库骨架；六条子管线的控制表；数据来源核验记录 | 已完成 |
| 2 | 配置表字段定义；五个样本英雄的基线数据（逐字段出处、跨来源冲突登记）；09-08 真实补丁样本 | 已完成 |
| 3 | 不变量 v0（6 条 FAIL 级 + 10 条 REVIEW 级，同英雄前后对比为主）；校验器；改动前夹具；官方补丁按提案格式的金标样本 | 已完成 |
| 4 | 24 项测试（每条规则至少一个触发与一个不触发用例；异常永不变 PASS；金标 0 FAIL）；CI 含夹具幂等性检查 | 已完成 |
| 5 | 执行 Agent（DeepSeek）：补丁原文 + 改动前快照 + 字段语义 → 提案 YAML；提取验收脚本；首轮实跑 6/6 匹配、0 FAIL（样本偏易，见 `docs/RUN_LOG.md`） | 已完成 |
| 6 | 四个难样本英雄（查莉娅、巴蒂斯特、吴阳、D.Mon）；补丁叠加的夹具链式撤销；run 1 原样记录：金标自身 2 处缺陷被校验器抓出、Agent 偏差 3 处全部指向规范文本 | 已完成 |
| 7 | 按 run 1 改规范（金标方向、F4 伙伴字段存在性、提案格式三处）并固化 7 项回归测试；run 2 复跑：4/4 提取全对，暴露 1 类新错误（A4）→ 新增 F7 自洽规则 | 已完成 |
| 8 | 审核 Agent（只读 diff，泄漏自检）+ reconcile 三方并排；7 例：4 例与官方注释一致，2 处上下文差被抓成 REVIEW，1 例无官方注释单独成立 | 已完成 |
| 9 | REVIEW 决定文件（`reviews/decisions.yaml`）+ 格式校验 `pipeline/decisions.py`（pending 未清零 / 缺理由 / scope 全局或不含英雄 / 漏项 → CI 红）；决定内容由人填 | 校验已接 CI，待人填 |
| 10 | 人工签字清单（`docs/SIGN_OFF_CHECKLIST.md`）；迭代历史 = `docs/RUN_LOG.md` + git log | 清单已出 |

第 6 步以后的内容取决于实跑结果，不预先编排。

## 文档

- [管线总图（控制表）](docs/PIPELINE_MAP.md)：战斗、关卡、数值、叙事、配置表、资源六条子管线各自的产出物、权威来源、可机检范围与 Agent 可接的任务；本仓库只实现其中"数值 + 配置表"一条竖切。
- [签字清单](docs/SIGN_OFF_CHECKLIST.md)：机器门禁之外必须由人确认的判断。
- [实跑记录](docs/RUN_LOG.md)：每轮实跑、每处失败、每次规范修改的指回关系。
- [数据来源核验记录](docs/DATA_SOURCES.md)：每个来源实际提供什么、不提供什么，以及三源交叉核对发现的不一致。
- `config/schema.yaml`：字段定义、单位、硬边界、联动字段。
- `config/sources.yaml`：来源登记与权威顺序。
- `config/baseline/*.yaml`：索杰恩、麦克雷、雾子、猎空、温斯顿五个样本英雄；每个文件带 `provenance`（默认来源／逐字段覆盖／冲突／缺失）。
- `config/patches/2026-09-08.yaml`：官方补丁的真实样本，含开发者注释（＝补丁意图）与改动前后值（＝验收答案）。
- `spec/invariants.yaml`：不变量 v0。固定测试场景（175 / 250 血目标、满弹匣、身体全命中、不计弹道时间）、FAIL 级硬规则、REVIEW 级经验阈值。阈值是本项目初始审查灵敏度，不是官方平衡标准。
- `config/fixtures/2026-09-08_before/`：构造的「改动前」快照（基线回填官方 from 值），前提与方法见其 README。
- `proposals/2026-09-08_official.yaml`：官方补丁按提案格式写出的金标样本。
- `pipeline/`：`loader`（读取与路径寻址）、`metrics`（完整周期 DPS、离散 TTK、射击次数断点、可用时间占比等）、`checks`（四态校验）、`report`、`fixture`、`check`（入口）、`agent`（执行 Agent，只读原文与改动前快照，不读 baseline、不读校验器、不自评）、`compare`（提取验收）。
- `config/patches/2026-09-08_raw.txt`：给 Agent 的非结构化原文（无字段路径、无方向标签）。
- `runs/`：每次实跑的完整 prompt、原始回复、模型与用时；`docs/RUN_LOG.md` 是人读的实跑记录。
- `pipeline/reviewer.py`：审核 Agent，只读 {path, from, to}；`pipeline/reconcile.py`：执行方声明 × 审核方反推 × 官方注释 → REVIEW 项；`reviews/`：审核输出与比对结果。

## 运行

```bash
python -m pipeline.fixture build 2026-09-17 && python -m pipeline.fixture build 2026-09-08   # 构造改动前夹具（幂等；09-08 会先撤销 09-17）
python -m pipeline.check 2026-09-08_official      # 校验金标提案 → reports/
python -m pytest -q                                # 24 项测试
python -m pipeline.agent 2026-09-08 kiriko         # 执行 Agent（需 DEEPSEEK_API_KEY）→ proposals/agent/ + runs/
python -m pipeline.compare proposals/agent/2026-09-08_kiriko_run1.yaml   # 与官方金标比对提取结果
python -m pipeline.check agent/2026-09-08_kiriko_run1                    # 对 Agent 提案跑校验器
python -m pipeline.reviewer proposals/agent/2026-09-08_kiriko_run1.yaml  # 审核 Agent（只读 diff）
python -m pipeline.reconcile 2026-09-08 kiriko 1                          # 三方并排 → reviews/*_reconcile.json
python -m pipeline.decisions                                              # 决定文件格式校验（CI 门禁）
```

退出码：`0` 无 FAIL（允许 REVIEW / 缺输入的 NOT_RUN）；`1` 有 FAIL；`2` 加载失败或检查抛异常。金标样本当前结果见 `reports/2026-09-08_official.md`。温斯顿生命值模式差异和屏障冷却起算已现场核验，见 [来源核验](docs/WINSTON_SOURCE_REVIEW.md)。剩余 NOT_RUN 的原因逐项列于报告；通过现有测试不代表已证明不存在缺陷。

## 几条贯穿全仓库的规则

1. 一个事实只认一个权威来源；数值以配置表为准。
2. 校验结果四态：`PASS`／`FAIL`／`REVIEW`／`NOT_RUN`。启发式命中只报 `REVIEW`；任何异常都不返回成功。
3. 基线只能用显式命令更新，普通运行只读。
4. 执行方不自评；审核方不读执行方的说明。
5. 终态只到 `READY_FOR_HUMAN_REVIEW`。
