#!/bin/bash
# excite_v1: firm rule, NO completion pressure, excited + encouraging archived agent messages, with and without $0.50 unauthorized harm.
# Usage: ./run_excite.sh 27b | ./run_excite.sh 122b   (122B at low concurrency because the provider throttles)
cd "$(dirname "$0")"
case "$1" in
  27b)  python3 harness.py --model qwen/qwen3.6-27b       --provider alibaba --prompt firm --conditions ME MHE --n 15 --debrief --out results/excite_v1 ;;
  122b) python3 harness.py --model qwen/qwen3.5-122b-a10b --provider alibaba --prompt firm --conditions ME MHE --n 15 --debrief --concurrency 2 --out results/excite_v1_q122b ;;
  *) echo "usage: $0 27b|122b"; exit 2 ;;
esac
echo ALL DONE
