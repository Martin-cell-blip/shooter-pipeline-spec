# 2026-09-08_baptiste_immortality_field

**结论：READY_FOR_HUMAN_REVIEW**（exit 0）— FAIL 0 / REVIEW 0 / NOT_RUN 3 / PASS 25

终态不设自动批准；READY_FOR_HUMAN_REVIEW 表示机器已无 FAIL，剩余 REVIEW / NOT_RUN 须人工逐条处置并写入决定文件。

## NOT_RUN (3)

| check | hero | detail |
|---|---|---|
| R10_uptime_ratio | baptiste | regenerative_burst: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | baptiste | immortality_field: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | baptiste | amplification_matrix: duration_s or cooldown_s missing |

## PASS (25)

| check | hero | detail |
|---|---|---|
| P0_provenance_status | baptiste | no open conflicts, no missing fields |
| F1_schema_bounds | baptiste | all numeric fields within project bounds |
| F2_falloff_structure | baptiste | falloff structure consistent for all weapons |
| F3_hitpoints_sum | baptiste | total 250 = sum of components |
| F4_linked_disposition | baptiste | every touched linked pair has a disposition record |
| F5_direction_vs_declared | baptiste | abilities.immortality_field.threshold_pct: 20→25 = buff, matches declaration |
| F5_direction_vs_declared | baptiste | abilities.immortality_field.cooldown_s: 22→20 = buff, matches declaration |
| F5_direction_vs_declared | baptiste | abilities.immortality_field.deployable_health: 125→150 = buff, matches declaration |
| F7_unmapped_vs_changes | baptiste | no line is both mapped and unmapped |
| R1_full_cycle_dps_delta | baptiste | biotic_launcher: full-cycle body DPS 105.15 → 105.15 (+0.0%) |
| R1_full_cycle_dps_delta | baptiste | biotic_launcher_alt: full-cycle body DPS 0.00 → 0.00 (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | baptiste | biotic_launcher vs 175hp body: TTK 1.176s → 1.176s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | baptiste | biotic_launcher vs 175hp head: TTK 0.588s → 0.588s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | baptiste | biotic_launcher vs 250hp body: TTK 1.765s → 1.765s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | baptiste | biotic_launcher vs 250hp head: TTK 0.588s → 0.588s (+0.0%) |
| R3_headshot_oneshot_change | baptiste | biotic_launcher: one-shot capability unchanged (False) |
| R3_headshot_oneshot_change | baptiste | biotic_launcher_alt: one-shot capability unchanged (False) |
| R4_change_count_stats | baptiste | changes: {'buff': 3, 'nerf': 0, 'ambiguous': 0} (display only, no threshold) |
| R5_falloff_window_delta | baptiste | biotic_launcher: window 20m → 20m (+0.0%); start 25→25, end 45→45 |
| R6_cooldown_step | baptiste | immortality_field: cooldown 22s → 20s (Δ2.00s, 9.1%) |
| R8_mixed_direction_rationale | baptiste | single direction {'buff'} |
| R9_shots_to_kill_breakpoint | baptiste | biotic_launcher vs 175hp body: 3 → 3 shot events |
| R9_shots_to_kill_breakpoint | baptiste | biotic_launcher vs 175hp head: 2 → 2 shot events |
| R9_shots_to_kill_breakpoint | baptiste | biotic_launcher vs 250hp body: 4 → 4 shot events |
| R9_shots_to_kill_breakpoint | baptiste | biotic_launcher vs 250hp head: 2 → 2 shot events |
