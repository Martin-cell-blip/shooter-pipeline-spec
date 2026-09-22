# 实跑记录

每次执行 Agent 实跑一条：输入、模型、提取验收（与官方 from/to 比对）、校验结果、发现的问题。失败原样记录，不做事后美化；后续规范修改必须能指回这里的某一条。

## 2026-09-22 · run 1 · deepseek-chat · 补丁 2026-09-08（雾子、温斯顿）

| 英雄 | 提取验收（matched / wrong / missing / extra） | 方向声明 | 校验器 | 用时 / tokens |
|---|---|---|---|---|
| 雾子 | 4 / 0 / 0 / 0 | 4/4 与金标一致；`duration_s` 主动标注"语义 ambiguous，按上下文判 nerf" | 0 FAIL · 3 REVIEW · 3 NOT_RUN | 1.8 s / 1513 |
| 温斯顿 | 2 / 0 / 0 / 0 | 2/2 一致；给出对冲理由；正确挂到 `cooldown_s.v5` 并标 mode | 0 FAIL · 1 REVIEW · 5 NOT_RUN | 1.8 s / 1371 |

输出未加 markdown 围栏，YAML 一次解析成功。**本轮没有失败，原因是样本太容易**：每行自带精确 from/to，技能名与快照 id 几乎一一对应。

## 2026-09-22 · run 1 · deepseek-chat · 难样本（查莉娅、巴蒂斯特、吴阳、D.Mon；补丁 09-08 与 09-17）

先说金标：**新样本的官方金标自己先被校验器打出 2 个 FAIL**，都是我写金标时的错：

| # | 金标缺陷 | 校验器怎么抓到的 | 定性 |
|---|---|---|---|
| G1 | 吴阳 `los_timeout_s` 5→3 我声明 buff | F5：字段语义 higher_is=buff，5→3 是 nerf | 金标写错方向；**Agent 判 nerf 是对的** |
| G2 | D.Mon `plasma_saber.damage_max` 65→60 被 F4 要求给 `damage_min` 处置，但近战武器根本没有 `damage_min` 字段 | F4 只看 schema 的联动对，不看快照里字段是否存在 | **规范缺陷**：联动处置应只对快照中实际存在的伙伴字段要求 |

Agent 五次运行（每次约 2 s）：

| 运行 | 提取验收 | 问题 |
|---|---|---|
| 09-08 查莉娅 | 1/1 matched | 把开发者注释里的一句话（"Projected Barrier remains unchanged…"）放进了 `unmapped`。金标 unmapped 为空 → 记 `agent_extra_unmapped` 1。**规范缺陷**：提案格式没说清 unmapped 只收条目行、不收注释 |
| 09-08 巴蒂斯特 | 3/3 matched，方向全对 | 无（百分比字段 20%→25% 正确映射到 `threshold_pct`） |
| 09-08 吴阳 | 2/2 matched | `los_timeout_s` 方向与金标不一致——见 G1，是金标错。Agent 整体方向标 buff 却含一条 nerf 且无对冲理由 → R8 REVIEW，属正常 |
| 09-08 D.Mon | 4/5 matched，1 missing，1 extra；3 条 unmapped 全部正确保留（施法时间无字段、非数值、非配置改动） | ①护甲路径写成 `hitpoints.armor.v6`，金标是 `hitpoints_by_mode.v6.armor`。**规范缺陷**：我给 Agent 的路径语法只写了 `hitpoints.<field>` 和 `.v5/.v6` 后缀，快照里却是 `hitpoints_by_mode` 结构——Agent 按我给的语法拼的。②`linked_dispositions` 的键写在被改的字段（`falloff_start_m`）上，而不是伙伴字段（`falloff_end_m`）上，F4 会判 FAIL。**规范缺陷**：格式说明没写明"键 = 伙伴字段路径" |
| 09-17 D.Mon | 3/5 matched，2 missing，2 extra；"Damage per bullet 45→36" 正确放进 unmapped，没有硬凑 | 两条护甲路径同样的 `hitpoints.armor.v5/.v6` 问题 |

**本轮定性**：5 次运行里 Agent 的数值提取 0 错（from/to 全对），不可映射条目 4/4 处理正确；所有偏差都指向**我写的规范**——金标方向错 1 处、联动规则 1 处过宽、提案格式 3 处没说清（路径语法、处置键、unmapped 范围）。第 7 步先改规范，把这五条固化成回归测试，再跑 run 2。

## 2026-09-22 · 第 7 步规范修改（指回上表）

| 指回 | 改了什么 | 固化为 |
|---|---|---|
| G1 | 金标 wuyang `los_timeout_s` 改为 nerf，整体 mixed 并注明对冲理由缺失 | `test_G1_golden_wuyang_direction_is_nerf` |
| G2 | F4 只对快照中实际存在的伙伴字段要求处置 | `test_G2_linked_disposition_not_required_when_partner_absent` |
| A1 | 提案格式写明处置键 = 伙伴字段路径，并给例子 | `test_A1_disposition_keyed_on_changed_field_is_not_accepted` |
| A2 | 提案格式的路径语法加入 `hitpoints_by_mode.<v5|v6>.<field>`，并写明"逐级照抄快照键名" | `test_A2_prompt_grammar_covers_hitpoints_by_mode_and_partner_key`、`test_A2_wrong_hitpoints_path_is_caught_by_apply` |
| A3 | 提案格式写明 unmapped 只收条目行、不收开发者注释 | 同 A2 语法测试 |
| — | compare 的 unmapped 三分类（保留 / 硬凑 / 静默丢弃）与空提案必失败 | `test_compare_unmapped_classification`、`test_empty_proposal_fails_acceptance` |

