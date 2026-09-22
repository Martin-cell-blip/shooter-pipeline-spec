# 2026-09-08_kiriko_healing_ofuda_protection_suzu

**结论：READY_FOR_HUMAN_REVIEW**（exit 0）— FAIL 0 / REVIEW 3 / NOT_RUN 3 / PASS 23

终态不设自动批准；READY_FOR_HUMAN_REVIEW 表示机器已无 FAIL，剩余 REVIEW / NOT_RUN 须人工逐条处置并写入决定文件。

## REVIEW (3)

| check | hero | detail |
|---|---|---|
| P0_provenance_status | kiriko | open source conflict on weapons.healing_ofuda.projectile_speed: {'patch_notes_official': 18, 'wiki_fandom': '30 (homing) / 24 (non-homing)'} — wiki 在补丁两周后未更新；且 wiki 区分 homing/non-homing 两个速度而补丁只给一个数——补丁改的是哪一个，需确认后才能关闭 |
| P0_provenance_status | kiriko | open source conflict on weapons.healing_ofuda.max_range_m: {'patch_notes_official': 30, 'wiki_fandom': 35} — 同上，wiki 未更新 |
| F5_direction_vs_declared | kiriko | abilities.protection_suzu.duration_s: field semantics 'ambiguous' — direction cannot be machine-judged; declared=nerf, reason='Phased out invulnerability duration reduced from 0.65 to 0.5 seconds; duration_s 语义为 ambiguous，按上下文（无敌窗口缩短）判定为 nerf。' |

## NOT_RUN (3)

| check | hero | detail |
|---|---|---|
| R10_uptime_ratio | kiriko | swift_step: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | kiriko | protection_suzu: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | kiriko | kitsune_rush: duration_s or cooldown_s missing |

## PASS (23)

| check | hero | detail |
|---|---|---|
| F1_schema_bounds | kiriko | all numeric fields within project bounds |
| F2_falloff_structure | kiriko | falloff structure consistent for all weapons |
| F3_hitpoints_sum | kiriko | total 225 = sum of components |
| F4_linked_disposition | kiriko | every touched linked pair has a disposition record |
| F5_direction_vs_declared | kiriko | weapons.healing_ofuda.projectile_speed: 24→18 = nerf, matches declaration |
| F5_direction_vs_declared | kiriko | weapons.healing_ofuda.max_range_m: 35→30 = nerf, matches declaration |
| F5_direction_vs_declared | kiriko | abilities.protection_suzu.radius_m: 5→4 = nerf, matches declaration |
| R1_full_cycle_dps_delta | kiriko | healing_ofuda: full-cycle body DPS 0.00 → 0.00 (+0.0%) |
| R1_full_cycle_dps_delta | kiriko | kunai: full-cycle body DPS 102.27 → 102.27 (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | kiriko | kunai vs 175hp body: TTK 1.000s → 1.000s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | kiriko | kunai vs 175hp head: TTK 0.500s → 0.500s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | kiriko | kunai vs 250hp body: TTK 2.000s → 2.000s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | kiriko | kunai vs 250hp head: TTK 1.000s → 1.000s (+0.0%) |
| R3_headshot_oneshot_change | kiriko | healing_ofuda: one-shot capability unchanged (False) |
| R3_headshot_oneshot_change | kiriko | kunai: one-shot capability unchanged (False) |
| R4_change_count_stats | kiriko | changes: {'buff': 0, 'nerf': 4, 'ambiguous': 0} (display only, no threshold) |
| R5_falloff_window_delta | kiriko | no falloff weapons |
| R6_cooldown_step | kiriko | no cooldown changes |
| R8_mixed_direction_rationale | kiriko | single direction {'nerf'} |
| R9_shots_to_kill_breakpoint | kiriko | kunai vs 175hp body: 3 → 3 shot events |
| R9_shots_to_kill_breakpoint | kiriko | kunai vs 175hp head: 2 → 2 shot events |
| R9_shots_to_kill_breakpoint | kiriko | kunai vs 250hp body: 5 → 5 shot events |
| R9_shots_to_kill_breakpoint | kiriko | kunai vs 250hp head: 3 → 3 shot events |
