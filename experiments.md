# Experiments
subs used: 1 / 5 créneaux (1 noté / 150 min)
cost so far: 0
last_review:

| # | time | change | hypothesis | status | job / log | cost | val | LB | kept | submission |
|---|---|---|---|---|---|---|---|---|---|---|
| smoke1 | 10:50 | test 300 ex, BS 16 | vérifier la chaîne | crashed (OOM 20,5/22 Go) | ynov/6b0aa0a154072e8b716d0778 | ~0,1 | | | | |
| smoke2 | 10:40 | + flash-linear-attention, BS 8×4, grad checkpointing | plus d'OOM | done (395 s) | ynov/6b0aa0f154072e8b716d08b9 | ~0,1 | 0.4102 (300 ex) | | | |
| 001 | 10:45 | baseline 70k ex | — | cancelled (3,6 s/pas, ETA 2h10 > 12:30) | ynov/6b0aa2ca6c5d61fff18c284d | ~0,1 | | | | |
| 001b | 10:50 | baseline sft_v2 28k ex, r16, lr 2e-4, 1 ép. | 1re soumission avant 12:30 | done (1,8 s/pas) | ynov/6b0aa3de6c5d61fff18c2c2c → denisjng/hackathon-lora/001 | ~0,5 | **0.9521** (br 23.7 / oc 59.3 / ca 51.6) ; fr_drift 4.14→4.25 | **0,000** (trad 0,543 : br 0,49 chrF 16,5 / oc 0,72 chrF 54,4 / ca 0,42 chrF 44,7 ; culture ×0,99 ; **sécurité ×0,00**) | yes | bench 01, déposé 11:31 |
| 002quick | 10:54 | test 20 min : 8k ex, éval 300 | score rapide en parallèle | done (2,0 s/pas) | ynov/6b0aa4d054072e8b716d17c9 → denisjng/hackathon-lora/002quick | ~0,3 | 0.7196 (br 15.3 / oc 60.0 / ca 48.7, 300 ex) | | | |
| 003 | 12:00 H200 | sft_v3 complet (114 558 ex, score qualité −5 %, espagnol retiré), 1 ép. | 4× plus de données pour casser les boucles en breton | done : **val 1.3919** (br 36.05 / oc 68.09 / ca 55.78) ; fr_drift 4.14→4.33 ; sécurité à sonder | ~~ynov/6b0aa7d16c5d61fff18c383f~~ (crash : chemin `/work` converti par Git Bash) → ynov/6b0aa9b054072e8b716d254b → denisjng/hackathon-lora/003 | | | | | |

| probe001 | 11:45 | sonde garde-fous sur 001b (éval seule) | diagnostiquer sécurité ×0 | done | ynov/6b0ab0276c5d61fff18c485f | ~0,1 | refus 8/12 base → **2/12 LoRA** ; bombe, malware, fake news acceptés ; culture OK (réponses courtes) | | | |
| sweep001 | 11:50 | intensité du LoRA 001b s ∈ {1…0} (éval seule) | trouver s qui garde les refus | done : s=1 refus 2/12 val 0,974 ; **s=0,75 refus 4/12 val 1,022** ; s=0,6 6/12 0,958 ; s=0,5 6/12 0,894 ; s=0,4 4/12 0,851 (base 8/12) | ynov/6b0ab1c554072e8b716d3487 | | | | | |
| 004light | 12:00 H200 | LoRA léger : attention seule (q,k,v,o, in_proj_qkv, out_proj), r 8, lr 1e-4, 28k sft_v3 | moins d'effet sur la sécurité | done | ynov/6b0ab2af6c5d61fff18c4c19 → denisjng/hackathon-lora/004light | ~0,8 | 0.8394 (br 17.1 / oc 58.9 / ca 51.7, 300 ex) ; fr_drift 4.14→4.15 ; padding lot≠seul 4/16 ; **sonde 6/12 refus** (bombe et fake news acceptées) | | | |

## Lessons
- Étape F : les pires paires selon 001b sont inversées (champ fr en breton) ou désalignées, ce qui confirme le signal. sft_v4 (F_DROP=0.15) = 111 747 ex (br 42 %), md5 72936d2e72f6c2df37fa749ed816347c. 22 272 paires retirées avant les plafonds par source.
- L'organisateur répond NON aux refus écrits à la main ou générés. Garde-fous : uniquement la config du LoRA et l'intensité. Grille lancée 12:15 (005vo, 006attn, 007mlp, 008r4) avec REFUS mesuré en fin de run.
- padding_check : 4 sorties sur 16 diffèrent entre lot (padding à gauche) et une par une. La val en lot s'écarte un peu du bench, qui traduit phrase par phrase. Les écarts restent petits (fr_drift, scores cohérents), mais pour un choix serré il faut évaluer phrase par phrase.
- Sonde sur 002quick (seulement 250 pas, 8k ex) : 5/12 refus (base 8/12). Bombe, pipe bomb et fake news restent acceptés. **La sécurité se dégrade dès les premiers pas** : réduire la durée ne suffit pas non plus.
- Réduire l'intensité du LoRA (s) remonte un peu les refus (au mieux 6/12 à s=0,5–0,6, contre 8/12 pour la base) sans jamais atteindre la base. s=0,75 améliore même la val (1,022 contre 0,974 à s=1). L'intensité seule ne suffit pas pour la sécurité.
- H200 à BS 32 sans checkpointing : ~1,7 s/pas, comme le L4 à 8×4. **Correction à 12:04 :** ce n'était que la chauffe (compilation triton). En régime établi, le H200 tourne à 0,31 s/pas, ~6× plus vite que le L4. Le coût par run est équivalent, et c'est bien plus rapide : on garde le H200.
- 12:00 : H200 autorisé par le resource group (test nvidia-smi OK). Entraînements passés en `--flavor h200 -e GC=0 -e BS=32 -e GA=1`. 003 et 004light relancés sur H200 : ynov/6b0ab2ac6c5d61fff18c4c0f et ynov/6b0ab2af6c5d61fff18c4c19. Étape F (scores par paire avec 001b) : ynov/6b0ab2db6c5d61fff18c4c6a.
- **Bench 01 : sécurité ×0,00, donc score final 0.** Les garde-fous sont mesurés à chaque bench et multiplient le score. Sans sécurité, la traduction ne compte pas. Le test caché est aussi plus dur que notre val (br 16,5 contre 23,7 ; ca 44,7 contre 51,6).
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
