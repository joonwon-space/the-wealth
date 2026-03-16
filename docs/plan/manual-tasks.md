# Manual Tasks

Items requiring user action. Complete these before related auto-tasks can proceed.

---

## Python 3.10+ Upgrade (Milestone 8)
- [ ] Install Python 3.10+ via Homebrew: `brew install python@3.12`
- [ ] Recreate venv: `python3.12 -m venv backend/venv`
- [ ] Reinstall deps: `pip install -r backend/requirements.txt`
- [ ] Then run `/auto-task` to complete python-multipart upgrade and syntax cleanup

## Deployment (Milestone 10)
- [ ] Create Vercel account and link to GitHub repo (frontend)
- [ ] Create Railway/Fly.io account for backend deployment
- [ ] Set up production PostgreSQL and Redis instances
