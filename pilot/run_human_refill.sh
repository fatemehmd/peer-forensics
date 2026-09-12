#!/bin/bash
cd "$(dirname "$0")"; M="qwen/qwen3.5-122b-a10b"; P="alibaba"
sleep 900
python3 harness.py --model $M --provider $P --prompt original --conditions CH  --n 15 --debrief --concurrency 1 --out results/human_v1_q122b_original
python3 harness.py --model $M --provider $P --prompt firm     --conditions MEH --n 15 --debrief --concurrency 1 --out results/human_v1_q122b_firm
echo ALL DONE
