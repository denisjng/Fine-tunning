# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#     "torch",
#     "transformers>=4.57",
#     "peft",
#     "accelerate",
#     "safetensors",
# ]
# ///
"""Vérifie ton LoRA AVANT de le déposer sur le Space du hackathon.

    uv run verifier_mon_lora.py mon_dossier_lora/            # contrôles + test de chargement et de traduction
    uv run verifier_mon_lora.py mon_dossier_lora/ --rapide   # contrôles seulement (quelques secondes, sans GPU)

(sans uv : pip install torch "transformers>=4.57" peft accelerate safetensors, puis python verifier_mon_lora.py ...)

1. Les mêmes contrôles que le Space au dépôt (base, fichiers, poids LoRA seulement, taille, types).
2. Le chargement exact du bench : Qwen/Qwen3.5-0.8B officiel + ton adapter via PeftModel, puis 3 traductions
   avec le gabarit du bench. Si ça passe ici, ça passe sur le bench.
Rien n'est envoyé nulle part. Le modèle de base (~1,6 Go) est téléchargé depuis Hugging Face la première fois.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

# --- Contrôles du dépôt : identiques à plateforme_bench/space/verification.py (garder synchronisés) ---
BASE_ATTENDUE = "Qwen/Qwen3.5-0.8B"
TAILLE_MAX_MO = 200
FICHIERS = ("adapter_config.json", "adapter_model.safetensors")
DTYPES_OK = {"F32", "F16", "BF16"}

# --- Gabarit de traduction : identique à pipeline/bench_officiel/bench_rapide.py (CANON) ---
LANGUES = {"br": ("le breton", "Breton"), "oc": ("l'occitan", "Occitan"), "ca": ("le catalan", "Catalan")}
PHRASES = ["Le marché ouvre tous les samedis matin sur la place de l'église.",
           "Nous avons pris le train pour rendre visite à ma grand-mère.",
           "Il faut fermer la fenêtre, le vent est très froid ce soir."]

OK, KO, ATT = "  [OK]  ", "  [REFUS]", "  [!]   "


def gabarit(code: str, phrase: str) -> str:
    article, nom = LANGUES[code]
    return f"Traduisez fidèlement du français vers {article}. Répondez uniquement par la traduction.\nFrançais : {phrase}\n{nom} :"


class Refus(Exception):
    pass


def lire_entete_safetensors(chemin: Path) -> dict:
    with open(chemin, "rb") as f:
        brut = f.read(8)
        if len(brut) != 8:
            raise Refus("adapter_model.safetensors est vide ou coupé.")
        n = struct.unpack("<Q", brut)[0]
        if not 2 <= n <= 50_000_000:
            raise Refus("adapter_model.safetensors n'est pas un fichier safetensors valide.")
        try:
            return json.loads(f.read(n))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise Refus("adapter_model.safetensors n'est pas un fichier safetensors valide.") from None


def controles(dossier: Path) -> dict:
    """Les contrôles du Space, avec un message par problème. Lève Refus au premier blocage."""
    if not dossier.is_dir():
        raise Refus(f"{dossier} n'est pas un dossier. Donne le dossier produit par model.save_pretrained(...).")
    presents = {p.name for p in dossier.iterdir()}
    if "adapter_model.bin" in presents and "adapter_model.safetensors" not in presents:
        raise Refus("Format .bin (pickle) refusé. Sauvegarde avec model.save_pretrained(dossier, safe_serialization=True).")
    if "model.safetensors" in presents or any(n.startswith("model-0") for n in presents):
        raise Refus("Ce dossier contient un modèle COMPLET (fusionné). Il faut l'adapter seul : model.save_pretrained(...) "
                    "et non save_pretrained_merged / merge_and_unload.")
    manquants = [f for f in FICHIERS if f not in presents]
    if manquants:
        raise Refus(f"Fichier(s) manquant(s) : {', '.join(manquants)}. Le dépôt = exactement ces deux fichiers.")
    config, poids = dossier / FICHIERS[0], dossier / FICHIERS[1]

    taille_mo = (config.stat().st_size + poids.stat().st_size) / 1e6
    if taille_mo > TAILLE_MAX_MO:
        raise Refus(f"LoRA trop gros : {taille_mo:.0f} Mo (maximum {TAILLE_MAX_MO} Mo). Baisse le rang r.")
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise Refus("adapter_config.json n'est pas un JSON lisible.") from None
    if str(cfg.get("peft_type", "")).upper() != "LORA":
        raise Refus(f"Il faut un LoRA (peft_type = LORA), reçu : {cfg.get('peft_type')!r}.")
    base = cfg.get("base_model_name_or_path")
    if base != BASE_ATTENDUE:
        conseil = ""
        if isinstance(base, str) and "qwen3.5-0.8b" in base.lower():
            conseil = (" C'est sûrement la copie Unsloth ou une version 4 bits du même modèle : si tu as bien entraîné sur "
                       f"Qwen3.5-0.8B, remplace simplement la valeur par \"{BASE_ATTENDUE}\".")
        raise Refus(f"Modèle de base attendu : {BASE_ATTENDUE}. Reçu : {base!r}. "
                    f"Corrige base_model_name_or_path dans adapter_config.json.{conseil}")
    if cfg.get("modules_to_save"):
        raise Refus("modules_to_save est interdit (embed_tokens, lm_head…) : seuls les poids LoRA sont acceptés. "
                    "Retire-le de la config d'entraînement et n'ajoute pas de tokens au tokenizer.")

    entete = lire_entete_safetensors(poids)
    entete.pop("__metadata__", None)
    if not entete:
        raise Refus("adapter_model.safetensors ne contient aucun tenseur.")
    hors_lora = [k for k in entete if "lora_" not in k]
    if hors_lora:
        raise Refus(f"Poids non LoRA trouvés ({len(hors_lora)}, ex. {hors_lora[0]}). Seuls les poids lora_A / lora_B sont acceptés.")
    dtypes = {v.get("dtype") for v in entete.values()}
    if not dtypes <= DTYPES_OK:
        raise Refus(f"Types de tenseurs non acceptés : {sorted(dtypes - DTYPES_OK)} (attendu : bf16, fp16 ou fp32).")
    params = 0
    for v in entete.values():
        n = 1
        for d in v.get("shape", []):
            n *= d
        params += n

    autres = sorted(n for n in presents - set(FICHIERS) if not n.startswith("."))   # .cache de hf download : ignoré
    return {"cfg": cfg, "rang": cfg.get("r"), "alpha": cfg.get("lora_alpha"),
            "modules": sorted(cfg.get("target_modules") or []) if isinstance(cfg.get("target_modules"), list)
            else cfg.get("target_modules"), "tenseurs": len(entete), "parametres": params,
            "taille_mo": round(taille_mo, 1), "autres": autres}


def test_reel(dossier: Path) -> bool:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if torch.cuda.is_available():
        device, dtype = "cuda", torch.bfloat16
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device, dtype = "mps", torch.float32
    else:
        device, dtype = "cpu", torch.float32
    print(f"\n2. Chargement comme sur le bench ({device}) : base {BASE_ATTENDUE} + ton adapter")
    tok = AutoTokenizer.from_pretrained(BASE_ATTENDUE)   # le tokenizer de la BASE : le tien est ignoré
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(BASE_ATTENDUE, dtype=dtype).to(device)
    try:
        model = PeftModel.from_pretrained(model, str(dossier))
    except Exception as e:  # noqa: BLE001 — on veut afficher la cause, quelle qu'elle soit
        print(f"{KO} PeftModel.from_pretrained a échoué : {type(e).__name__}: {e}")
        print("        Causes fréquentes : adapter entraîné sur un autre modèle (tailles différentes), "
              "target_modules absents de Qwen3.5-0.8B, version de peft très différente.")
        return False
    model.eval()
    print(f"{OK} adapter chargé par PeftModel (la même ligne que le bench)")

    # L'adapter change-t-il quelque chose ? (lora_B à zéro = adapter jamais entraîné)
    texte = tok.apply_chat_template([{"role": "user", "content": gabarit("br", PHRASES[0])}],
                                    tokenize=False, add_generation_prompt=True)
    enc = tok([texte], return_tensors="pt", add_special_tokens=False).to(device)
    with torch.inference_mode():
        avec = model(**enc, logits_to_keep=1).logits[:, -1, :].float()
        with model.disable_adapter():
            sans = model(**enc, logits_to_keep=1).logits[:, -1, :].float()
    ecart = (avec - sans).abs().max().item()
    if ecart < 1e-4:
        print(f"{ATT} l'adapter ne change rien aux sorties (écart {ecart:.1e}) : il est vide ou pas entraîné.")
    else:
        print(f"{OK} l'adapter modifie bien le modèle (écart max des logits {ecart:.2f})")

    print("\n3. Traductions avec le gabarit exact du bench (message utilisateur seul, chat template de la base) :")
    bon = True
    for code, phrase in zip(LANGUES, PHRASES):
        texte = tok.apply_chat_template([{"role": "user", "content": gabarit(code, phrase)}],
                                        tokenize=False, add_generation_prompt=True)
        enc = tok([texte], return_tensors="pt", add_special_tokens=False).to(device)
        with torch.inference_mode():
            out = model.generate(**enc, max_new_tokens=160, do_sample=False, use_cache=True,
                                 pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id)
        g = out[0][enc["input_ids"].shape[1]:].tolist()
        rep = tok.decode(g, skip_special_tokens=True).strip()
        fin = tok.eos_token_id in g
        print(f"   [{code}] {phrase}\n        → {rep or '(vide)'}")
        if not rep:
            print(f"{ATT} réponse vide.")
            bon = False
        if not fin:
            print(f"{ATT} pas de fin de réponse en 160 tokens : le modèle ne s'arrête pas (vérifie le token de fin "
                  "dans tes données d'entraînement).")
        if "<think>" in rep or "</think>" in rep:
            print(f"{ATT} balises de réflexion dans la réponse : elles comptent comme du texte et font baisser le score.")
    return bon


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dossier", type=Path, help="dossier de l'adapter (adapter_config.json + adapter_model.safetensors)")
    p.add_argument("--rapide", action="store_true", help="contrôles du dépôt seulement, sans charger le modèle")
    args = p.parse_args()

    print(f"1. Contrôles du dépôt (les mêmes que le Space) : {args.dossier}")
    try:
        r = controles(args.dossier)
    except Refus as e:
        print(f"{KO} {e}\n\nRÉSULTAT : le Space refuserait ce LoRA.")
        sys.exit(1)
    print(f"{OK} base {BASE_ATTENDUE}, poids LoRA seulement, safetensors, {r['taille_mo']} Mo")
    print(f"        rang {r['rang']}, alpha {r['alpha']}, {r['tenseurs']} tenseurs, "
          f"{r['parametres'] / 1e6:.1f} M paramètres, modules : {r['modules']}")
    if r["autres"]:
        print(f"{ATT} autres fichiers ignorés au dépôt : {', '.join(r['autres'])} "
              "(ne dépose que adapter_config.json et adapter_model.safetensors)")
    if r["cfg"].get("use_dora"):
        print(f"{ATT} DoRA activé : accepté par le bench, mais plus lent. Rien à faire si le test ci-dessous passe.")

    if args.rapide:
        print("\nRÉSULTAT : contrôles du dépôt OK (test de chargement non fait : relance sans --rapide).")
        return
    if not test_reel(args.dossier):
        print("\nRÉSULTAT : le LoRA passe le dépôt mais NE PASSERAIT PAS le bench. Corrige avant de déposer.")
        sys.exit(1)
    print("\nRÉSULTAT : OK, tu peux déposer adapter_config.json et adapter_model.safetensors sur le Space.")


if __name__ == "__main__":
    main()