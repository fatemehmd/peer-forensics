#!/bin/bash
# attribution_v1: original prompt, only the author line differs: B unsigned / C agents / CW coworkers. 50 fresh runs each,
# both models, Alibaba, interleaved within each model's batch, no debriefs. Then an automatic set-aside + refill loop.
cd "$(dirname "$0")"
python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt original --conditions B C CW --n 50 --concurrency 8 --out results/attribution_v1       > ../logs/attribution_27b.txt  2>&1 &
python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt original --conditions B C CW --n 50 --concurrency 4 --out results/attribution_v1_q122b > ../logs/attribution_122b.txt 2>&1 &
wait
for pass in 1 2 3 4; do
  m27=$(python3 set_aside_failed.py results/attribution_v1 | awk '{print $NF}'); m122=$(python3 set_aside_failed.py results/attribution_v1_q122b | awk '{print $NF}')
  echo "pass $pass: set aside 27B=$m27 122B=$m122"
  if [ "$m27" = "0" ] && [ "$m122" = "0" ]; then echo "REFILL COMPLETE"; break; fi
  sleep 90
  [ "$m27" != "0" ]  && python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt original --conditions B C CW --n 50 --concurrency 4 --out results/attribution_v1
  [ "$m122" != "0" ] && python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt original --conditions B C CW --n 50 --concurrency 2 --out results/attribution_v1_q122b
done
echo ALL DONE
