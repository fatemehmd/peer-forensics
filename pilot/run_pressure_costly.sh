#!/bin/bash
# Follow-up: MHP_costly = firm rule + archived agent messages + $250 unauthorized billing + completion pressure.
# 15 fresh runs per model, both debrief questions, new folders. Resumable. Does not touch existing folders.
cd "$(dirname "$0")"
python3 harness.py --model qwen/qwen3.6-27b        --provider alibaba --prompt firm --conditions MHP_costly --n 15 --debrief --out results/pressure_costly_v1
python3 harness.py --model qwen/qwen3.5-122b-a10b  --provider alibaba --prompt firm --conditions MHP_costly --n 15 --debrief --out results/pressure_costly_v1_q122b
echo ALL DONE
