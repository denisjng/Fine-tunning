"""data/derived/train_v2_scored.jsonl (quality_score.py) -> data/derived/sft_v3.jsonl : mélange dosé, au gabarit exact du bench (seed 42).
V2=1 : reproduit sft_v2.jsonl (run 001b, 1er dépôt) = même mélange, sans filtre de score ni filtre espagnol.

Chaque ligne : {"prompt": <message utilisateur>, "completion": <traduction>, "lang", "dir", "source"}.
À l'entraînement : texte = apply_chat_template([user prompt], add_generation_prompt=True)  (finit par
"<think>\n\n</think>\n\n"), cible = completion + "<|im_end|>", perte sur la cible seulement.
"""
import collections, json, os, random

LANG = {"br": ("le breton", "Breton"), "oc": ("l'occitan", "Occitan"), "ca": ("le catalan", "Catalan")}
DE = {"br": "du breton", "oc": "de l'occitan", "ca": "du catalan"}
# plafond (nb de paires) ou facteur de suréchantillonnage (x2) par source, d'après l'audit de data_strategy.md §4
CAP = {"ofis_publik": 8000, "opensubtitles_br": 8000, "autogramm": 3000, "oplb": 2000, "gatitos_br": 1000,
       "cx_oc": 15000, "locongres_sites": 10000, "tatoeba_oc": 8000, "aina": 15000, "cx_ca": 12000}
UP = {"divyezhek": 1, "tatoeba_br": 2, "wikimedia_br": 2, "ud_keb": 2, "flores_oc": 2, "flores_ca": 2, "tatoeba_ca": 2}
REVERSE = 0.25   # part X->fr ; le bench vérifié teste fr->X
FRAG_KEEP = 0.3


def fr_to_x(lg, fr):
    art, nom = LANG[lg]
    return f"Traduisez fidèlement du français vers {art}. Répondez uniquement par la traduction.\nFrançais : {fr}\n{nom} :"


def x_to_fr(lg, x):
    nom = LANG[lg][1]
    return f"Traduisez fidèlement {DE[lg]} vers le français. Répondez uniquement par la traduction.\n{nom} : {x}\nFrançais :"


TRUSTED = {"flores_ca", "flores_oc", "tatoeba_br", "tatoeba_oc", "tatoeba_ca", "ud_keb", "gatitos_br"}   # score bas = phrase courte, pas une erreur
BOTTOM = 0.05   # décision de la revue manuelle : keep_A_B_C sauf les 5 % pires par langue (hors corpus humains)
rng = random.Random(42)
V2 = os.environ.get("V2") == "1"
scored = [json.loads(l) for l in open("data/derived/train_v2.jsonl" if V2 else "data/derived/train_v2_scored.jsonl", encoding="utf-8")]
cut = {lg: -1 for lg in LANG} if V2 else {lg: sorted(r["q"] for r in scored if r["lang"] == lg and r["source"] not in TRUSTED)[int(BOTTOM * sum(1 for r in scored if r["lang"] == lg and r["source"] not in TRUSTED))] for lg in LANG}
by, dropped = collections.defaultdict(list), collections.Counter()
for r in scored:
    if not V2 and r["source"] not in TRUSTED and r["q"] < cut[r["lang"]]: dropped["score_bas"] += 1; continue
    if not V2 and ("¿" in r["x"] or "¡" in r["x"]): dropped["espagnol"] += 1; continue   # ponctuation absente du catalan et de l'occitan
    by[r["source"]].append(r)
print("seuils", {k: round(v, 3) for k, v in cut.items()}, "retirés", dict(dropped))
rows = []
for src, v in by.items():
    rng.shuffle(v)
    if src != "gatitos_br":   # titres d'1-2 mots (« Biographie ») : le test contient des phrases, on n'en garde que 30 %
        v = [r for r in v if len(r["fr"].split()) > 2 or rng.random() < FRAG_KEEP]
    rows += v[:CAP[src]] if src in CAP else v * UP.get(src, 1)
rng.shuffle(rows)
out = []
for r in rows:
    if rng.random() < REVERSE:
        out.append({"prompt": x_to_fr(r["lang"], r["x"]), "completion": r["fr"], "lang": r["lang"], "dir": "x2fr", "source": r["source"]})
    else:
        out.append({"prompt": fr_to_x(r["lang"], r["fr"]), "completion": r["x"], "lang": r["lang"], "dir": "fr2x", "source": r["source"]})
with open(os.environ.get("OUT", "data/derived/sft_v2.jsonl" if V2 else "data/derived/sft_v3.jsonl"), "w", encoding="utf-8") as f:
    f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in out)

n = collections.Counter(r["lang"] for r in out)
print(len(out), {k: f"{v} ({100 * v / len(out):.0f}%)" for k, v in n.items()}, dict(collections.Counter(r["dir"] for r in out)))
assert out[0]["prompt"].count("\n") == 2 and not out[0]["completion"].startswith(" ")
print(out[0]["prompt"], "→", out[0]["completion"])
print(next(r for r in out if r["dir"] == "x2fr" and r["lang"] == "oc")["prompt"])
