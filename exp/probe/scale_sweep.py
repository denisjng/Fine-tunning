# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["torch", "transformers>=4.57", "peft", "accelerate", "safetensors", "flash-linear-attention", "sacrebleu"]
# ///
"""Compromis traduction / sécurité en réduisant l'effet du LoRA (facteur s sur lora_alpha, équivalent à lora_B × s).
Pour chaque s : refus sur les demandes dangereuses de safety_probe.py + chrF++ (score Space) sur 150 phrases de val.
Usage : ... scale_sweep.py /lora/<run>/lora   (val et metric dans /work)"""
import json, sys, torch
sys.path.insert(0, "/work")
from metric import score
from verifier_mon_lora import gabarit
from safety_probe_lists import HARM, REFUS  # noqa: E402
from peft import PeftModel
from peft.tuners.lora import LoraLayer
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "Qwen/Qwen3.5-0.8B"
tok = AutoTokenizer.from_pretrained(BASE); tok.padding_side = "left"
model = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16).cuda(), sys.argv[1]).eval()
layers = [m for m in model.modules() if isinstance(m, LoraLayer)]
base_scaling = [dict(m.scaling) for m in layers]
val = [json.loads(l) for l in open("/work/val.jsonl", encoding="utf-8")]
val = [r for lg in ("br", "oc", "ca") for r in [v for v in val if v["lang"] == lg][:50]]   # 50 par langue


@torch.inference_mode()
def gen(prompts, n):
    out = []
    for i in range(0, len(prompts), 16):
        t = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True) for p in prompts[i:i + 16]]
        e = tok(t, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        o = model.generate(**e, max_new_tokens=n, do_sample=False, pad_token_id=tok.pad_token_id or tok.eos_token_id)
        out += [tok.decode(x[e["input_ids"].shape[1]:], skip_special_tokens=True).strip() for x in o]
    return out


print("s | refus /12 | score val | br | oc | ca")
for s in (1.0, 0.75, 0.6, 0.5, 0.4, 0.3, 0.0):
    for m, b in zip(layers, base_scaling):
        for k in b: m.scaling[k] = b[k] * s
    ref = sum(bool(REFUS.search(a)) for a in gen(HARM, 120))
    sc = score(gen([gabarit(r["lang"], r["fr"]) for r in val], 160), [r["x"] for r in val], [r["lang"] for r in val])
    print(f"SWEEP s={s} refus={ref}/12 score={sc['score']} br={sc['br']['chrf']} oc={sc['oc']['chrf']} ca={sc['ca']['chrf']}", flush=True)
