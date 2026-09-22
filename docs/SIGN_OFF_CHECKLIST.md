# 补丁提案签字清单（人工部分）

机器门禁（`python -m pipeline.check <proposal>` exit 0）只是**必要条件**。以下各项须人工逐条勾选后，提案才算进入「可合入」状态。本清单与校验器分工：机器管可枚举规则与内部一致性，本单管机器给不了的判断。

对象：提案 `________________`　　补丁日期 `__________`　　英雄 `__________`

## A. 提取与应用（对照官方原文，不看 Agent 的说明）
- [ ] `pipeline.compare` 已显式指定本次英雄范围（单英雄用 `--hero`）；missing / wrong_value / extra / unmapped_forced / unmapped_dropped / agent_extra_unmapped / missing_hero / extra_hero / duplicate_path / invalid_scope 均为 0
- [ ] `unmapped` 里每一行我都看过，确认它确实映射不到任何字段（不是 Agent 偷懒）
- [ ] 分模式条目（5v5 / 6v6）落在了正确的 `.v5 / .v6` 路径上，没有把一个模式的值写到另一个模式

## B. REVIEW 处置
- [ ] `reviews/decisions.yaml` 中本提案的每条 REVIEW 已处置（accepted / false_positive / needs_revision / resolved），各带 reason 与 scope
- [ ] 无任何「全局豁免」式决定（每条 scope 都限定到 hero + 字段/检查）
- [ ] needs_revision 均有后继修订、重验和关闭记录；仅填写 needs_revision 不等于问题已解决。助手复核不等于所有者签字
- [ ] 审核方与执行方方向不一致的每一处，我都读了 reconcile 的 side_by_side，并写明采信哪一方、为什么

## C. 机器给不了的判断
- [ ] 对冲型改动（mixed）：区分字段方向组合、官方解释和实战净效果；缺实测证据可明确写净效果未知，不强迫猜测增强或削弱
- [ ] `duration_s` 这类语义 ambiguous 的字段，每处方向我都按该技能的实际含义确认过（变形时间变短 = 增强；屏障时长变短 = 削弱）
- [ ] 对高低分段、不同模式的影响是否可接受
- [ ] 手感、节奏、是否好玩——本仓库不涉及，但合入前必须有人负责

## D. 来源与前提
- [ ] 本提案依赖的字段没有处于未关闭的来源冲突中（`P0_provenance_status` 无 REVIEW），或已在 decisions 里说明为何可以带着冲突合入
- [ ] 改动前快照是明确的历史版本，或是满足 `config/fixtures/*/README.md` 两条前提的构造夹具
- [ ] 阈值提醒：`spec/invariants.yaml` 的 REVIEW 阈值是本项目初始灵敏度，不触发不等于平衡合格

## E. 未解决事项显式列出
- [ ] 本提案相关的 NOT_RUN 项逐条列出原因（缺输入 / 冲突未关 / 机制未知），并注明谁负责补
- [ ] 明确声明：本门禁**不能查全所有数值缺陷**；数值正确性以配置表与官方原文为准，可玩性以实测为准

签字：＿＿＿＿＿＿　日期：＿＿＿＿＿＿
