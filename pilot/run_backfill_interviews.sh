#!/bin/bash
# Backfill both interview questions into the existing replication folders. No new runs; run.json untouched; debrief.json added per run.
cd "$(dirname "$0")"
python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm     --conditions MP MHP MHP_costly --n 50 --debrief --concurrency 8 --out results/replication_v1       > ../logs/backfill_rep_27b.txt  2>&1 &
python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm     --conditions MP MHP MHP_costly --n 50 --debrief --concurrency 4 --out results/replication_v1_q122b > ../logs/backfill_rep_122b.txt 2>&1 &
python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt original --conditions B C CW           --n 50 --debrief --concurrency 8 --out results/attribution_v1       > ../logs/backfill_att_27b.txt  2>&1 &
python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt original --conditions B C CW           --n 50 --debrief --concurrency 4 --out results/attribution_v1_q122b > ../logs/backfill_att_122b.txt 2>&1 &
wait
for f in results/replication_v1 results/replication_v1_q122b results/attribution_v1 results/attribution_v1_q122b; do
  echo "$f: debriefs $(ls $f/*/debrief.json 2>/dev/null | wc -l | tr -d ' ') / runs $(ls -d $f/*__?? 2>/dev/null | wc -l | tr -d ' ')"
done
echo ALL DONE
