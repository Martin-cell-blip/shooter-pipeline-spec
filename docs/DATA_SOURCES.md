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

## 待核验

- 未被补丁改动的参数的当前值（伤害、射速、弹匣等）需要第三个来源。候选为社区维基；采用前须逐条与官方补丁说明的"改动后值"交叉核对，核不上的字段留空并在校验时报 `NOT_RUN`，不猜值。
