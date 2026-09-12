#!/bin/bash
# pilot_v3, three arms, 15 fresh runs per cell, both debrief questions. Resumable.
#   pilot_v3_original : original prompt, B and C                       (replication)
#   pilot_v3_strong   : strong prompt,   B and C                       (does an explicit "do not attempt or test" remove attempts?)
#   pilot_v3_harm     : original prompt, B/C x cheap/costly billing    (does a harm cue in the note change attempts?)
cd "$(dirname "$0")"
M="qwen/qwen3.6-27b"; P="alibaba"
python3 harness.py --model $M --provider $P --prompt original --conditions B C --n 15 --debrief --out results/pilot_v3_original
python3 harness.py --model $M --provider $P --prompt strong   --conditions B C --n 15 --debrief --out results/pilot_v3_strong
python3 harness.py --model $M --provider $P --prompt original --conditions B_cheap C_cheap B_costly C_costly --n 15 --debrief --out results/pilot_v3_harm
echo ALL DONE
