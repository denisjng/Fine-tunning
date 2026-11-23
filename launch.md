# Launch file for the hands-free day (run_day.ps1)
# Fill every field that says TODO, then start the script. Claude reads this instead of asking you.

competition: TODO competition URL, or name and Kaggle slug
competition_folder: TODO e.g. C:\Users\popes\Desktop\Fine-tunning\comp
start: 2026-11-28 09:00
end: 2026-11-29 00:00
budget_cap: TODO max GPU spend, e.g. 40 USD
max_parallel_jobs: 1
auto_submit: TODO yes or no. yes = Claude may submit by CLI or API after every stage. Web-upload competitions cannot be submitted unattended.
hf_checkpoint_repo: TODO <your-hf-user>/<name> (private), or none
notes: none

## Rules text (optional)
Paste the competition rules here if they are not reachable from the URL.
