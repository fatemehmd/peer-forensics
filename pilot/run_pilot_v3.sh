#!/bin/bash
# pilot_v3, four folders, 15 fresh runs per cell, both debrief questions. Resumable.
#   pilot_v3_original    : original prompt, B and C                  (replication)
#   pilot_v3_strong      : strong prompt,   B and C                  (does an explicit "do not attempt or test" remove attempts?)
#   pilot_v3_harm_cheap  : original prompt, billing $0.50/page, B and C
#   pilot_v3_harm_costly : original prompt, billing $250/page,  B and C
cd "$(dirname "$0")"
M="qwen/qwen3.6-27b"; P="alibaba"
python3 harness.py --model $M --provider $P --prompt original --conditions B C               --n 15 --debrief --out results/pilot_v3_original
python3 harness.py --model $M --provider $P --prompt strong   --conditions B C               --n 15 --debrief --out results/pilot_v3_strong
python3 harness.py --model $M --provider $P --prompt original --conditions B_cheap C_cheap   --n 15 --debrief --out results/pilot_v3_harm_cheap
python3 harness.py --model $M --provider $P --prompt original --conditions B_costly C_costly --n 15 --debrief --out results/pilot_v3_harm_costly
echo ALL DONE
