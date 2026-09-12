#!/bin/bash
# After run_replication.sh finishes: up to 4 passes of set-aside-failed + rerun, low concurrency, 90s pause between passes.
cd "$(dirname "$0")"
while pgrep -f run_replication.sh > /dev/null; do sleep 15; done
for pass in 1 2 3 4; do
  m27=$(python3 set_aside_failed.py results/replication_v1 | awk '{print $NF}')
  m122=$(python3 set_aside_failed.py results/replication_v1_q122b | awk '{print $NF}')
  echo "pass $pass: set aside 27B=$m27 122B=$m122"
  if [ "$m27" = "0" ] && [ "$m122" = "0" ]; then echo "REFILL COMPLETE"; exit 0; fi
  sleep 90
  [ "$m27" != "0" ]  && python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions MP MHP MHP_costly --n 50 --concurrency 4 --out results/replication_v1
  [ "$m122" != "0" ] && python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions MP MHP MHP_costly --n 50 --concurrency 2 --out results/replication_v1_q122b
done
echo "REFILL PASSES EXHAUSTED"
