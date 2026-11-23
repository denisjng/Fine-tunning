# Saturday 2026-11-28: competition checklist

## Before 09:00
- [ ] Laptop on power, phone notifications on, food ready.
- [ ] Hugging Face account with credits and a write token at hand (huggingface.co/settings/tokens).
- [ ] Kaggle competition: `kaggle.json` in `C:\Users\<you>\.kaggle\`, and the competition rules accepted on the website.
- [ ] Optional: if the rules or data are already published, run `/compete` early. Setup and data analysis can happen before 09:00.

## 09:00
1. Create a folder for the competition, e.g. `C:\Users\popes\Desktop\Fine-tunning\comp`.
2. Open Claude Code in the `Fine-tunning` folder and type `/loop /compete`.
3. In the first message, paste the competition URL or rules and say:
   - the competition folder path;
   - your budget cap (e.g. "$40");
   - "yes, you may submit on your own after every stage" (only if the platform has a CLI or API).
4. When asked, run `hf auth login` yourself and paste your token. Never paste it into the chat.

## During the day
- Watch the status line: best val, submissions used, loops left, next deadline.
- Steer any time by typing, e.g. "try a bigger model next" or "stop".
- When Claude says "good moment for a fresh session": open a new session in the same folder and type `/loop /compete`. It resumes from the files.
- Emergency, at any time: ask "submit best now". `submissions/best.*` is always the current best valid file.

## Deadlines (defaults; they move if the organizer's deadline is not midnight)
| Time | What |
|---|---|
| 12:30 | First submission |
| 20:00 | Loops stop, final run starts |
| 22:00 | Verify and pick the final submission |
| 23:00 | Final submission deadline |
