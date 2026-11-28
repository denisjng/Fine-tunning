# Experiments
subs used: 0 / 5 créneaux (1 noté / 150 min)
cost so far: 0
last_review:

| # | time | change | hypothesis | status | job / log | cost | val | LB | kept | submission |
|---|---|---|---|---|---|---|---|---|---|---|
| smoke1 | 10:50 | test 300 ex, BS 16 | vérifier la chaîne | crashed (OOM 20,5/22 Go) | ynov/6b0aa0a154072e8b716d0778 | ~0,1 | | | | |
| smoke2 | 10:40 | + flash-linear-attention, BS 8×4, grad checkpointing | plus d'OOM | done (395 s) | ynov/6b0aa0f154072e8b716d08b9 | ~0,1 | 0.4102 (300 ex) | | | |
| 001 | 10:45 | baseline 70k ex | — | cancelled (3,6 s/pas, ETA 2h10 > 12:30) | ynov/6b0aa2ca6c5d61fff18c284d | ~0,1 | | | | |
| 001b | 10:50 | baseline sft_v2 28k ex, r16, lr 2e-4, 1 ép. | 1re soumission avant 12:30 | running | ynov/6b0aa3de6c5d61fff18c2c2c → denisjng/hackathon-lora/001 | | | | | |
| 002quick | 10:54 | test 20 min : 8k ex, éval 300 | score rapide en parallèle | done (2,0 s/pas) | ynov/6b0aa4d054072e8b716d17c9 → denisjng/hackathon-lora/002quick | ~0,3 | 0.7196 (br 15.3 / oc 60.0 / ca 48.7, 300 ex) | | | |
| 003 | 11:07 | sft_v3 complet (114 558 ex, score qualité −5 %, espagnol retiré), 1 ép. | 4× plus de données pour casser les boucles en breton | running (~2 h, relancé à 11:16) | ~~ynov/6b0aa7d16c5d61fff18c383f~~ (crash : chemin `/work` converti par Git Bash) → ynov/6b0aa9b054072e8b716d254b → denisjng/hackathon-lora/003 | | | | | |

## Lessons
- Git Bash convertit `-e DATA=/work/...` en chemin Windows : toujours préfixer les commandes `hf jobs` par `MSYS_NO_PATHCONV=1`.
- Erreurs du run 002quick : le breton part en **boucles de répétition** (« eus eus eus… », 20 sorties sur 102 sont plus de 1,6× trop longues), signe d'un sous-entraînement. Seulement 6 % des sorties copient le français. En occitan, l'écart vient surtout du dialecte (références gasconnes de tatoeba_oc et locongres, sortie languedocienne). Catalan correct (aina 42,8, cx_ca 52,7).

## Research notes

Papiers fournis par l'utilisateur (28/11), filtrés par les règles du challenge. Les décisions viennent de ce que je sais de ces papiers. Ils n'ont pas été relus en ligne aujourd'hui, pour économiser les crédits. Les titres de 2025–2026 marqués (?) n'ont pas été vérifiés : je ne les connais pas assez pour en tirer plus que l'idée générale.

### Appliqué dès la baseline
- **LoRA (Hu et al. 2021) + QLoRA (Dettmers et al. 2023)** : adapter sur **toutes les couches linéaires** (q, k, v, o, gate, up, down). QLoRA montre que c'est ce qui compte le plus, plus que le rang.
  - Départ : r = 16, alpha = 32, dropout 0,05, lr 2e-4 (cosine, warmup 3 %).
  - **Base en bf16, pas en 4 bits** : 0,8B tient largement sur L4, et le bench charge la base en bf16. Pas d'écart entre l'entraînement et le bench.
  - Taille estimée ~20 Mo, loin des 200 Mo.
- **Which LoRA? (2026) (?)** : LoRA standard, sans DoRA, rsLoRA, CURLoRA ni autre variante. C'est cohérent avec la pratique courante et le DoRA ralentit le bench (avertissement du vérificateur).
- **Monolingual or Multilingual Instruction Tuning (Chen et al. 2023)** : **un seul adapter** pour les 6 directions, déjà le cas dans `sft_v2`. La val est suivie par langue.
- **Scaling Laws for Forgetting (Kalajdzievski 2024)** : avec LoRA, l'oubli croît en loi de puissance avec le nombre de pas et la baisse de la perte d'entraînement. Donc **1 époque**, perte sur la réponse seulement, et checkpoint choisi sur le chrF++ de val, pas sur la perte.
- **Rethinking low-resource MT (Scalvini et al. 2025) (?)** : le fine-tuning bat le prompting pour les langues peu dotées. C'est la confirmation du choix de faire du SFT et non du prompt engineering, qui de toute façon est impossible : le gabarit du bench est fixe.

