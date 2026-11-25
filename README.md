# Autopilote pour le hackathon de fine-tuning

Le skill Claude Code `/compete` mène le hackathon pour toi. Après le kick-off, tu lui donnes les infos du sujet, et il fait le reste :
- il lit les règles et adapte le plan ;
- il analyse les données ;
- il entraîne une baseline sur Hugging Face et la soumet ;
- il améliore le modèle en boucles, avec des agents en parallèle pour la recherche, l'analyse, le code et la revue de code ;
- il fait la soumission finale et prépare le dossier pour la vérification du top 3.

## Avant samedi (une fois, ~20 min)

1. **Compte Hugging Face avec ton adresse Ynov**, dans l'organisation de l'école : https://huggingface.co/join/ynov. **Envoie ton identifiant HF** à l'organisateur, par Teams ou en réponse au mail.
2. **Pose deux questions à l'organisateur :**
   - Un agent IA qui entraîne et soumet seul est-il autorisé, ou seulement l'aide pour coder ?
   - Combien de crédits GPU, et quels GPU sont permis ?

   Sans un oui clair à la première, utilise le mode guidé (section « Mode guidé » plus bas).
3. **Installe Claude Code (CLI)**, puis lance `claude` une fois **dans ce dossier**. Accepte les plugins du projet, puis vérifie avec `/plugin` que `data`, `mlflow`, `hf-cli`, `superpowers` et `ponytail` sont bien installés.
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
4. **Connexion Hugging Face avec le compte Ynov.** Tape le token toi-même :
   ```powershell
   pip install -U huggingface_hub
   hf auth login
   ```
5. **Outil local pour les helpers :**
   ```powershell
   pip install optuna==5.1.0
   ```
6. **Mode de permission.** Dans `.claude\skills\compete\run_day.ps1`, règle la ligne `$PermissionArgs`. Elle décide ce que Claude peut faire sans te demander ; les options et leurs risques sont écrits juste au-dessus.
7. **`launch.md` :** remplis la partie « Fill now » (dossier, nom de l'org HF, repo de checkpoints privé **dans ton espace à toi**, crédits). Laisse les champs `ASK`.

## Samedi matin

1. **9 h :** suis le kick-off sur Teams et note le sujet, les règles, la métrique, comment soumettre et la deadline.
2. Ouvre Claude dans ce dossier et tape `/compete`.
3. Colle tout : le lien, les règles, tes notes et les messages Teams.
4. Réponds à son unique message de questions, dont « je peux soumettre seul ? ».
5. Il résume le plan et lance l'autopilote dans une nouvelle fenêtre. Laisse-la ouverte, branche le chargeur et **ne ferme pas le capot**.

**Sur place à Nanterre :** l'autopilote se met en pause pendant le trajet du retour à 16 h, puis reprend quand tu rouvres le PC. Les entraînements continuent sur Hugging Face. Pour zéro pause, reste en ligne depuis chez toi.

## Pendant la journée (facultatif)

| Pour… | Regarde / fais |
|---|---|
| Suivre l'avancement | `<dossier>\logs\supervisor.log` |
| Voir les scores et les expériences | `<dossier>\experiments.md` |
| Voir la courbe du score | `<dossier>\agents\progress.png` |
| Lire les messages pour toi | `<dossier>\logs\notes.md` |
| Tout arrêter | Crée un fichier vide `<dossier>\STOP` |

Repères par défaut : première soumission vers 12 h 30, boucles jusqu'à 20 h, choix final à 22 h, dernière soumission avant minuit.

## Mode guidé, ou si l'autopilote plante

1. Crée `<dossier>\STOP` et attends « supervisor finished » dans `supervisor.log` : deux pilotes en même temps se marcheraient dessus.
2. Ouvre Claude dans ce dossier et tape `/loop /compete`. Il reprend depuis les fichiers.

## Après minuit

Le dossier de reproductibilité est poussé dans `<ton-compte>/<sujet>-final`, un repo privé. Si tu es dans le top 3, c'est ce repo que tu partages avec les organisateurs pour la vérification des 29 et 30 novembre.
