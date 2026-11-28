# Brief
start: 2026-11-28 09:00
end: 2026-11-28 23:59

## Rules
competition: Hackathon IA & Data × Asus (Ynov), Space https://huggingface.co/spaces/ynov/hackathon-ia-data-asus
task: LoRA sur Qwen/Qwen3.5-0.8B qui traduit FR ↔ breton (br), occitan (oc), catalan (ca), dans les deux sens. Bench noté : fr→X au gabarit du vérificateur.
metric: chrF++ par langue, normalisé (chrf − BASE) / max(5, PROF − BASE), moyenne des 3 ; plus haut = mieux. BASE br 6.64 / oc 32.0 / ca 40.56 ; PROF br 26.8 / oc 62.94 / ca 50.38. Colonne « mauvaise langue » affichée. Garde-fous culture générale × sécurité au bench complet.
data: ynov/hackathon-trad-donnees, donnees.jsonl (fr, x, lang, source, domain), 225 372 paires
sample_submission: aucun ; le rendu = dossier adapter (adapter_config.json + adapter_model.safetensors)
submission_method: web upload sur https://huggingface.co/spaces/ynov/hackathon-ia-data-asus?page=depot (pseudo + code élève), fait par l'utilisateur ; le code n'est jamais écrit dans le repo
submission_cap: 1 soumission notée / 150 min, une seule dans la file à la fois ; contrôle complet (culture + sécurité) 2 fois max
auto_submit: no (dépôt web : Claude prépare et vérifie, l'utilisateur dépose)
final_pick: best counts (« c'est ta meilleure note qui compte », app.py:438) ; à égalité, le premier déposé passe devant → déposer toute vraie amélioration au plus tôt
deadlines: dépôts jusqu'à 23:59 (FIN du Space, +01:00 = heure locale) ; un bench dure ~40 min
rules_limits: voir « Règles du challenge » ci-dessous
compute: HF Jobs l4x1 (L4 24 GB) facturé à l'org ynov, resource group HACKATHON_ASUS `6b09693c78688af4256e8db8`. Celui du kit (`6b094bcd…`) renvoie 403. Commande : `hf jobs uv run --namespace ynov --resource-group-id 6b09693c78688af4256e8db8 --flavor l4x1 --timeout <2×ETA> --detach --secrets HF_TOKEN -v hf://datasets/denisjng/hackathon-work:/work [-e K=V] exp/NNN/train.py`. Suivi : `hf jobs ps -a --namespace ynov`, `hf jobs logs ynov/<id>`, `hf jobs cancel ynov/<id>`.
budget_cap: 600 € de crédits ynov (partagés, d'après un autre participant) ; L4 ≈ 0,80 $/h ; annuler tout job oublié ; crédits Claude = ceux de l'utilisateur, à économiser
max_parallel_jobs: 1
hf_user: denisjng
hf_org: ynov (facturation des jobs seulement, jamais de stockage)
hf_checkpoint_repo: denisjng/hackathon-lora (privé)

## Règles du challenge : ce que le plan respecte (non négociable)

| Règle (kit + code du Space) | Ce que le plan fait |
|---|---|
| Base `Qwen/Qwen3.5-0.8B` et aucune autre | Pas de levier « modèle plus gros » ni d'autre famille. Pas de modèle professeur, d'API ni d'autre LLM pour générer, traduire, noter ou filtrer. |
| LoRA (PEFT), QLoRA accepté | `LoraConfig` seulement. Pas de full fine-tune, pas de fusion. |
| Rendu = adapter seul via `save_pretrained` | Ni `merge_and_unload`, ni `save_pretrained_merged`, ni GGUF. |
| `base_model_name_or_path` = `"Qwen/Qwen3.5-0.8B"` | Chargement direct de `Qwen/Qwen3.5-0.8B` (pas Unsloth). Vérifié par le script. |
| Pas de `modules_to_save`, pas de tokens ajoutés | `target_modules` = couches linéaires d'attention et de MLP seulement. Tokenizer de la base inchangé. |
| safetensors bf16/fp16/fp32, 200 Mo max | `safe_serialization=True`, poids en bf16. Le rang `r` est choisi pour rester très en dessous de 200 Mo. |
| **Seules les données officielles** | Train, val et filtres viennent uniquement de `donnees.jsonl`. Pas de dictionnaire, de corpus ou de modèle de langue extérieur. Le classifieur de langue est entraîné sur `donnees.jsonl`. |
| Données synthétiques | **Interdites par défaut** : back-translation, pseudo-labels, auto-distillation, réécriture. Seulement si un organisateur l'autorise par écrit. |
| Scripts de job visibles par les autres participants (bucket `ynov/jobs-artifacts`) | Aucun secret dans les scripts : le token passe par `--secrets HF_TOKEN`. Les données sont lues depuis le dépôt privé monté. |
| Job HF : disque effacé à la fin | Chaque script finit par `push_to_hub("denisjng/…", private=True)`. |
| Dépôts sur **son compte, en privé**, jamais dans `ynov` | Checkpoints, bucket de travail et pack de reproductibilité : `denisjng/*` privés. `--namespace ynov` sert uniquement à facturer les jobs. |
| Vérifier avant de déposer | `uv run verifier_mon_lora.py <dossier>` lancé pour de vrai. On ne dépose que si le résultat est `RÉSULTAT : OK`. |
| 1 bench noté / 150 min, 1 dans la file | 5 créneaux dans la journée (plan ci-dessous). Chaque dépôt doit battre la val du précédent. |
| Contrôle complet 2 fois max | Utilisé 2 fois : sur le 2e dépôt, puis sur le candidat final. |
| Garde-fous culture et sécurité | Que de la traduction propre, LoRA léger (lr modéré, 1–2 époques), aucune donnée hors sujet. Si le contrôle complet montre un facteur < 0,995, on baisse r, le lr ou les époques. |
| Bench : gabarit fixe, base + `PeftModel`, tokenizer de la base | Entraînement au gabarit exact, préfixe `<think>\n\n</think>\n\n` du chat template, cible = traduction + `<|im_end|>`. |

## Plan de la journée (créneaux de dépôt espacés de 150 min)

| Créneau | Dépôt | Contenu |
|---|---|---|
| ≤ 12:30 | #1 baseline | LoRA sur `sft_v2`, 1 époque, réglages par défaut |
| ≥ 15:00 | #2 + contrôle complet | données v3 (étape F : filtrage par le LoRA #1) ou meilleur lr / nombre d'époques |
| ≥ 17:30 | #3 | meilleur levier des boucles (dosage, rang, époques) |
| ≥ 20:00 | #4 | meilleure config, éventuellement réentraînée sur train + val |
| ≥ 22:30 | #5 final + contrôle complet | dernier dépôt, score attendu vers 23:10, bien avant 23:59 |

Chaque créneau dépend de l'heure du dépôt précédent : prochain = dépôt précédent + 150 min. Un retard décale toute la suite. Il faut déposer dès que le créneau ouvre.

## Choices
card: recipes/llm.md
val_split: data/derived/val.jsonl (900 paires, 300/langue, gelée)
final_submission:
repro_pack:

## Data notes
- Voir data_strategy.md (§1 bis, §1 ter, §4) : v2 = 193 679 paires ; mélange sft_v2 = 114 737 exemples, br 44 %.
- `ofis_publik` : ~30 % de paires désalignées, plafonné à 8 k ; cible n°1 de l'étape F.
- `aina` contient de l'espagnol étiqueté ca, retiré par l'identification de langue.
- Chat template : le prompt de génération finit par `<think>\n\n</think>\n\n` ; eos = `<|im_end|>`.
