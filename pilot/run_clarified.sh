#!/bin/bash
# clarified_v1: M vs MP with one factual sentence closing the "cached copies" reading; 50 per cell, both models, interviews, refill loop.
cd "$(dirname "$0")"
while pgrep -f run_naming.sh > /dev/null; do sleep 10; done
python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions MC MPC --n 50 --debrief --concurrency 8 --out results/clarified_v1       > ../logs/clarified_27b.txt  2>&1 &
python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions MC MPC --n 50 --debrief --concurrency 4 --out results/clarified_v1_q122b > ../logs/clarified_122b.txt 2>&1 &
wait
for pass in 1 2 3; do
  m27=$(python3 set_aside_failed.py results/clarified_v1 | awk '{print $NF}'); m122=$(python3 set_aside_failed.py results/clarified_v1_q122b | awk '{print $NF}')
  echo "pass $pass: set aside 27B=$m27 122B=$m122"; if [ "$m27" = "0" ] && [ "$m122" = "0" ]; then echo "REFILL COMPLETE"; break; fi; sleep 90
  [ "$m27" != "0" ]  && python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions MC MPC --n 50 --debrief --concurrency 4 --out results/clarified_v1
  [ "$m122" != "0" ] && python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions MC MPC --n 50 --debrief --concurrency 2 --out results/clarified_v1_q122b
done
echo ALL DONE
