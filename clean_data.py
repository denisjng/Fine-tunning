"""Nettoie data/donnees.jsonl -> data/derived/{train_v2,val}.jsonl (seed 42). Le fichier brut n'est jamais modifié.

Règle du kit : aucune donnée externe. Le classifieur de langue est entraîné sur ce dataset seulement.
La val est gelée : data/derived/val.jsonl est relue telle quelle (jamais recréée) et ses phrases sont retirées du train.
"""
import collections, json, random, re, sys, unicodedata
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import SGDClassifier

DROP_SRC = {"kde_br", "gnome_br", "ubuntu_br"}          # chaînes d'interface (_accélérateurs, %s), pas des phrases
TRUSTED = {"flores_ca", "flores_oc", "tatoeba_br", "tatoeba_oc", "tatoeba_ca", "ud_keb"}   # corpus humains : pas de filtre structurel
BAD = re.compile(r"\[réf|\[citation|↑|\[\d+\]|�|[\x00-\x08\x0b-\x1f]|https?://|www\.|<[a-z/][^>]*>|Ã.|â€|[Ѐ-ӿ֐-ۿ぀-鿿]")
NUM, SENT, SEP = re.compile(r"\d+"), re.compile(r"[.!?…](?:\s|$)"), re.compile(r"(?<=\d)[ .  ](?=\d{3})")
MAX_PER_FR = 2
VAL = Path("data/derived/val.jsonl")
norm = lambda s: re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def key(s):
    """Clé de quasi-doublon : casse, accents, ponctuation et chiffres ignorés."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s.casefold()) if not unicodedata.combining(c))
    return re.sub(r"\d+", "0", re.sub(r"[^\w]+", " ", s)).strip()
drops = collections.Counter()


def rule(r):
    """Nom de la première règle qui rejette la paire, ou None."""
    fr, x = r["fr"], r["x"]
    if r["source"] in DROP_SRC: return "source_interface"
    if len(fr) < 2 or len(x) < 2: return "vide"
    if BAD.search(fr + x): return "caracteres"
    if len(fr) >= 15 and fr.casefold() == x.casefold(): return "non_traduit"
    if r["source"] in TRUSTED: return None
    if len(fr) >= 20 and not 0.45 <= len(x) / len(fr) <= 2.2: return "ratio_global"
    nx = sorted(NUM.findall(SEP.sub("", x)))
    if nx and sorted(NUM.findall(SEP.sub("", fr))) != nx: return "nombres"   # chiffres en toutes lettres côté X : gardé
    if fr.rstrip()[-1] == "?" and "?" not in x[-3:]: return "ponct_finale"
    if abs(fr.count("(") - x.count("(")) >= 2: return "parentheses"
    if abs(len(SENT.findall(fr)) - len(SENT.findall(x))) > 1: return "nb_phrases"
    return None


rows = []
for l in open("data/donnees.jsonl", encoding="utf-8"):
    r = json.loads(l)
    r["fr"], r["x"] = norm(r["fr"]), norm(r["x"])
    rows.append(r)
kept = []
for r in rows:
    why = rule(r)
    if why: drops[why] += 1
    else: kept.append(r)

# ratio de longueur par (langue, source) : hors percentiles 1-99 = désaligné pour cette source
ratios = collections.defaultdict(list)
for r in kept: ratios[(r["lang"], r["source"])].append(len(r["x"]) / len(r["fr"]))
bounds = {k: (np.percentile(v, 1), np.percentile(v, 99)) for k, v in ratios.items()}
tmp = []
for r in kept:
    lo, hi = bounds[(r["lang"], r["source"])]
    if r["source"] not in TRUSTED and len(r["fr"]) >= 20 and not lo <= len(r["x"]) / len(r["fr"]) <= hi: drops["ratio_source"] += 1
    else: tmp.append(r)
kept = tmp

# identification de langue : n-grammes de caractères, prédiction croisée en 2 plis (pas de score sur ses propres données)
vec = HashingVectorizer(analyzer="char_wb", ngram_range=(1, 4), n_features=2**20, alternate_sign=False, norm="l2")
texts = [r["x"] for r in kept]
labels = np.array([r["lang"] for r in kept])
fold = np.arange(len(kept)) % 2
fr_texts = [r["fr"] for r in kept]
X_x, X_fr = vec.transform(texts), vec.transform(fr_texts)
proba = np.zeros((len(kept), 4))
classes = None
for k in (0, 1):
    tr = fold != k
    clf = SGDClassifier(loss="log_loss", alpha=1e-6, max_iter=8, tol=None, random_state=42)
    clf.fit(sp.vstack([X_x[tr], X_fr[tr]]), np.concatenate([labels[tr], ["fr"] * tr.sum()]))
    classes = list(clf.classes_)
    proba[fold == k] = clf.predict_proba(X_x[fold == k])
pred = np.array(classes)[proba.argmax(1)]
tmp, rej = [], []
for r, p, pr in zip(kept, pred, proba):
    if len(r["x"]) < 20: tmp.append(r); continue   # trop court pour un avis fiable
    if (p == "fr" and pr.max() > 0.5) or (p != r["lang"] and pr.max() > 0.8):
        drops["langue_fr" if p == "fr" else f"langue_{p}_au_lieu_de_{r['lang']}"] += 1
        rej.append({**r, "pred": p, "p": round(float(pr.max()), 2)})
    else: tmp.append(r)
kept = tmp
with open("data/derived/rejets_langue.jsonl", "w", encoding="utf-8") as f:   # pour l'audit manuel
    f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rej)

# doublons : une phrase FR garde au plus MAX_PER_FR variantes (longueur la plus proche), un même X une seule fois
kept.sort(key=lambda r: abs(len(r["x"]) / max(1, len(r["fr"])) - 1))
seen_x, per_fr, out = set(), collections.Counter(), []
for r in kept:
    kf, kx = (r["lang"], key(r["fr"])), (r["lang"], key(r["x"]))
    if kx in seen_x or per_fr[kf] >= MAX_PER_FR:
        drops["doublon"] += 1
        continue
    seen_x.add(kx); per_fr[kf] += 1; out.append(r)

# val gelée (créée le 28/11 à ~10:30 : 75 par source, 300 par langue, phrases >= 20 car.) : jamais recréée
rng = random.Random(42)
rng.shuffle(out)
if not VAL.exists():
    sys.exit("val.jsonl manquante : récupérer denisjng/hackathon-work/val.jsonl (val gelée, ne pas la recréer)")
val = [json.loads(l) for l in open(VAL, encoding="utf-8")]
val_fr = {(r["lang"], key(r["fr"])) for r in val}
val_x = {(r["lang"], key(r["x"])) for r in val}
train = [r for r in out if (r["lang"], key(r["fr"])) not in val_fr and (r["lang"], key(r["x"])) not in val_x]
with open("data/derived/train_v2.jsonl", "w", encoding="utf-8") as f:
    f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in train)

print(f"brut {len(rows)} -> train {len(train)}, val {len(val)}")
print("rejets:", dict(drops.most_common()))
src_raw = collections.Counter((r["lang"], r["source"]) for r in rows)
src_kept = collections.Counter((r["lang"], r["source"]) for r in train)
for k in sorted(src_raw, key=lambda k: (k[0], -src_raw[k])):
    print(f"  {k[0]} {k[1]:18} {src_raw[k]:6} -> {src_kept[k]:6} ({100 * src_kept[k] / src_raw[k]:.0f}% gardé)")
