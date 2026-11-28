# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["torch", "transformers>=4.57", "peft", "accelerate", "safetensors", "huggingface_hub", "sacrebleu", "flash-linear-attention"]
# ///
"""LoRA Qwen/Qwen3.5-0.8B, traduction FR<->br/oc/ca. Respecte le kit : base officielle, LoRA seul, pas de modules_to_save,
safetensors, push privé sur le compte perso. Entrées dans /work (dataset privé monté) : sft_*.jsonl, val.jsonl, metric.py.

Réglages par variables d'env : DATA, MAX_EX (0 = tout), EPOCHS, LR, RANK, BS, GA, RUN, PUSH (repo privé, vide = pas de push).
Imprime EPOCH_SCORE=<epoch>,<score> et VAL_SCORE=<score> (score = moyenne des gains normalisés du Space).
"""
import json, math, os, sys, time
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

sys.path.insert(0, "/work")
from metric import score  # noqa: E402
from verifier_mon_lora import gabarit  # noqa: E402  gabarit exact du bench

E = lambda k, d: type(d)(os.environ.get(k, d))
BASE, DATA, MAX_EX, EPOCHS, LR = "Qwen/Qwen3.5-0.8B", E("DATA", "/work/sft_v2.jsonl"), E("MAX_EX", 0), E("EPOCHS", 1), E("LR", 2e-4)
R, BS, GA, RUN, PUSH, MAXLEN = E("RANK", 16), E("BS", 8), E("GA", 4), E("RUN", "001"), E("PUSH", ""), 384
EVAL_N = E("EVAL_N", 0)   # 0 = toute la val (900) ; petit nombre pour les tests rapides
TARGET = E("TARGET", "all-linear")   # ou liste "q_proj,k_proj,..." (LoRA plus léger = moins de perte de sécurité)
LANG = {"br": ("le breton", "Breton"), "oc": ("l'occitan", "Occitan"), "ca": ("le catalan", "Catalan")}
torch.manual_seed(42)
print("config", dict(GPU=torch.cuda.get_device_name(0), GC=E("GC", 1), TARGET=TARGET, DATA=DATA, MAX_EX=MAX_EX, EPOCHS=EPOCHS, LR=LR, R=R, BS=BS, GA=GA, RUN=RUN), flush=True)

tok = AutoTokenizer.from_pretrained(BASE)
tok.pad_token = tok.pad_token or tok.eos_token
model = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16, attn_implementation="sdpa").cuda()
model = get_peft_model(model, LoraConfig(r=R, lora_alpha=2 * R, lora_dropout=0.05, target_modules=TARGET if TARGET == "all-linear" else TARGET.split(","), task_type="CAUSAL_LM"))
if E("GC", 1):   # utile sur L4 24 Go (OOM à BS 16 sans) ; GC=0 sur H200 141 Go, plus rapide
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
model.print_trainable_parameters()


def prompt_ids(p):
    # gabarit du bench : rôle user seul, prompt de génération de la base (finit par "<think>\n\n</think>\n\n")
    return tok(tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True),
               add_special_tokens=False)["input_ids"]


rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
for _r in [r for r in rows if r["dir"] == "fr2x"][:50]:   # le prompt fr->X doit être exactement celui du bench
    _fr = _r["prompt"].split("Français : ", 1)[1].rsplit(chr(10), 1)[0]
    assert _r["prompt"] == gabarit(_r["lang"], _fr), f"gabarit d'entraînement ≠ bench : {_r['prompt']!r}"
rows = rows[:MAX_EX] if MAX_EX else rows
ex = []
for r in rows:
    p, c = prompt_ids(r["prompt"]), tok(r["completion"] + tok.eos_token, add_special_tokens=False)["input_ids"]
    if len(p) + len(c) <= MAXLEN:
        ex.append((p + c, [-100] * len(p) + c))   # perte sur la traduction + <|im_end|> seulement
print("exemples", len(ex), "sur", len(rows), flush=True)

val = [json.loads(l) for l in open("/work/val.jsonl", encoding="utf-8")]


