#!/bin/bash
# Version-1 resampling: the six C cheaters, each continued 30x as C (same) and 30x as B (author line swapped).
# ~360 continuations + 360 debrief questions. Resumable: rerun to fill gaps.
cd "$(dirname "$0")"
for run in C__00 C__01 C__04 C__08 C__10 C__11; do
  python3 resample.py results/pilot_v2 $run --n 30 --out results/resample_v1
  python3 resample.py results/pilot_v2 $run --n 30 --swap-to B --out results/resample_v1
done
echo ALL DONE
