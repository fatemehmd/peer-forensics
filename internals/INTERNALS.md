# Looking inside: runbook

Everything here is prepared from saved runs; nothing new is sampled. Prefixes are the exact messages the model saw
before its decision reply, per run, split by outcome (route / honest) within each cell.

## The three questions (from RESULTS_DIGEST.md, "Language before the decision")
1. **Pressure and "confusion".** 27B, cell MP vs M (same rule, same note; only the user paragraph differs). Cheaters write
   "this is a contradiction ... let me try anyway". At the last prefix token and along the decision reply, does the lens show a
   *rule-violation / not-allowed* representation while the text says "contradiction"? Compare MP route (12) vs MP honest (3)
   vs M honest (14).
2. **Cost that never reaches the text.** 122B, cells MHP and MHP_costly. Honest runs cite the charge; the 7 cheaters do not.
   Is a *cost / harm-to-person / unauthorized* representation present in the cheaters (suppressed) or absent (not attended)?
   Read at the positions of the billing line in the brief tool result and at the last prefix token.
3. **Where the pivot starts.** 27B MP: does an *urgency / incomplete-delivery* representation appear when the pressure
   paragraph is read, and does it precede the first "contradiction" sentence in the decision reply?

## Matched sets
`internals/prefixes/index.json` lists runs by model, cell and outcome. Best-balanced cells:
- 27B `pressure_v1__MHP` (7 route / 8 honest), `pilot_v3_original__B` (7/8), `pilot_v2__C` (6/9).
- 122B `excite_v1_q122b__ME` (8/7), `pilot_v2_q122b__C` (11/4), `pressure_v1_q122b__MP` (10/5).

## Qwen3.6-27B: hosted lens, no GPU
Neuronpedia hosts a J-Lens for this model: https://www.neuronpedia.org/qwen3.6-27b/jlens . Paste a rendered prefix
(`*.rendered.txt`), read the lens at the final assistant-prefix token and at the tokens of the billing line / pressure
paragraph. Do a route run and an honest run from the same cell back to back.
Caveat: `*.rendered.txt` is an approximate chat-template rendering. For exact positions, render with the tokenizer:
```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.6-27B")
rec = json.load(open("internals/prefixes/qwen3.6-27b/pressure_v1__MP/MP__00__route.json"))
text = tok.apply_chat_template(rec["messages_before_decision"], tokenize=False, add_generation_prompt=True)
```
(Tool-call messages need the OpenAI-style `tool_calls` field the transcript already stores.)

## Qwen3.5-122B-A10B: local lens
Pre-fitted lens weights: https://huggingface.co/neuronpedia/jacobian-lens (and camilablank/workspace-lenses). Model in fp8 needs
~2x80GB; bf16 ~4x80GB. Replay `messages_before_decision` with the model's own tokenizer, hook the residual stream at the
lens layer, apply the lens at the same positions as above. Same route-vs-honest comparison within cell.

## What would count as an answer
- Q1: violation-like readouts present in MP cheaters at the decision point at rates similar to honest runs → the "confusion"
  is narrative over a recognised violation. Absent → the pressure genuinely reframes the rule.
- Q2: cost readouts in 122B cheaters comparable to honest runs → suppression; near-zero → inattention.
- Q3: urgency readouts rising at the pressure paragraph and preceding the "contradiction" sentence → the pivot is driven by
  the completion signal, not the note.
Report per-cell rates with Wilson intervals, as elsewhere; the lens is a readout, not a causal test. Causal follow-up is
steering against the identified direction at the decision turn and re-measuring the route rate.
