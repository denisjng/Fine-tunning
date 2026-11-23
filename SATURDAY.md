# Saturday 2026-11-28: competition checklist

## Hands-free route (recommended): set up once, then walk away

### One-time setup (any time before Saturday 09:00, about 15 minutes)
1. Install the Claude Code CLI in PowerShell. Either:
   - `irm https://claude.ai/install.ps1 | iex`, or
   - `npm install -g @anthropic-ai/claude-code`.

   Then run `claude` once and log in.
2. Run `pip install -U huggingface_hub`, then `hf auth login`, and paste your Hugging Face write token yourself.
3. Kaggle competition: put `kaggle.json` in `C:\Users\popes\.kaggle\` and accept the competition rules on the website.
4. Open `.claude\skills\compete\run_day.ps1` and set the `$PermissionArgs` line. This is your choice: it decides what the unattended runs may do without asking. The two options and their risks are listed above the line.
5. Fill every `TODO` in `launch.md`. If the platform only accepts web uploads, set `auto_submit: no`: unattended runs can't submit there, and you'll upload the files listed in `comp\logs\notes.md` yourself.

### Start (any time before 09:00; it waits until `start`)
From the Fine-tunning folder:

```powershell
powershell -ExecutionPolicy Bypass -File .claude\skills\compete\run_day.ps1
```

Leave the window open and the laptop on power. The script keeps Windows awake and starts a fresh Claude run every cycle until the final submission or midnight.

### While it runs (optional; you never have to touch it)
- Progress: `comp\logs\supervisor.log`, one line per cycle. Each run's full output is in `comp\logs\cycle-NNN.log`, and messages for you are in `comp\logs\notes.md`.
- Experiments and scores: `comp\experiments.md`.
- Stop it: create an empty file `comp\STOP`. The current run finishes and nothing new starts.

## Fallback: desktop route (if the CLI route fails)
1. Open Claude in the `Fine-tunning` folder and type `/loop /compete`.
2. In the first message: the competition URL or rules, the folder path, your budget, and "yes, you may submit on your own after every stage" (CLI or API platforms only).
3. When Claude says "good moment for a fresh session", open a new session and type `/loop /compete`. It resumes from the files.

## Deadlines (defaults; they move with `end`)
| Time | What |
|---|---|
| 12:30 | First submission |
| 20:00 | Loops stop, final run starts |
| 22:00 | Verify and pick the final submission |
| 23:00 | Final submission deadline |
