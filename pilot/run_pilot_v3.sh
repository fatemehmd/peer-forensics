#!/bin/bash
# pilot_v3: original vs strong prompt, conditions B and C, 15 fresh runs each, both debrief questions. Resumable.
cd "$(dirname "$0")"
M="qwen/qwen3.6-27b"; P="alibaba"
python3 harness.py --model $M --provider $P --prompt original --conditions B C --n 15 --debrief --out results/pilot_v3_original
python3 harness.py --model $M --provider $P --prompt strong   --conditions B C --n 15 --debrief --out results/pilot_v3_strong
echo ALL DONE
