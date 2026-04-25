# Quick Instructions (GitHub + Hugging Face Space)

This is the exact command playbook used in this project.

## 0) Repo location

```powershell
cd D:\meta-scalar-hack
```

## 1) Check remotes

```powershell
git remote -v
```

Expected important remotes:
- `origin` -> GitHub repo
- `hf` -> Hugging Face Space repo

If `hf` is missing:

```powershell
git remote add hf https://huggingface.co/spaces/joynnayvedya/disaster-response-openenv.git
```

## 2) Safe push flow (normal deploy)

```powershell
git status
git checkout main
git pull origin main
git add -A
git commit -m "Update project"
git push origin main
git push hf main
```

If there are no new changes:

```powershell
git push origin main
git push hf main
```

## 3) If HF push says non-fast-forward

This means HF `main` has commits your local branch does not.

```powershell
git fetch hf
git checkout main
git merge hf/main
git push hf main
```

If conflicts appear, resolve then:

```powershell
git add -A
git commit -m "Resolve merge from hf/main"
git push hf main
```

## 4) If HF rejects push due to binary file

HF Space remote can reject raw binaries (example: `image.png`).

Quick workaround: remove that file from tracked changes and push again.

```powershell
git rm --cached image.png
del image.png
git add -A
git commit -m "Remove binary file for HF push"
git push origin main
git push hf main
```

If file does not exist locally, skip `del image.png`.

## 5) Local environment test commands

Use `py -m pip` on Windows (not plain `pip`):

```powershell
py -m pip install -e .
py smoke_test.py
```

Run local server:

```powershell
py -m server.app
```

Expected:
- Uvicorn running on `http://0.0.0.0:8000`

## 6) Local API sanity checks (PowerShell)

PowerShell `curl` alias is not Linux curl. Use one of these:

```powershell
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/reset"
```

or:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/reset"
```

## 7) Local URLs to open

- `http://127.0.0.1:8000/web/`
- `http://127.0.0.1:8000/ui/`

## 8) Pre-push check when branch is ahead

If your branch says "ahead by N commits", inspect exactly what will go in:

```powershell
git log --oneline origin/main..HEAD
git diff --name-only origin/main..HEAD
```

Local run gate before merge/push to `main`:

```powershell
py smoke_test.py
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/reset"
```

If both pass, safe merge/deploy flow:

```powershell
git push origin round2-training-proof
git checkout main
git pull origin main
git merge round2-training-proof
git push origin main
git push hf main
```

## 9) How to verify HF deploy worked

1. Open your Space page.
2. Go to `Logs`.
3. Confirm build starts and container becomes `Running`.
4. Open Space URL and test reset/UI.

## 10) If Space breaks after push

### A) Read logs first
- Build error -> fix dependency/config, push again.
- Runtime error -> fix code, push again.

### B) Fast rollback to known-good commit

```powershell
git log --oneline -n 10
git checkout <GOOD_COMMIT_SHA>
git checkout -b hotfix-rollback
git push hf hotfix-rollback:main
```

## 11) Token safety (important)

- Never keep HF token embedded in remote URLs.
- If exposed, revoke and create a new token immediately.
- Keep remote URL clean:

```powershell
git remote set-url hf https://huggingface.co/spaces/joynnayvedya/disaster-response-openenv.git
```

---

If anything fails, copy the exact terminal error and debug from the first error line.
