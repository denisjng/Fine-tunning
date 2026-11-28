"""Métrique du Space : chrF++ (sacrebleu, word_order=2) par langue, normalisé comme depot.py, moyenne des 3 langues.

    python metric.py            # auto-test
Usage : from metric import score ; score(hyps, refs, langs) -> {"score": .., "br": {"chrf": .., "gain": ..}, ...}
"""
from sacrebleu.metrics import CHRF

BASE = {"br": 6.64, "oc": 32.0, "ca": 40.56}    # depot.py:39
PROF = {"br": 26.8, "oc": 62.94, "ca": 50.38}   # depot.py:40


def gain(chrf, lg):
    return (chrf - BASE[lg]) / max(5.0, PROF[lg] - BASE[lg])   # depot.py:145 ; 1.0 = niveau du prof


def score(hyps, refs, langs):
    out = {}
    for lg in BASE:
        idx = [i for i, l in enumerate(langs) if l == lg]
        if not idx:
            continue
        c = CHRF(word_order=2).corpus_score([hyps[i] for i in idx], [[refs[i] for i in idx]]).score
        out[lg] = {"chrf": round(c, 2), "gain": round(gain(c, lg), 4), "n": len(idx)}
    out["score"] = round(sum(v["gain"] for v in out.values()) / len(out), 4)
    return out


if __name__ == "__main__":
    s = score(["Demat d'an holl", "Bonjorn a totes", "Bon dia a tothom"], ["Demat d'an holl", "Bonjorn a totes", "Bon dia a tothom"], ["br", "oc", "ca"])
    assert s["br"]["chrf"] == 100 and abs(s["br"]["gain"] - (100 - 6.64) / 20.16) < 1e-3, s
    assert abs(gain(PROF["oc"], "oc") - 1) < 1e-9 and gain(BASE["ca"], "ca") == 0
    print("metric OK", s)
