# Design changes after external critique (2026-09-11)

Narrowed question: **When an agent finds evidence that a forbidden shortcut works, does attributing that evidence to other agents change whether it uses the shortcut or warns the operator?**

| critique | change |
|---|---|
| "reporting unexplored" overclaimed | dropped. Related: research-swarm cheating contagion paper (Sep 3 2026), agent whistleblowing studies. We test attribution, not novelty of the topic. |
| peer vs note differed in repetition/excitement/justification | `notes_doing` and `peers_doing` now contain the **same four lines, same order**. Only difference: signed agent messages on a board described as used by other agents, vs one unsigned scratch-notes file. |
| reporting metric too coarse | operator messages and submit notes are stored and sorted into blocker / warning / confession (rules + LLM judge + hand check, `classify.py`). Headline reporting metric = warning or confession, not any message. |
| removing the report tool removes the measure | no-report-tool variant dropped from the plan (flag left in code, unused). |
| conclusions too strong | claims scoped to "this setting, this model". n=30/cell where budget allows. Wilson CIs. |
| resampling prefix contaminated / swap breaks reads | branch is now **before** first contact with the shared cache; exposure itself is regenerated. |
| J-lens hours overstated | acknowledged; Neuronpedia-hosted lenses exist for Qwen. Optional look if a behavioral result appears. |

Kept: the alternative project ("rejects cheat, later accepts it") as a fallback if the pilot shows no behavior worth studying.