### Leviers pour les boucles (notés gain × chance ÷ minutes GPU au moment de choisir)
- **Multi-étapes (Beyond Vanilla Fine-Tuning, 2025) (?)** : étape 1 sur tout `sft_v*`, puis une **étape 2 courte à lr ÷ 4** sur le sous-ensemble le plus propre (flores, tatoeba, divyezhek, ud_keb, et les meilleures paires de l'étape F). Données officielles uniquement. Gain attendu moyen, ~15 min GPU.
- **Intensité de l'entraînement (Prompt, Translate, Fine-Tune…, 2025 ; LinguaLIFT 2024)** : un entraînement agressif sur les langues cibles dégrade le français et les capacités générales. Pour les leviers « plus d'époques » et « r plus grand », on ne garde le résultat que si la dérive de garde-fou (ci-dessous) reste stable.
- **CURLoRA (2024)** : seulement en plan B, si le contrôle complet du Space donne un facteur culture ou sécurité < 0,995 et que baisser lr, r et époques ne suffit pas.

### Mesure de l'oubli sans données externes (Demystifying Forgetting 2024 ; Scaling Laws for Forgetting)
- **Dérive en français** : perte moyenne (NLL) de la base et de base + LoRA sur 300 phrases FR de la val, en texte brut sans gabarit. Une hausse nette signale que le modèle oublie le français. Coût : quelques secondes, à chaque run.
- **12 prompts témoins écrits à la main** (6 de culture générale, 6 de sécurité avec refus attendu). Comparaison base / LoRA à l'œil, **évaluation seulement, jamais à l'entraînement**.
- Le **contrôle complet du Space** (2 fois max) reste la mesure qui fait foi.

### Écarté, avec la raison
- **COMET, xCOMET, BLEU Meets COMET** : COMET est un modèle externe (XLM-R) qui ne couvre pas l'occitan et couvre mal le breton. Surtout, le classement utilise **chrF++**. On optimise et on choisit sur chrF++ (sacrebleu, `word_order=2`), plus une lecture manuelle des erreurs sur br et oc.
- **Self-Synthesized Rehearsal (Luo et al. 2024), Scaling Low-Resource MT via Synthetic Data (2025)** : données générées, donc interdites par défaut tant qu'un organisateur ne les autorise pas par écrit.
- **Compensating for Data with Reasoning (2025) (?)** : le raisonnement ou les exemples dans le prompt sont impossibles, car le bench impose son gabarit et compte les balises `<think>` comme du texte.
- **Prompt « Traduis du français vers le breton : »** suggéré dans la bibliographie : non. On garde le gabarit exact du vérificateur (« Traduisez fidèlement du français vers le breton. Répondez uniquement par la traduction. … »).
- **Split stratifié par domaine** : la val reste gelée (règle). On ajoute à la place une ventilation du chrF++ par source et domaine dans le rapport de `metric.py`.

## Strategy log

## Handoff
- 10:45 : jobs bloqués, erreur 403 « missing permissions: job.write » sur ynov. Le compte a le rôle `no_access` dans l'org et attend l'accès des organisateurs. Token à régénérer : il a été affiché en clair par HF_DEBUG.
- Prêt : `metric.py` (auto-test OK), `exp/001/train.py` (compilation OK, jamais exécuté), données sur `denisjng/hackathon-work` (privé : sft_v2, val, metric).
- Test rapide dès que l'accès arrive (environ 300 exemples, sans push) :
  `hf jobs uv run --namespace ynov --resource-group-id 6b09693c78688af4256e8db8 --flavor l4x1 --timeout 30m --secrets HF_TOKEN -v hf://datasets/denisjng/hackathon-work:/work -e MAX_EX=300 -e RUN=smoke --detach exp/001/train.py`
- Run complet ensuite : mêmes options, `--timeout 3h -e RUN=001 -e PUSH=denisjng/hackathon-lora`, sans `MAX_EX`.
