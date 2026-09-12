#!/bin/bash
# Second model: Qwen3.5-122B-A10B (open J-lens available), Alibaba endpoint, same settings.
#   smoke check, then the original experiment (A/B/C, original prompt), then pressure_v1 (M/MH/MP/MHP, firm prompt).
# 15 fresh runs per condition, both debrief questions. Resumable.
cd "$(dirname "$0")"
M="qwen/qwen3.5-122b-a10b"; P="alibaba"
python3 harness.py --model $M --provider $P --condition smoke_local --n 1 --out results/smoke_q122b
python3 harness.py --model $M --provider $P --prompt original --conditions A B C       --n 15 --debrief --out results/pilot_v2_q122b
python3 harness.py --model $M --provider $P --prompt firm     --conditions M MH MP MHP --n 15 --debrief --out results/pressure_v1_q122b
echo ALL DONE
