# How we work

**`main` is the reviewed, always-working version.** Nobody commits to it directly. Everything goes through a branch and a pull request (PR).

## Branches
Name branches `<name>/<task>`, one branch per task:

Examples: `divya/colab-setup`, `faranak/diagnostic-cases`, `hanieh/benchmark-cases`.

## Workflow
1. **Start from the latest main:** `git checkout main && git pull`, then `git checkout -b <name>/<task>`.
2. **Commit small and often**, with clear messages ("add Q18 case write-up", not "update").
3. **Push** your branch: `git push -u origin <name>/<task>`.
4. **Open a PR into `main`** and fill in the template. Request a review from at least **one** teammate.
5. **The reviewer checks it runs and makes sense**, then approves. The **author merges** using *Squash and merge*.
6. **Delete the branch** after merging and start the next task from a fresh `main`.

## Working from Colab
- Open a notebook from GitHub: *File → Open notebook → GitHub*, then pick the repo and your branch.
- Save back: *File → Save a copy in GitHub*, then choose **your branch**, never `main`.
- Notebooks have **one owner each**. Don't edit someone else's notebook; copy it or ask the owner.
- Before committing, *Edit → Clear all outputs* unless the outputs are the deliverable. This keeps diffs readable.

## Never commit
API keys, `.env`, indexes (`*.pkl`, `*.sqlite3`), `Baseline.zip` or the corpus. These live on Drive or in Colab Secrets. `.gitignore` covers most of it, but check `git status` before you commit.

## Results
Each run gets its own folder `results/<YYYYMMDD_HHMM>_<who>_<what>/` with `run_meta.json`. Never overwrite a previous run: the report's numbers must trace back to a saved run.

## AI tools
Add a line to `docs/ai_use_log.md` whenever an AI tool meaningfully helped (code, benchmark candidates, text). The final report needs it.
