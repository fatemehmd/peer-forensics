#!/bin/bash
# replication_v1: MP / MHP / MHP_costly, 50 fresh runs each, both models, interleaved (harness shuffles across conditions),
# no debriefs, prompts frozen (manifest guard refuses any change). 27B and 122B run in parallel as separate processes.
cd "$(dirname "$0")"
python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions MP MHP MHP_costly --n 50 --concurrency 8 --out results/replication_v1       > ../logs/replication_27b.txt  2>&1 &
python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions MP MHP MHP_costly --n 50 --concurrency 4 --out results/replication_v1_q122b > ../logs/replication_122b.txt 2>&1 &
wait
echo ALL DONE
