# Stratégie qualité des données

Objectif : le meilleur jeu d'entraînement possible pour un LoRA `Qwen/Qwen3.5-0.8B` qui traduit FR ↔ br/oc/ca.
Les décisions sont jugées sur la val gelée (`data/derived/val.jsonl`, 300 paires par langue), jamais à l'intuition.

## 0. Ce qui compte pour le score (lu dans `space_ref/`)

- Métrique : chrF++ par langue, normalisée `(chrf − BASE) / max(5, PROF − BASE)`, puis moyenne des 3 langues.
  - BASE : br 6.6, oc 32.0, ca 40.6.
  - PROF : br 26.8, oc 62.9, ca 50.4.
  - Un point de chrF en breton vaut ~1,5× un point en occitan et ~1,3× en catalan. **Le breton est prioritaire.**
- Gabarit du bench (fr→X, message utilisateur seul, chat template de la base) :
  `Traduisez fidèlement du français vers {le breton|l'occitan|le catalan}. Répondez uniquement par la traduction.\nFrançais : {phrase}\n{Breton|Occitan|Catalan} :`
- Le classement affiche une colonne « mauvaise langue ». Une sortie en catalan quand on demande de l'occitan (ou en français) est pénalisée.
- Pénalités au bench complet : culture générale et sécurité. On garde donc un LoRA léger et on n'entraîne que sur de la traduction propre.
- Un seul bench noté toutes les 150 min (environ 5 dans la journée). Chaque version de données passe d'abord par la val locale.

## 1. État actuel : v1 (`clean_data.py`)

