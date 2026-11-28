# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["torch", "transformers>=4.57", "peft", "accelerate", "safetensors", "flash-linear-attention", "huggingface_hub"]
# ///
"""Étape F (data_strategy.md) : note chaque paire officielle de train_v2 avec base + LoRA (dual conditional cross-entropy,
Junczys-Dowmunt 2018). Perte moyenne par token de la traduction, sens fr->X et X->fr. Aucun texte généré : on ne fait que
noter des paires existantes. Sortie : /tmp/pair_scores.jsonl poussé sur denisjng/hackathon-work.
Usage : ... score_pairs.py /lora/<run>/lora"""
import json, sys, torch
sys.path.insert(0, "/work")
from verifier_mon_lora import gabarit
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "Qwen/Qwen3.5-0.8B"
DE = {"br": ("du breton", "Breton"), "oc": ("de l'occitan", "Occitan"), "ca": ("du catalan", "Catalan")}
tok = AutoTokenizer.from_pretrained(BASE)
model = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16).cuda(), sys.argv[1]).eval()
rows = [json.loads(l) for l in open("/work/train_v2.jsonl", encoding="utf-8")]
chat = lambda p: tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True)
x2fr = lambda lg, x: f"Traduisez fidèlement {DE[lg][0]} vers le français. Répondez uniquement par la traduction.\n{DE[lg][1]} : {x}\nFrançais :"


@torch.inference_mode()
def nll(pairs):
    """pairs = [(prompt, cible)] -> perte moyenne par token de la cible (+ <|im_end|>)."""
    ex = []
    for p, c in pairs:
        a = tok(chat(p), add_special_tokens=False)["input_ids"]; b = tok(c + tok.eos_token, add_special_tokens=False)["input_ids"]
        ex.append(((a + b)[:384], len(a)))
    L = max(len(e[0]) for e in ex)
    ids = torch.tensor([e[0] + [tok.pad_token_id] * (L - len(e[0])) for e in ex]).cuda()
    att = (torch.arange(L)[None] < torch.tensor([len(e[0]) for e in ex])[:, None]).cuda()
    logp = torch.log_softmax(model(input_ids=ids, attention_mask=att).logits[:, :-1].float(), -1)
    tgt = ids[:, 1:]
    lp = logp.gather(-1, tgt[..., None])[..., 0]
    out = []
    for i, (e, n) in enumerate(ex):
        s, t = n - 1, len(e) - 1   # positions qui prédisent la cible
        out.append(-lp[i, s:t].mean().item())
    return out


order = sorted(range(len(rows)), key=lambda i: len(rows[i]["fr"]) + len(rows[i]["x"]))   # lots de longueurs proches
res = [None] * len(rows)
B = 64
for k in range(0, len(order), B):
    idx = order[k:k + B]
    f = nll([(gabarit(rows[i]["lang"], rows[i]["fr"]), rows[i]["x"]) for i in idx])
    b = nll([(x2fr(rows[i]["lang"], rows[i]["x"]), rows[i]["fr"]) for i in idx])
    for i, a, c in zip(idx, f, b):
        res[i] = (a, c)
    if k % (B * 200) == 0:
        print(f"{k}/{len(rows)}", flush=True)
with open("/tmp/pair_scores.jsonl", "w", encoding="utf-8") as fo:
    for r, (a, c) in zip(rows, res):
        fo.write(json.dumps({"lang": r["lang"], "source": r["source"], "fr": r["fr"], "x": r["x"], "nll_fx": round(a, 4), "nll_xf": round(c, 4)}, ensure_ascii=False) + "\n")
from huggingface_hub import HfApi
HfApi().upload_file(path_or_fileobj="/tmp/pair_scores.jsonl", path_in_repo="pair_scores.jsonl", repo_id="denisjng/hackathon-work",
                    repo_type="dataset", commit_message=f"étape F : scores par paire avec {sys.argv[1]}")
print("SCORES_DONE", len(rows))
