#!/bin/bash
# concealment_v2: MPL2, 15 per model (user's call), interviews, refill loop.
cd "$(dirname "$0")"
python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions MPL2 --n 15 --debrief --concurrency 8 --out results/concealment_v2       > ../logs/concealment2_27b.txt  2>&1 &
python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions MPL2 --n 15 --debrief --concurrency 4 --out results/concealment_v2_q122b > ../logs/concealment2_122b.txt 2>&1 &
wait
for pass in 1 2 3; do
  m27=$(python3 set_aside_failed.py results/concealment_v2 | awk '{print $NF}'); m122=$(python3 set_aside_failed.py results/concealment_v2_q122b | awk '{print $NF}')
  echo "pass $pass: set aside 27B=$m27 122B=$m122"; if [ "$m27" = "0" ] && [ "$m122" = "0" ]; then echo "REFILL COMPLETE"; break; fi; sleep 90
  [ "$m27" != "0" ]  && python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions MPL2 --n 15 --debrief --concurrency 4 --out results/concealment_v2
  [ "$m122" != "0" ] && python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions MPL2 --n 15 --debrief --concurrency 2 --out results/concealment_v2_q122b
done
echo ALL DONE