## 2026-09-22 · run 2 · deepseek-chat · 规范修改后重跑 run 1 有偏差的四例

| 运行 | 提取验收 | 校验器 | 与 run 1 相比 |
|---|---|---|---|
| 09-08 查莉娅 | 1/1，unmapped 为空 | 0 FAIL | A3 修正生效：开发者注释不再进 unmapped |
| 09-08 吴阳 | 2/2，`los_timeout_s` 判 nerf 与修正后金标一致 | 0 FAIL · R8 REVIEW（整体标 buff 却含 nerf 且无对冲理由——这是应当被人看的） | 金标改对之后不再有方向不一致 |
| 09-08 D.Mon | 5/5，3 条 unmapped 全部保留 | 0 FAIL | A1、A2 修正生效：护甲路径 `hitpoints_by_mode.v6.armor`，处置键 `falloff_end_m: keep` |
| 09-17 D.Mon | 5/5 数值全对，"45→36" 正确保留 unmapped | **F7 FAIL**（新规则） | **新错误 A4**：把已映射的两行（16→15、4→5）又原样抄进了 unmapped，且带着"- "前缀。compare 记 `agent_extra_unmapped` 2 |

A4 的处置：这是提案自洽问题，不需要金标就能判——新增 FAIL 级规则 `F7_unmapped_vs_changes`（同一原文行不得既作改动依据又列在 unmapped），固化为 `test_A4_line_both_mapped_and_unmapped_fails`。提案格式暂不再加措辞，先看 run 3 是否复现。

**两轮合计（9 个英雄、11 次运行）**：数值 from/to 提取 0 错；不可映射条目 8/8 正确保留；Agent 侧真实错误 1 类（A4）；其余偏差 5 处全部是规范文本或金标的错，且都已固化为回归测试。

## 2026-09-22 · 第 8 步 · 审核 Agent（零上下文，只读 diff）· 7 例

审核方输入 = {path, from, to} 列表 + 字段语义 + 单位表。不给执行方的 why / 方向声明 / 对冲理由，不给开发者注释，不给补丁原文，不给校验报告（`pipeline/reviewer.py` 有泄漏自检，`tests/test_reviewer.py` 锁住）。事后由 `pipeline/reconcile.py` 把三方并排：执行方声明、审核方反推、官方注释。

| 案例 | 比对项 | 审核方反推的意图 vs 官方注释 |
|---|---|---|
| 雾子 09-08 | 0 | 反推"降低远程治疗可达性与团队保护"，与官方"lower healing consistency at longer distances / reduce invulnerability window"一致 |
| 温斯顿 09-08 | 0 | 反推"从单次长驻改为更频繁但更短促"，与官方对冲说法一致；审核方自报"对冲后净覆盖率无法判断"——这正是 R10 该算的事 |
| 查莉娅 09-08 | 0 | 反推"单点定向削弱"；官方注释还提到能量生成与投射屏障不变，diff 里看不到，审核方没有编 |
| 巴蒂斯特 09-08 | 0 | 反推"三项同向增强可用性与存活"，与官方一致 |
| 吴阳 09-08 | 2 | **审核方判整体 mixed，执行方 run 2 写的是 buff**（含一条 nerf 却无对冲理由）；官方注释只解释了增强的那条。审核方把视线超时缩短读成"更依赖保持视线的高强度引导"——这是从 diff 能得到的最合理解读，官方没说 |
| D.Mon 09-08 | 4 | ①`call_mech.duration_s` 1.95→0.95：**审核方判 nerf，执行方判 buff**。执行方对——它读过原文"缩短变形时间以对齐 D.Va"；审核方只见 duration 变短，按保守读法判削弱。`duration_s` 语义 ambiguous 在这里第一次真正咬人 ②整体：审核方 nerf，执行方与官方 mixed ③审核方标记可疑："散布收紧（buff）与衰减起点提前（nerf）方向相反，可能并非同一意图"——官方注释恰好解释了这一对（improve accuracy and reduce effectiveness at longer distances）。审核方没有上下文时把"设计上的有意组合"报成可疑，是预期行为，不是误报 |
| D.Mon 09-17 | 1 | 无官方注释 → 审核方反推"整体削弱生存与机动/输出"单独成立，人须自己判 |

**本步结论**：审核方在 7 例里没有一次凭空编造背景（cannot_determine 每例都列了 2–3 条），4 例与官方注释方向一致；两处不一致（吴阳整体方向、D.Mon 变形时间）都是**上下文差**造成的，而且都被 reconcile 抓成 REVIEW 交给人。这正是"审核方不读执行方说明"的价值：它替人把"没有说明就读不出来的地方"标了出来。

## 2026-09-23 · 第 9 步 · REVIEW 决定文件

19 条 REVIEW 项全部处置（accepted 10 / resolved 5 / needs_revision 3 / false_positive 1），每条带理由与限定范围；格式由 `pipeline/decisions.py` 校验并接入 CI。**决定内容由助手按仓库所有者指示代填，所有者签字待办**（文件头 `_filled` 段有注明）。三条 needs_revision：吴阳提案整体方向应为 mixed 并补对冲理由（#4、#11）；D.Mon 生命值继续留空待第三来源（#12）。附带一处数据修正：`config/patches/2026-09-08.yaml` 中吴阳的 direction 由 buff 改为 mixed（#5）。