@torch.inference_mode()
def evaluate(n=None):
    model.eval(); tok.padding_side = "left"
    v = val[:n] if n else val
    hyps = []
    for i in range(0, len(v), 64):
        b = v[i:i + 64]
        texts = [tok.apply_chat_template([{"role": "user", "content":
                 f"Traduisez fidèlement du français vers {LANG[r['lang']][0]}. Répondez uniquement par la traduction.\nFrançais : {r['fr']}\n{LANG[r['lang']][1]} :"}],
                 tokenize=False, add_generation_prompt=True) for r in b]
        enc = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        out = model.generate(**enc, max_new_tokens=160, do_sample=False, use_cache=True, pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id)
        hyps += [tok.decode(o[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip() for o in out]
    s = score(hyps, [r["x"] for r in v], [r["lang"] for r in v])
    think = sum("<think>" in h or "</think>" in h for h in hyps)
    model.train(); tok.padding_side = "right"
    return s, hyps, think


@torch.inference_mode()
def padding_check(n=16):
    """Traductions en lot (padding à gauche) vs une par une : doivent être identiques sur une archi récurrente."""
    model.eval(); tok.padding_side = "left"
    texts = [tok.apply_chat_template([{"role": "user", "content": gabarit(r["lang"], r["fr"])}], tokenize=False, add_generation_prompt=True) for r in val[:n]]
    gen = lambda enc: model.generate(**enc, max_new_tokens=60, do_sample=False, use_cache=True, pad_token_id=tok.pad_token_id)
    enc = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
    lot = [tok.decode(o[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip() for o in gen(enc)]
    seul = []
    for t in texts:
        e = tok([t], return_tensors="pt", add_special_tokens=False).to("cuda")
        seul.append(tok.decode(gen(e)[0][e["input_ids"].shape[1]:], skip_special_tokens=True).strip())
    model.train(); tok.padding_side = "right"
    return sum(a != b for a, b in zip(lot, seul))


@torch.inference_mode()
def fr_drift():
    """NLL moyenne sur 300 phrases FR de la val, texte brut : dérive du français (oubli), adapter actif vs désactivé."""
    model.eval()
    def nll():
        tot = 0.0
        for r in val[:300]:
            ids = tok(r["fr"], return_tensors="pt").input_ids.cuda()
            tot += model(input_ids=ids, labels=ids).loss.item()
        return tot / 300
    with_a = nll()
    with model.disable_adapter():
        base = nll()
    model.train()
    return round(base, 4), round(with_a, 4)


ex.sort(key=lambda e: len(e[0]))   # paquets de longueurs proches (moins de padding), mélangés ensuite
batches = [ex[i:i + BS] for i in range(0, len(ex), BS)]
steps = math.ceil(len(batches) * EPOCHS / GA)
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.0)
sched = get_cosine_schedule_with_warmup(opt, int(0.03 * steps), steps)
g = torch.Generator().manual_seed(42)
best, t0, step = -1e9, time.time(), 0
model.train()
for ep in range(EPOCHS):
    order = torch.randperm(len(batches), generator=g).tolist()
    for k, bi in enumerate(order):
        b = batches[bi]
        L = max(len(e[0]) for e in b)
        ids = torch.tensor([e[0] + [tok.pad_token_id] * (L - len(e[0])) for e in b]).cuda()
        lab = torch.tensor([e[1] + [-100] * (L - len(e[1])) for e in b]).cuda()
        att = (torch.arange(L)[None, :] < torch.tensor([len(e[0]) for e in b])[:, None]).cuda()
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss / GA
        loss.backward()
        if (k + 1) % GA == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad(); step += 1
            if step % 20 == 0:
                el = time.time() - t0
                print(f"step {step}/{steps} loss {loss.item() * GA:.3f} {el / step:.2f}s/step ETA {(steps - step) * el / step / 60:.0f} min", flush=True)
    if len(order) % GA:   # reste de l'époque : un dernier pas plutôt que des gradients perdus
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step(); opt.zero_grad(); step += 1
    s, hyps, think = evaluate(EVAL_N)
    print(f"EPOCH_SCORE={ep + 1},{s['score']}", json.dumps(s), "think_tags", think, flush=True)
    if s["score"] > best:
        best = s["score"]
        model.save_pretrained("out/lora", safe_serialization=True)
        with open("out/val_hyps.jsonl", "w", encoding="utf-8") as f:
            f.writelines(json.dumps({"lang": r["lang"], "fr": r["fr"], "ref": r["x"], "hyp": h, "source": r["source"]}, ensure_ascii=False) + "\n"
                         for r, h in zip(val, hyps))

print("padding_check : sorties différentes lot/seul sur 16 =", padding_check(), flush=True)
print("fr_drift (base, lora)", fr_drift(), flush=True)
cfg = json.load(open("out/lora/adapter_config.json"))
assert cfg["base_model_name_or_path"] == BASE and not cfg.get("modules_to_save"), cfg
print("adapter Mo", round(os.path.getsize("out/lora/adapter_model.safetensors") / 1e6, 1))
if PUSH:
    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(PUSH, private=True, exist_ok=True)   # compte perso, privé (kit)
    api.upload_folder(folder_path="out", repo_id=PUSH, path_in_repo=RUN, commit_message=f"run {RUN} val {best}")
    print("pushed", PUSH, RUN, flush=True)
print(f"VAL_SCORE={best}")
