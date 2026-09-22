# zarya_particle_barrier_cooldown_2026-09-08

**结论：READY_FOR_HUMAN_REVIEW**（exit 0）— FAIL 0 / REVIEW 0 / NOT_RUN 6 / PASS 20

终态不设自动批准；READY_FOR_HUMAN_REVIEW 表示机器已无 FAIL，剩余 REVIEW / NOT_RUN 须人工逐条处置并写入决定文件。

## NOT_RUN (6)

| check | hero | detail |
|---|---|---|
| P0_provenance_status | zarya | missing field abilities.particle_barrier.cooldown_s.v6: 补丁只给 5v5 值，6v6 未查到可靠出处 |
| P0_provenance_status | zarya | missing field weapons.particle_cannon.energy_scaling: 能量 0%→100% 的伤害缩放（95→175 /s、55→110）未建模，schema 无能量扩展 |
| R10_uptime_ratio | zarya | particle_barrier[v5]: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | zarya | particle_barrier[v6]: duration_s or cooldown_s missing |
| R10_uptime_ratio | zarya | projected_barrier: cooldown_starts unknown — duration/cooldown must not be presented as coverage |
| R10_uptime_ratio | zarya | graviton_surge: duration_s or cooldown_s missing |

## PASS (20)

| check | hero | detail |
|---|---|---|
| F1_schema_bounds | zarya | all numeric fields within project bounds |
| F2_falloff_structure | zarya | falloff structure consistent for all weapons |
| F3_hitpoints_sum | zarya | total 550 = sum of components |
| F4_linked_disposition | zarya | every touched linked pair has a disposition record |
| F5_direction_vs_declared | zarya | abilities.particle_barrier.cooldown_s.v5: 11→12 = nerf, matches declaration |
| F7_unmapped_vs_changes | zarya | no line is both mapped and unmapped |
| R1_full_cycle_dps_delta | zarya | particle_cannon: full-cycle body DPS 73.08 → 73.08 (+0.0%) |
| R1_full_cycle_dps_delta | zarya | particle_cannon_alt: full-cycle body DPS 40.00 → 40.00 (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | zarya | particle_cannon vs 175hp body: TTK 1.842s → 1.842s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | zarya | particle_cannon vs 250hp body: TTK 2.632s → 2.632s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | zarya | particle_cannon_alt vs 175hp body: TTK 3.000s → 3.000s (+0.0%) |
| R2_ttk_delta_or_reload_breakpoint | zarya | particle_cannon_alt vs 250hp body: TTK 5.500s → 5.500s (+0.0%) |
| R3_headshot_oneshot_change | zarya | particle_cannon: one-shot capability unchanged (False) |
| R3_headshot_oneshot_change | zarya | particle_cannon_alt: one-shot capability unchanged (False) |
| R4_change_count_stats | zarya | changes: {'buff': 0, 'nerf': 1, 'ambiguous': 0} (display only, no threshold) |
| R5_falloff_window_delta | zarya | no falloff weapons |
| R6_cooldown_step | zarya | particle_barrier[v5]: cooldown 11s → 12s (Δ1.00s, 9.1%) |
| R8_mixed_direction_rationale | zarya | single direction {'nerf'} |
| R9_shots_to_kill_breakpoint | zarya | particle_cannon_alt vs 175hp body: 4 → 4 shot events |
| R9_shots_to_kill_breakpoint | zarya | particle_cannon_alt vs 250hp body: 5 → 5 shot events |
