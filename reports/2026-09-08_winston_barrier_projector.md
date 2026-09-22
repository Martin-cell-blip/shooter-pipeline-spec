# 2026-09-08_winston_barrier_projector

**结论：READY_FOR_HUMAN_REVIEW**（exit 0）— FAIL 0 / REVIEW 1 / NOT_RUN 5 / PASS 19

终态不设自动批准；READY_FOR_HUMAN_REVIEW 表示机器已无 FAIL，剩余 REVIEW / NOT_RUN 须人工逐条处置并写入决定文件。

## REVIEW (1)

| check | hero | detail |
|---|---|---|
| F5_direction_vs_declared | winston | abilities.barrier_projector.duration_s: field semantics 'ambiguous' — direction cannot be machine-judged; declared=nerf, reason='原文 "Duration reduced from 8 to 7 seconds."，持续时间缩短削弱屏障可用时长；duration_s 语义为 ambiguous，按上下文（缩短可用时间）判为 nerf。' |

## NOT_RUN (5)

| check | hero | detail |
|---|---|---|
| P0_provenance_status | winston | missing field abilities.barrier_projector.cooldown_s.v6: 补丁只给 5v5 值，6v6 未查到可靠出处 |
| P0_provenance_status | winston | missing field weapons.tesla_cannon_alt.damage_min: 该字段语义是「最低蓄力伤害」而非距离衰减，与 schema 中 damage_min 定义不同——schema 需要 charge_min/charge_max 扩展，记入待办 |
| R1_full_cycle_dps_delta | winston | tesla_cannon_alt: ammo or reload_s missing (full-cycle DPS needs both) |
| R10_uptime_ratio | winston | barrier_projector[v6]: duration_s or cooldown_s missing |
| R10_uptime_ratio | winston | primal_rage: duration_s or cooldown_s missing |

## PASS (19)

| check | hero | detail |
|---|---|---|
| F1_schema_bounds | winston | all numeric fields within project bounds |
| F2_falloff_structure | winston | falloff structure consistent for all weapons |
| F3_hitpoints_sum | winston | total 625 = sum of components |
| F4_linked_disposition | winston | every touched linked pair has a disposition record |
| F5_direction_vs_declared | winston | abilities.barrier_projector.cooldown_s.v5: 12→10 = buff, matches declaration |
| R1_full_cycle_dps_delta | winston | tesla_cannon: full-cycle body DPS 56.00 → 56.00 (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | winston | tesla_cannon vs 175hp body: TTK 2.500s → 2.500s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | winston | tesla_cannon vs 250hp body: TTK 3.571s → 3.571s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | winston | tesla_cannon_alt vs 175hp body: TTK 3.175s → 3.175s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | winston | tesla_cannon_alt vs 250hp body: TTK 6.349s → 6.349s (+0.0%) |
| R3_headshot_oneshot_change | winston | tesla_cannon: one-shot capability unchanged (False) |
| R3_headshot_oneshot_change | winston | tesla_cannon_alt: one-shot capability unchanged (False) |
| R4_change_count_stats | winston | changes: {'buff': 1, 'nerf': 1, 'ambiguous': 0} (display only, no threshold) |
| R5_falloff_window_delta | winston | no falloff weapons |
| R6_cooldown_step | winston | barrier_projector[v5]: cooldown 12s → 10s (Δ2.00s, 16.7%) |
| R8_mixed_direction_rationale | winston | mixed, rationale given: '冷却时间缩短（12→10s）为增益，屏障持续时间缩短（8→7s）为削弱，两者按原文设计意图相互对冲。' (local directions only; net effect not machine-judged) |
| R9_shots_to_kill_breakpoint | winston | tesla_cannon_alt vs 175hp body: 3 → 3 shot events |
| R9_shots_to_kill_breakpoint | winston | tesla_cannon_alt vs 250hp body: 5 → 5 shot events |
| R10_uptime_ratio | winston | barrier_projector[v5]: uptime 66.7% → 70.0% (+3.3pp) |
