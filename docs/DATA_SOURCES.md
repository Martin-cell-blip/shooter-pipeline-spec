# 数据来源核验记录

原则：每个来源先核实"它到底提供什么"，再决定用不用；结论带核验日期。配置表里每条取值另行标注出处网址与抓取日期。

## 已核验

### 守望先锋官方补丁说明
- 地址：`https://overwatch.blizzard.com/en-us/news/patch-notes/`
- 核验日期：2026-09-20
- 实测：页面可直接抓取（HTTP 200）；当前页含 40 条形如 `… reduced/increased from X to Y` 的数值变更，最新一期日期为 2026-09-17。
- 提供：参数的**改动前值与改动后值**、所属英雄与技能、部分条目的适用模式（出现了 `(5v5)`／`(6v6)` 分别给值的情况）。
- 不提供：未被改动的参数的当前值。
- 用途：①补丁意图的真实样本（执行 Agent 的输入）；②被改动参数的基线值与目标值。

### OverFast API
- 地址：`https://overfast-api.tekrop.fr/heroes/{hero}`
- 核验日期：2026-09-20
- 实测返回字段：`name, description, backgrounds, portrait, role, subrole, location, birthday, age, hitpoints, abilities, perks, story, stadium_powers`。
- 提供：英雄定位、`hitpoints`（生命／护甲／护盾／合计）、技能名称与**文字描述**。
- **不提供：伤害、射速、衰减距离、冷却等任何战斗数值**（技能条目只有 `name, description, icon, video`）。
- 用途：英雄与技能的主键清单、生命值基线、§4 文案一致性检查所需的技能描述文本。

### Overwatch Wiki（fandom）
- 地址：`https://overwatch.fandom.com/wiki/{Hero}`
- 核验日期：2026-09-22
- 实测：curl 与 liquipedia 同样返回 403（Cloudflare）；浏览器可读。每个技能有一个 `.ability-box` 块，结构化字段形如 `Damage:70 - 21 / Falloff range:25 - 35 meters / Rate of fire:2 shots/s`；抓取时排除标注 `(old)` 的历史块与 Perk 块。
- 提供：未被近期补丁改动的参数的当前值——这是官方补丁说明与 OverFast 都给不了的部分。
- 用途：五个样本英雄的默认基线来源（authority 3，最低）。

## 三源交叉核对结果（2026-09-22）

| 英雄 | 字段 | 官方补丁 | wiki | 处置 |
|---|---|---|---|---|
| 雾子 | 治愈符 弹速 | 24 → 18（09-08） | 仍写 30 (homing) / 24 (non-homing) | 取补丁值 18；登记 REVIEW——补丁改的是两个速度中的哪一个尚待确认 |
| 雾子 | 治愈符 索敌距离 | 35 → 30（09-08） | 仍写 35 | 取补丁值 30；登记 REVIEW |
| 雾子 | 护身铃 无敌时长 / 半径 | 0.65 → 0.5；5 → 4 | 已写 0.5；4 | 一致，RESOLVED。**同一页面里一个技能已更新、另一个没更新**——wiki 只能按字段信任，不能按页面信任 |
| 温斯顿 | 屏障 冷却 / 持续 | 12 → 10 (5v5)；8 → 7 | 10；7 | 一致 |
| 温斯顿 | 生命值 | — | 信息框首项 275 | OverFast 给 425 + 200 护甲 = 625；差距过大，疑为口径不同（模式或含/不含护甲），**留空不猜**，REVIEW |

### 未能覆盖的字段
- 温斯顿屏障冷却的 6v6 值（补丁只给 5v5）。
- 索杰恩充能射击的射速（wiki 只给 0.64 s 施放时间，表中为派生值并标注）。
- 蓄力型武器（温斯顿副武器）的最低/最高蓄力伤害与 schema 里"距离衰减"语义的 `damage_min` 不是一回事，schema 需扩展。

以上均记录在各英雄文件的 `provenance.conflicts` / `provenance.missing`，校验器读到时对相应检查报 `NOT_RUN`。
