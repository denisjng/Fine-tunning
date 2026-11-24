# Fine-tuning competition autopilot

The `/compete` Claude Code skill runs a one-day fine-tuning competition for you. In the morning you give it the competition information, and it does the rest:
- reads the rules and adapts the plan;
- analyses the data;
- trains a baseline and submits it;
- improves the model in loops, researching techniques and changing strategy as results come in, with parallel helper agents (each using the matching Claude skill) for research, analysis, code prep, code review and tracking;
- makes the final submission.

It handles any modality (LLM, text, vision, audio, tabular).

## Before the day (once, ~15 min)

1. **Install the Claude Code CLI**, then run `claude` once and log in:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
2. **Hugging Face login.** Type the token yourself:
   ```powershell
   pip install -U huggingface_hub
   hf auth login
   ```
   Your account needs GPU credits.
3. **Kaggle competitions only.** Put `kaggle.json` in `C:\Users\<you>\.kaggle\`. Accept the competition rules on the website once they are published.
4. **Permission mode.** In `.claude\skills\compete\run_day.ps1`, set the `$PermissionArgs` line. It decides what Claude may do without asking. The options and their risks are written above it.
5. **`launch.md`:** fill the "Fill now" part (folder, budget, checkpoint repo). Leave the `ASK` fields alone.

## In the morning

1. Open Claude in this folder and type `/compete`.
2. Paste everything you received for the competition: link, rules, data, deadlines, submission method.
3. Answer its one follow-up message. Most questions come with a default; the only one without is whether it may submit on its own.
4. It summarises the plan and starts the autopilot in a new window. Keep that window open and the laptop on power, then walk away.

## While it runs (optional)

| To… | Look at / do |
|---|---|
| See progress | `<competition folder>\logs\supervisor.log` |
| See scores and experiments | `<competition folder>\experiments.md` |
| See the score-over-time chart | `<competition folder>\agents\progress.png` |
| Read messages for you | `<competition folder>\logs\notes.md` |
| Stop everything | Create an empty file `<competition folder>\STOP` |

Default times: first submission 12:30, loops stop 20:00, final pick 22:00, final submission 23:00. They shift with the organizer's deadline.

## If the autopilot fails

Open Claude in this folder and type `/loop /compete`. It resumes from the files and runs in that chat instead.
