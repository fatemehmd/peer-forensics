#!/bin/bash
# pressure_v1: firm rule for all; archived agent conversation in the brief; 2x2 harm x completion pressure.
# One folder, four conditions shuffled together, 15 fresh runs each, both debrief questions. Resumable.
cd "$(dirname "$0")"
python3 harness.py --model qwen/qwen3.6-27b --provider alibaba --prompt firm --conditions M MH MP MHP --n 15 --debrief --out results/pressure_v1
echo ALL DONE
