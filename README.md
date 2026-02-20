# ACE (Academic Clarity Engine)

ACE is a Penn State-focused academic advisor assistant with:

- FastAPI backend (`backend/`)
- React frontend (`frontend/`)
- Policy vault and admin tools

## Private deployment (recommended first)

If you are the only user right now, start with the private deployment guide:

- [DEPLOY_PRIVATE.md](./DEPLOY_PRIVATE.md)
If your local branch is missing frontend deploy files, run:

```bash
./deploy/scripts/recover_missing_frontend_files.sh
```

(If you are already in `deploy/`, use `./scripts/recover_missing_frontend_files.sh`.)