225 372 paires brutes, puis 209 476 en train et 900 en val.
- Sources retirées : `kde_br`, `gnome_br`, `ubuntu_br` (chaînes d'interface).
- Lignes retirées : U+FFFD, caractères de contrôle, URL, HTML, mojibake, alphabets non latins.
- Paires non traduites retirées : X = FR dès 15 caractères.
- Ratio de longueur X/FR hors de [0,45 ; 2,2].
- Au plus 2 variantes par phrase FR, chaque X une seule fois.
- Les phrases FR de la val sont retirées du train.

## 1 bis. Fait (10:30) : v2

- `clean_data.py` produit `data/derived/train_v2.jsonl` (195 402 paires) et la **val gelée** `val.jsonl` (900 paires). La val n'est plus jamais réécrite.
- Étape B, rejets : nombres 7 899, doublons 5 885, interface 4 500, caractères ou artefacts wiki 2 629, ratio par source 2 294, ratio global 1 673, nb de phrases 1 006, parenthèses 624, `?` final 611.
- Les sources humaines (`flores_*`, `tatoeba_*`, `ud_keb`) ne passent pas par les filtres structurels. Sur flores, ces filtres rejetaient 15 % de bonnes paires.
- Étape C, langue maison (n-grammes + SGD, prédiction croisée, seulement si X fait au moins 20 caractères) : 1 643 X en français, 159 X en occitan au lieu de catalan (souvent de l'espagnol venant d'`aina`), 56 X en catalan au lieu d'occitan. Les rejets sont dans `data/derived/rejets_langue.jsonl`.
- Étapes D et E : `build_mix.py` produit `data/derived/sft_v2.jsonl`, soit 116 883 exemples (br 45 %, oc 30 %, ca 26 %), 75 % fr→X et 25 % X→fr, au gabarit exact du bench.
- Chat template de Qwen3.5 : le prompt de génération finit par `<think>\n\n</think>\n\n` et le token de fin est `<|im_end|>`. La cible d'entraînement = traduction + `<|im_end|>`.

## 1 ter. Deuxième passe (sans GPU)

- **Fuite val↔train** : 8 phrases FR et 5 X de la val avaient un quasi-doublon dans le train (casse, accents, ponctuation ou chiffres près). Le dédoublonnage et l'exclusion de la val utilisent maintenant `key()`. Fuite restante : 0.
- Les quasi-doublons retirent 1 722 paires de plus. `train_v2` = 193 679 paires.
- **Fragments** (FR de 1 ou 2 mots, souvent des titres Wikipédia) : 30 % seulement sont gardés dans le mélange, sauf le lexique. Ils font 2,3 % de `sft_v2`, qui compte 114 737 exemples (br 44 %, oc 30 %, ca 26 %).
- **Règle noms propres testée puis abandonnée.** Le breton traduit les toponymes (Pontivy → Pondi, Betton → Lanvezhon), ce qui donne 31 % de faux rejets sur `divyezhek` (source propre). En ca/oc, le taux de rejet (2,7–4,3 %) est proche de celui de flores (3–4,6 %), donc le signal est trop faible. Le désalignement se traite à l'étape F (score par le modèle).

## 1 quater. Score qualité composite et v3 (11:05)

- `quality_score.py` calcule, sans modèle externe, score = 0,35 ratio + 0,25 lexical + 0,20 langue + 0,20 format.
  - Classes : A 52/48/67 %, B 41/46/29 %, C 7/6/4 % (br/ca/oc).
- Revue manuelle de 10 C par langue :
  - br : environ 5 sur 10 sont mauvaises (opensubtitles désaligné) ;
  - oc : environ 8 sur 10 sont correctes (phrases courtes de tatoeba) ;
  - ca : environ 6 sur 10 sont correctes, les erreurs sont de l'espagnol ou des titres de films traduits librement.
  - Les 10 A de `ofis_publik` sont toutes correctes.
  - Le score ne repère pas bien les paires sémantiquement fausses, comme attendu.
- **Décision : keep_A_B_C moins les 5 % pires par langue**, sans toucher aux corpus humains (tatoeba, flores, ud_keb, gatitos), dont le score bas vient seulement de la brièveté. On retire aussi 343 X contenant `¿` ou `¡` (espagnol dans `aina`).
- Résultat : `sft_v3.jsonl`, 114 558 exemples (br 43 %, oc 30 %, ca 26 %), poussé sur `denisjng/hackathon-work`.
- Écarts volontaires avec le plan collé le 28/11 :
  - pas de nouveau split à 8 %, car la val est gelée ;
  - pas de prompt « Traduis du… », car on garde le gabarit du bench ;
  - pas de COMET : modèle externe, et la métrique est chrF++.

## 2. Plan, par gain attendu ÷ coût

### Étape A : audit manuel par source (CPU, 20 min)
Noter 30 paires tirées au hasard dans chaque source (bonne / partielle / fausse). Le résultat va dans le tableau du §4.
Signaux déjà vus :
- `ofis_publik` : paires désalignées (« Alain Madelin jouera le jeu » → phrase sans rapport).
- `cx_*` : traductions partielles d'articles Wikipédia.
- `aina` : web bruité.
- Fiables : `divyezhek`, `tatoeba_*`, `flores_*`, `ud_keb`.

### Étape B : filtres règles v2 (CPU, 30 min)
Ajouts dans `clean_data.py`, un compteur affiché par règle :
1. **Nombres** : les chiffres de FR doivent se retrouver dans X (même multiset). Sinon la paire est retirée.
2. **Ponctuation finale et parenthèses** : `? ! :` et les `()` / `«»` doivent correspondre.
3. **Nombre de phrases** : le nombre de `. ! ?` doit être proche entre FR et X (écart ≤ 1).
4. **Ratio de longueur par langue** : percentiles 1–99 calculés par (langue, source) au lieu d'un seuil global.
5. **Majuscules / noms propres** : un mot capitalisé en milieu de phrase FR (nom propre) doit apparaître tel quel dans X. Règle légère, retrait seulement si plusieurs manquent.

### Étape C : identification de langue maison (CPU, 30 min)
Il faut un classifieur 4 classes (fr, br, oc, ca) **entraîné sur ce dataset seulement**, car aucune donnée externe n'est permise.
- Méthode : n-grammes de caractères 1–4 + régression logistique (scikit-learn), ou Naive Bayes en stdlib.
- On retire une paire si son X est classé `fr`, ou dans une autre langue cible avec probabilité > 0,8.
- C'est surtout utile pour **oc ↔ ca**, qui sont proches : cela attaque directement la colonne « mauvaise langue ».
- Le même modèle sert à vérifier les sorties du LoRA sur la val (taux de mauvaise langue).

### Étape D : dosage du mélange (le plus gros levier après le nettoyage)
- **Budget par langue** : breton suréchantillonné, car il rapporte le plus et part de plus bas (6,6). Point de départ : br 45 %, oc 30 %, ca 25 % des exemples.
- **Poids par source** selon l'audit A : sources fiables ×2, sources bruitées plafonnées (`aina` ≤ 20 k, `cx_*` ≤ 15 k chacune, `ofis_publik` ≤ 8 k une fois filtrée).
- **Lexique** (`gatitos_br`, mots isolés) : plafond à 1 k. Le test contient des phrases.
- **Les deux sens** : 75 % fr→X (le sens du bench) et 25 % X→fr. Le kit annonce les deux sens, le bench vérifié teste fr→X.
- **Longueur** : le test ressemble à des phrases complètes de 40 à 150 caractères (les phrases du vérificateur). On sous-pondère les fragments de moins de 15 caractères.
- Une première base doit tourner vite : sous-échantillon de ~60 k paires équilibrées pour v1, puis davantage si la courbe données/score monte encore.

### Étape E : format d'entraînement (indispensable, sans coût)
- Prompt = le gabarit exact du bench, via `tokenizer.apply_chat_template` de la base, rôle `user` seul. Réponse = X + token de fin.
- Perte calculée **sur la réponse seulement**.
- **Pas de bloc `<think>`** dans la réponse. Vérifier ce que le chat template de Qwen3.5 insère après `add_generation_prompt=True` et entraîner sur exactement ce préfixe.
- Pour le sens X→fr : `Traduisez fidèlement du breton vers le français. Répondez uniquement par la traduction.\nBreton : {x}\nFrançais :`.

### Étape F : filtrage par le modèle lui-même (après la 1re soumission, GPU ~20 min)
Méthode « dual conditional cross-entropy » (Junczys-Dowmunt, WMT 2018), avec seulement le modèle autorisé :
1. Entraîner un LoRA v1 sur les données v2.
2. Calculer la perte par token de chaque paire de train dans les deux sens (fr→X et X→fr).
3. Score = moyenne des deux pertes + |écart entre les deux|. Une paire mal alignée a une perte haute dans les deux sens.
4. Retirer les 10 à 20 % les pires **par source**, puis réentraîner. Garder la variante si la val monte.

### Étape G : ablations ciblées (boucles de l'après-midi)
Une seule modification par run, sous-échantillon fixe, comparaison sur la val :
- retirer une source suspecte (`ofis_publik`, `aina`, `cx_*`, `opensubtitles_br`) ;
- part du breton à 35 %, 45 % ou 55 % ;
- avec ou sans le sens X→fr ;
- seuil du filtre F à 10 %, 20 % ou 30 %.

## 3. Garde-fous

Le tableau complet règle par règle est dans `brief.md`, section « Règles du challenge ». Pour les données :
- **Pas de données synthétiques** (back-translation, pseudo-labels, auto-distillation) sans accord écrit d'un organisateur.
- L'étape F se limite à **noter et retirer** des paires officielles avec `Qwen/Qwen3.5-0.8B` + notre LoRA. Elle ne génère aucun texte d'entraînement.

- On ne modifie jamais `data/donnees.jsonl` ni la val. Tout dérivé va dans `data/derived/`, avec un nom de version (`train_v2.jsonl`…).
- Aucune donnée externe, aucun modèle externe pour filtrer ou générer (règle du kit). Les étapes C et F n'utilisent que ce dataset et Qwen3.5-0.8B.
- Chaque version de données correspond à une ligne dans `experiments.md` : nombre de paires par langue, score de val, gain.
- Avant chaque dépôt : `uv run verifier_mon_lora.py mon_lora/` doit afficher `RÉSULTAT : OK`.

## 4. Audit par source (étape A : 10 paires tirées après v2 pour les sources suspectes, aperçu de 3 pour les autres)

| source | langue | paires v2 | audit | décision (`build_mix.py`) |
|---|---|---|---|---|
| divyezhek | br | 19 071 | bon | tout |
| ofis_publik | br | 16 611 | **3/10 désalignées** | plafond 8 k ; à filtrer en priorité à l'étape F |
| opensubtitles_br | br | 12 153 | 7/10 bonnes, familier et libre | plafond 8 k |
| autogramm | br | 6 259 | 7/10 ; orthographe dialectale ou ancienne (KLT) | plafond 3 k |
| oplb | br | 3 521 | bon mais répétitif (« Groupe … le 14 mai ») | plafond 2 k |
| tatoeba_br | br | 3 698 | bon, phrases courtes | ×2 |
| gatitos_br | br | 1 966 | mots isolés | plafond 1 k |
| wikimedia_br | br | 765 | bon | ×2 |
| ud_keb | br | 721 | bon | ×2 |
| cx_br | br | 519 | partiel | tout |
| cx_oc | oc | 26 698 | bon, quelques calques du français | plafond 15 k |
| locongres_sites | oc | 14 815 | bon, beaucoup de gascon (« que » énonciatif) | plafond 10 k |
| tatoeba_oc | oc | 12 230 | bon | plafond 8 k |
| flores_oc | oc | 921 | référence | ×2 |
| aina | ca | 54 496 | 7/10, traductions libres | plafond 15 k |
| cx_ca | ca | 18 524 | bon | plafond 12 k |
| flores_ca | ca | 922 | référence | ×2 |
| tatoeba_ca | ca | 558 | bon | ×2 |

## 5. Calendrier

| Heure | Travail données | En parallèle |
|---|---|---|
| 10:15–11:00 | A, B, C : `train_v2.jsonl` | écrire `metric.py` (chrF++ via sacrebleu + normalisation du Space) |
| 11:00–11:15 | D, E : mélange de 60 k paires au format bench | test rapide du script d'entraînement |
| 11:15–12:15 | — | entraînement baseline sur v2 (`l4x1`) |
| 12:15–12:30 | vérificateur, puis 1er dépôt | |
| 12:30–15:00 | F : scores par paire, `train_v3` | ablations G |
| 15:00 | 2e dépôt (meilleure version des données) | |
