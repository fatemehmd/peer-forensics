#!/bin/bash
# human_v1 on the 122B via Novita (bf16), self-contained: agent vs human authorship, both compared within this provider.
cd "$(dirname "$0")"; M="qwen/qwen3.5-122b-a10b"; P="novita"
python3 harness.py --model $M --provider $P --prompt original --conditions C  CH  --n 15 --debrief --concurrency 4 --out results/human_v1_novita_original
python3 harness.py --model $M --provider $P --prompt firm     --conditions ME MEH --n 15 --debrief --concurrency 4 --out results/human_v1_novita_firm
echo ALL DONE
