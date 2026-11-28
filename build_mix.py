"""data/derived/train_v2_scored.jsonl (quality_score.py) -> data/derived/sft_v3.jsonl : mélange dosé, au gabarit exact du bench (seed 42).
V5=1 F_DROP=0.15 : sft_v5 = v4 + occitan gascon retiré (test probablement languedocien : flores_oc n'a aucun marqueur gascon),
  phrases courtes non humaines sous-pondérées (FLORES : médiane 145 car., le mélange v4 en a 40 % sous 40 car. en breton),
  plafonds ajustés (autogramm graphie dialectale, opensubtitles oral familier), sources encyclopédiques relevées, flores ×4.
F_DROP=0.15 : sft_v4 = v3 moins les paires les plus mal notées par le modèle (étape F, data/derived/pair_scores.jsonl).
V2=1 : reproduit sft_v2.jsonl (run 001b, 1er dépôt) = même mélange, sans filtre de score ni filtre espagnol.

Chaque ligne : {"prompt": <message utilisateur>, "completion": <traduction>, "lang", "dir", "source"}.
À l'entraînement : texte = apply_chat_template([user prompt], add_generation_prompt=True)  (finit par
"<think>\n\n</think>\n\n"), cible = completion + "<|im_end|>", perte sur la cible seulement.
"""
import collections, json, os, random, re

LANG = {"br": ("le breton", "Breton"), "oc": ("l'occitan", "Occitan"), "ca": ("le catalan", "Catalan")}
DE = {"br": "du breton", "oc": "de l'occitan", "ca": "du catalan"}
# plafond (nb de paires) ou facteur de suréchantillonnage (x2) par source, d'après l'audit de data_strategy.md §4
CAP = {"ofis_publik": 8000, "opensubtitles_br": 8000, "autogramm": 3000, "oplb": 2000, "gatitos_br": 1000,
       "cx_oc": 15000, "locongres_sites": 10000, "tatoeba_oc": 8000, "aina": 15000, "cx_ca": 12000}
UP = {"divyezhek": 1, "tatoeba_br": 2, "wikimedia_br": 2, "ud_keb": 2, "flores_oc": 2, "flores_ca": 2, "tatoeba_ca": 2}
V5 = os.environ.get("V5") == "1"
if V5:
    CAP.update({"autogramm": 1500, "opensubtitles_br": 5000, "cx_oc": 14000, "cx_ca": 12000, "aina": 11000, "locongres_sites": 8000})   # moins d'oc/ca : le breton, le plus faible, gagne le plus
    UP.update({"flores_oc": 4, "flores_ca": 4})
GASCON = re.compile(r"\b(eth|era|eras|eths|hèr|hèra|shens|tà|entà|dab|qu'ei|ei|aqueth|aqueras|aquera|ua|uas)\b|^qu'|^que\b", re.I)
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
F_DROP = float(os.environ.get("F_DROP", 0))   # V4 : part des paires les plus mal notées par le modèle (étape F) retirée, par source
bad_f = set()
if F_DROP:
    ps = [json.loads(l) for l in open("data/derived/pair_scores.jsonl", encoding="utf-8")]
    pct = {}
    for d in ("nll_fx", "nll_xf"):   # rang percentile par langue : comparable entre br, oc, ca et entre sens
        for lg in LANG:
            idx = sorted((i for i, p in enumerate(ps) if p["lang"] == lg), key=lambda i: ps[i][d])
            for rank, i in enumerate(idx): pct[(i, d)] = rank / max(1, len(idx) - 1)
    # dual conditional cross-entropy : perte haute dans les deux sens, ou très différente entre les sens = désaligné
    dual = [(pct[(i, "nll_fx")] + pct[(i, "nll_xf")]) / 2 + abs(pct[(i, "nll_fx")] - pct[(i, "nll_xf")]) for i in range(len(ps))]
    per_src = collections.defaultdict(list)
    for i, p in enumerate(ps):
        if p["source"] not in TRUSTED: per_src[p["source"]].append(i)
    for idx in per_src.values():
        idx.sort(key=lambda i: -dual[i])
        bad_f |= {(ps[i]["lang"], ps[i]["fr"], ps[i]["x"]) for i in idx[:int(F_DROP * len(idx))]}
by, dropped = collections.defaultdict(list), collections.Counter()
for r in scored:
    if not V2 and r["source"] not in TRUSTED and r["q"] < cut[r["lang"]]: dropped["score_bas"] += 1; continue
    if (r["lang"], r["fr"], r["x"]) in bad_f: dropped["modele_F"] += 1; continue
    if V5 and r["lang"] == "oc" and not r["source"].startswith("flores") and GASCON.search(r["x"]): dropped["gascon"] += 1; continue
    if not V2 and ("¿" in r["x"] or "¡" in r["x"]): dropped["espagnol"] += 1; continue   # ponctuation absente du catalan et de l'occitan
    by[r["source"]].append(r)
print("seuils", {k: round(v, 3) for k, v in cut.items()}, "retirés", dict(dropped))
rows = []
for src, v in by.items():
    rng.shuffle(v)
    if src != "gatitos_br":   # titres d'1-2 mots (« Biographie ») : le test contient des phrases, on n'en garde que 30 %
        v = [r for r in v if len(r["fr"].split()) > 2 or rng.random() < FRAG_KEEP]
    if V5 and src not in TRUSTED:   # phrases courtes non humaines : 20 % sous 20 car., 50 % sous 40 car.
        v = [r for r in v if len(r["fr"]) >= 40 or rng.random() < (0.2 if len(r["fr"]) < 20 else 0.5)]
    rows += v[:CAP[src]] if src in CAP else v * UP.get(src, 1)
rng.shuffle(rows)
out = []
for r in rows:
    if rng.random() < REVERSE:
        out.append({"prompt": x_to_fr(r["lang"], r["x"]), "completion": r["fr"], "lang": r["lang"], "dir": "x2fr", "source": r["source"]})
    else:
        out.append({"prompt": fr_to_x(r["lang"], r["fr"]), "completion": r["x"], "lang": r["lang"], "dir": "fr2x", "source": r["source"]})
with open(os.environ.get("OUT", "data/derived/sft_v2.jsonl" if V2 else "data/derived/sft_v5.jsonl" if V5 else "data/derived/sft_v4.jsonl" if F_DROP else "data/derived/sft_v3.jsonl"), "w", encoding="utf-8") as f:
    f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in out)

n = collections.Counter(r["lang"] for r in out)
print(len(out), {k: f"{v} ({100 * v / len(out):.0f}%)" for k, v in n.items()}, dict(collections.Counter(r["dir"] for r in out)))
assert out[0]["prompt"].count("\n") == 2 and not out[0]["completion"].startswith(" ")
print(out[0]["prompt"], "→", out[0]["completion"])
print(next(r for r in out if r["dir"] == "x2fr" and r["lang"] == "oc")["prompt"])
