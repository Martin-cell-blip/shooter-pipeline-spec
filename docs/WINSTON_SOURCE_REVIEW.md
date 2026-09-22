# Winston 来源核验 — 2026-09-22

核验者：Codex（来源核验；不是人类最终签字）。

浏览器读取 https://overwatch.fandom.com/wiki/Winston 的 Game info：

| 页面模式标签 | 生命值 | 护甲 | 两项合计 |
|---|---:|---:|---:|
| Open queue | 275 | 200 | 475 |
| Role queue | 425 | 200 | 625 |
| 6v6 | 325 | 200 | 525 |

同日实时请求 https://overfast-api.tekrop.fr/heroes/winston 返回 health=425、armor=200、shields=0、total=625。
原始冲突来自只抽取 wiki 第一项、遗漏模式标签。当前 baseline 的 hitpoints 明确限定为 5v5_role_queue；不将该值推广到开放队列或 6v6。
保留原冲突记录并标 RESOLVED，而不是删除核验历史。

同页 Barrier Projector 的 Additional details 明确冷却从激活时开始，因此补充 cooldown_starts=on_cast。
R10 此处计算的是未被提前摧毁、忽略部署延迟的名义持续时间比，不是实战覆盖率；页面另列 0.13 秒激活延迟，当前模型未纳入。
该规则不依赖英雄生命值，关闭生命值冲突本身不会关闭 R10。

夹具继续是从当前基线构造的测试输入，并非历史抓取；本次核验不额外证明这些机制在历史日期完全相同。
