# Fine-tuning competition autopilot

The `/compete` Claude Code skill runs a one-day fine-tuning competition for you, start to finish:
- reads the rules;
- analyses the data;
- trains a baseline and submits it;
- improves the model in loops, researching techniques and changing strategy as results come in;
- makes the final submission.

It handles any modality (LLM, text, vision, audio, tabular).

## Before launch (once, ~15 min)

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
3. **Kaggle competitions only.** Put `kaggle.json` in `C:\Users\<you>\.kaggle\`, and accept the competition rules on the website.
4. **Permission mode.** In `.claude\skills\compete\run_day.ps1`, set the `$PermissionArgs` line. It decides what Claude may do without asking. The options and their risks are written above it.
5. **Fill `launch.md`.** Every `TODO`: competition URL, competition folder, budget, `auto_submit`, Hugging Face checkpoint repo. Set `auto_submit: no` if the platform only takes web uploads.

## Launch

From this folder, any time before the start time (it waits until `start` in `launch.md`):

```powershell
powershell -ExecutionPolicy Bypass -File .claude\skills\compete\run_day.ps1
```

Keep the window open and the laptop on power. Then you can walk away.

## While it runs (optional)

| To… | Look at / do |
|---|---|
| See progress | `<competition folder>\logs\supervisor.log` |
| See scores and experiments | `<competition folder>\experiments.md` |
| Read messages for you | `<competition folder>\logs\notes.md` |
| Stop everything | Create an empty file `<competition folder>\STOP` |

Default times: first submission 12:30, loops stop 20:00, final pick 22:00, final submission 23:00. They shift with `end` in `launch.md`.

## If the script fails

Open Claude in this folder and type `/loop /compete`. In the first message, give:
- the competition URL;
- the folder;
- your budget;
- "yes, you may submit on your own" (if you want that).

It resumes from the files at any point.
