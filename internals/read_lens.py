"""Read a J-lens / R-lens / template lens over a saved decision-turn prefix. GPU required (27B bf16 fits one 80GB card).
Not run in this session; prepared for the post-write-up internals pass.

Usage:
  python read_lens.py --model Qwen/Qwen3.6-27B --lens workspace-lenses/qwen3.6-27b/r-lens/lens.pt \
      --prefix prefixes/qwen3.6-27b/pressure_v1__MP/MP__00__route.json --positions last,billing,pressure --topk 12
  # add --templates workspace-lenses/qwen3.6-27b/template-lens/templates+phrases_v3.safetensors --words .../template_words+phrases_v3.txt
Outputs a JSON next to the prefix: per requested position, per layer, top-k vocabulary readouts (J-lens) and
top-k template phrases (template lens), so route vs honest runs in a cell can be compared offline.

Lens math (from the workspace-lenses README): readout_l = softmax(W_U · norm(J_l · h_l)); template score = cos(h_l, T_l[row]).
"""
import argparse, json, os, torch

PROBE_STRINGS = {  # substrings whose token positions we want to read; found in the rendered chat text
    "billing":  "personal credit card",
    "pressure": "recorded as an incomplete delivery",
    "rule":     "Do not attempt, test, or work around",
    "peers":    "cache remote-fetch worked",
}
CONCEPTS = ["not allowed", "forbidden", "violation", "policy", "rule", "unauthorized", "cost", "charge", "credit card", "harm",
            "employee", "incomplete", "urgent", "must complete", "contradiction", "confusing", "workaround", "try", "test", "risk", "permission"]

def find_positions(tok, text, names):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False)
    pos = {}
    if "last" in names: pos["last"] = len(enc["input_ids"]) - 1
    for name in names:
        s = PROBE_STRINGS.get(name)
        if not s: continue
        i = text.find(s)
        if i < 0: continue
        j = i + len(s)
        pos[name] = max(k for k, (a, b) in enumerate(enc["offset_mapping"]) if a < j)   # last token of the phrase
    return enc["input_ids"], pos

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--lens", required=True); ap.add_argument("--prefix", required=True)
    ap.add_argument("--positions", default="last,billing,pressure,rule,peers"); ap.add_argument("--topk", type=int, default=12)
    ap.add_argument("--templates", default=None); ap.add_argument("--words", default=None); ap.add_argument("--dtype", default="bfloat16")
    a = ap.parse_args()
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=getattr(torch, a.dtype), device_map="auto")
    rec = json.load(open(a.prefix))
    text = tok.apply_chat_template(rec["messages_before_decision"], tokenize=False, add_generation_prompt=True)
    ids, pos = find_positions(tok, text, a.positions.split(","))
    input_ids = torch.tensor([ids], device=model.device)
    with torch.no_grad():
        out = model(input_ids, output_hidden_states=True)
    hs = out.hidden_states                     # tuple: embeddings + one per layer, each [1, T, d]
    lens = torch.load(a.lens, map_location="cpu", weights_only=False)
    J, src_layers = lens["J"], list(lens["source_layers"])    # J[i] maps layer src_layers[i] -> target layer
    W_U = model.get_output_embeddings().weight.float().cpu()    # [V, d]
    final_norm = model.model.norm if hasattr(model.model, "norm") else None
    result = dict(prefix=a.prefix, outcome=rec["outcome"], cell=f"{rec['folder']}__{rec['condition']}", positions=pos, jlens={}, template={})
    for name, p in pos.items():
        per_layer = {}
        for i, l in enumerate(src_layers):
            h = hs[l + 1][0, p].float().cpu()               # residual after layer l at position p
            v = J[i].float() @ h if J[i].ndim == 2 else h
            if final_norm is not None:
                v = final_norm(v.to(model.device, dtype=next(final_norm.parameters()).dtype)).float().cpu()
            logits = W_U @ v; top = torch.topk(logits, a.topk)
            per_layer[str(l)] = [(tok.decode([int(t)]), round(float(s), 2)) for s, t in zip(top.values, top.indices)]
        result["jlens"][name] = per_layer
    if a.templates:
        from safetensors import safe_open
        with safe_open(a.templates, framework="pt") as f:
            T = f.get_tensor("templates")                     # [L, R, d] bf16
        words = [ln.rstrip("\n").split("\t", 1)[1] for ln in open(a.words)]
        want = [r for r, w in enumerate(words) if any(c == w.lower() for c in CONCEPTS)]
        for name, p in pos.items():
            per_layer = {}
            for l in range(T.shape[0]):
                h = hs[l + 1][0, p].float().cpu(); Tl = T[l].float()
                cos = torch.nn.functional.cosine_similarity(Tl, h[None, :], dim=1)
                top = torch.topk(cos, a.topk)
                per_layer[str(l)] = dict(top=[(words[int(r)], round(float(s), 3)) for s, r in zip(top.values, top.indices)],
                                         concepts={words[r]: round(float(cos[r]), 3) for r in want})
            result["template"][name] = per_layer
    outp = a.prefix.replace(".json", ".lens.json"); json.dump(result, open(outp, "w"), indent=1)
    print("wrote", outp, "| positions:", pos)

if __name__ == "__main__": main()
