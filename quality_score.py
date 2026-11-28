"""Score qualité composite par paire (sans modèle externe), sur data/derived/train_v2.jsonl -> data/derived/train_v2_scored.jsonl.

score = 0.35 ratio + 0.25 lexical + 0.20 langue + 0.20 format ; classes A >= 0.75, B >= 0.55, C sinon.
- ratio   : proximité de len(x)/len(fr) à la médiane de la langue (échelle log)
- lexical : recouvrement de trigrammes de caractères FR/X, en rang percentile dans la langue (br est loin du français)
- langue  : probabilité de la langue cible, classifieur maison entraîné sur ce dataset (prédiction croisée 2 plis)
- format  : chiffres, ponctuation finale, guillemets/parenthèses, majuscule initiale
"""
import collections, json, math, re

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import SGDClassifier

rows = [json.loads(l) for l in open("data/derived/train_v2.jsonl", encoding="utf-8")]
langs = np.array([r["lang"] for r in rows])

# ratio
ratio = np.array([len(r["x"]) / max(1, len(r["fr"])) for r in rows])
med = {lg: np.median(ratio[langs == lg]) for lg in set(langs)}
s_ratio = np.array([math.exp(-abs(math.log(max(q, 1e-3) / med[lg])) / 0.35) for q, lg in zip(ratio, langs)])

# lexical : Jaccard des trigrammes, puis rang percentile par langue
tri = lambda s: {s[i:i + 3] for i in range(len(s) - 2)} or {s}
jac = np.array([len(tri(r["fr"].lower()) & tri(r["x"].lower())) / max(1, len(tri(r["fr"].lower()) | tri(r["x"].lower()))) for r in rows])
s_lex = np.zeros(len(rows))
for lg in set(langs):
    idx = np.where(langs == lg)[0]
    s_lex[idx] = jac[idx].argsort().argsort() / max(1, len(idx) - 1)

# langue
vec = HashingVectorizer(analyzer="char_wb", ngram_range=(1, 4), n_features=2**20, alternate_sign=False, norm="l2")
Xx, Xfr = vec.transform([r["x"] for r in rows]), vec.transform([r["fr"] for r in rows])
fold = np.arange(len(rows)) % 2
s_lang = np.zeros(len(rows))
for k in (0, 1):
    tr = fold != k
    clf = SGDClassifier(loss="log_loss", alpha=1e-6, max_iter=8, tol=None, random_state=42)
    clf.fit(sp.vstack([Xx[tr], Xfr[tr]]), np.concatenate([langs[tr], ["fr"] * tr.sum()]))
    P = clf.predict_proba(Xx[fold == k])
    col = {c: i for i, c in enumerate(clf.classes_)}
    s_lang[fold == k] = P[np.arange(P.shape[0]), [col[l] for l in langs[fold == k]]]

# format
NUM = re.compile(r"\d+")
def fmt(fr, x):
    c = [sorted(NUM.findall(fr)) == sorted(NUM.findall(x)) or not NUM.findall(x),
         (fr[-1] in ".?!:") == (x[-1] in ".?!:") if fr and x else False,
         fr.count('"') + fr.count("«") == x.count('"') + x.count("«") + x.count("“"),
         fr.count("(") == x.count("("),
         fr[:1].isupper() == x[:1].isupper()]
    return sum(c) / len(c)
s_fmt = np.array([fmt(r["fr"], r["x"]) for r in rows])

score = 0.35 * s_ratio + 0.25 * s_lex + 0.20 * s_lang + 0.20 * s_fmt
cls = np.where(score >= 0.75, "A", np.where(score >= 0.55, "B", "C"))
with open("data/derived/train_v2_scored.jsonl", "w", encoding="utf-8") as f:
    for r, s, c, a, b, d, e in zip(rows, score, cls, s_ratio, s_lex, s_lang, s_fmt):
        f.write(json.dumps({**r, "q": round(float(s), 3), "cls": str(c),
                            "q_parts": [round(float(a), 2), round(float(b), 2), round(float(d), 2), round(float(e), 2)]}, ensure_ascii=False) + "\n")

print("médiane ratio", {k: round(float(v), 2) for k, v in med.items()})
for lg in sorted(set(langs)):
    c = collections.Counter(cls[langs == lg])
    print(lg, {k: f"{c[k]} ({100 * c[k] / sum(c.values()):.0f}%)" for k in "ABC"})
src = collections.defaultdict(collections.Counter)
for r, c in zip(rows, cls): src[r["source"]][c] += 1
for s, c in sorted(src.items(), key=lambda kv: -kv[1]["C"] / sum(kv[1].values())):
    n = sum(c.values()); print(f"  {s:18} n={n:6}  A {100 * c['A'] / n:4.0f}%  B {100 * c['B'] / n:4.0f}%  C {100 * c['C'] / n:4.0f}%")
assert len(score) == len(rows) and 0 <= score.min() and score.max() <= 1
