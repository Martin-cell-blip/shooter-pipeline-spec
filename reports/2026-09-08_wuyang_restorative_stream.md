# 2026-09-08_wuyang_restorative_stream

**结论：READY_FOR_HUMAN_REVIEW**（exit 0）— FAIL 0 / REVIEW 1 / NOT_RUN 3 / PASS 16

终态不设自动批准；READY_FOR_HUMAN_REVIEW 表示机器已无 FAIL，剩余 REVIEW / NOT_RUN 须人工逐条处置并写入决定文件。

## REVIEW (1)

| check | hero | detail |
|---|---|---|
| R8_mixed_direction_rationale | wuyang | mixed buff+nerf without mixed_rationale |

## NOT_RUN (3)

| check | hero | detail |
|---|---|---|
| P0_provenance_status | wuyang | missing field weapons.xuanwu_staff.charged: 蓄力档（直击 40 / 溅射 60、消耗 2 弹）未建模，schema 无蓄力扩展 |
| R10_uptime_ratio | wuyang | rushing_torrent: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | wuyang | guardian_wave: cooldown_starts unknown — duration/cooldown must not be presented as coverage |

## PASS (16)

| check | hero | detail |
|---|---|---|
| F1_schema_bounds | wuyang | all numeric fields within project bounds |
| F2_falloff_structure | wuyang | falloff structure consistent for all weapons |
| F3_hitpoints_sum | wuyang | total 225 = sum of components |
| F4_linked_disposition | wuyang | every touched linked pair has a disposition record |
| F5_direction_vs_declared | wuyang | abilities.restorative_stream.regen_pct_s: 12.5→15 = buff, matches declaration |
| F5_direction_vs_declared | wuyang | abilities.restorative_stream.los_timeout_s: 5→3 = nerf, matches declaration |
| F7_unmapped_vs_changes | wuyang | no line is both mapped and unmapped |
| R1_full_cycle_dps_delta | wuyang | xuanwu_staff: full-cycle body DPS 73.47 → 73.47 (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | wuyang | xuanwu_staff vs 175hp body: TTK 1.667s → 1.667s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | wuyang | xuanwu_staff vs 250hp body: TTK 2.667s → 2.667s (+0.0%) |
| R3_headshot_oneshot_change | wuyang | xuanwu_staff: one-shot capability unchanged (False) |
| R4_change_count_stats | wuyang | changes: {'buff': 1, 'nerf': 1, 'ambiguous': 0} (display only, no threshold) |
| R5_falloff_window_delta | wuyang | no falloff weapons |
| R6_cooldown_step | wuyang | no cooldown changes |
| R9_shots_to_kill_breakpoint | wuyang | xuanwu_staff vs 175hp body: 6 → 6 shot events |
| R9_shots_to_kill_breakpoint | wuyang | xuanwu_staff vs 250hp body: 9 → 9 shot events |
