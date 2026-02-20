# Private Deployment Guide (Beginner-Friendly)

This guide helps you deploy ACE so **only you** can access it.

## What this setup gives you

- Frontend + backend + MongoDB in Docker containers.
- HTTPS support via Caddy (automatic certs if you use a real domain).
- A login wall (basic auth) in front of the app.
- You can still use your in-app auth (signup/login) after that.

---

## 0) Prerequisites

Install these first:

- Docker
- Docker Compose plugin (`docker compose`)

Check:

```bash
docker --version
docker compose version
```

Also make sure you are on the branch that contains private deployment files:

```bash
git branch --show-current
ls
```

You should see both `DEPLOY_PRIVATE.md` and a `deploy/` folder.

If you do **not** see them, switch to the branch that contains the beta/private deployment work and pull latest changes:

```bash
git checkout <your-beta-branch>
git pull origin <your-beta-branch>
```

If you ran this command and got no output:

```bash
git log --all --oneline --grep="private deployment stack" -n 5
```

that simply means your current local branches do not contain that commit yet. In that case, use the branch that has deployment files already committed, or add the deployment files on your active beta branch before continuing.

---

## 1) Configure environment

From repo root:

```bash
cd deploy
cp .env.private.example .env.private
```

### If you see this error

```
cd: no such file or directory: deploy
cp: .env.private.example: No such file or directory
```

You are on a branch that does not include private deployment files yet. Run:

```bash
cd ~/ACE
git branch --show-current
git branch -r
git checkout part2
git pull origin part2
ls
```

If `deploy/` is still missing after that, your remote branch does not include the deployment files yet. In that case, pull the branch/PR that adds:

- `DEPLOY_PRIVATE.md`
- `deploy/docker-compose.private.yml`
- `deploy/.env.private.example`
- `deploy/Caddyfile`

Then rerun Step 1.

Open `deploy/.env.private` and edit:

- `DOMAIN`
- `PUBLIC_BASE_URL`
- `EMERGENT_LLM_KEY`
- `CORS_ORIGINS`

### For local/private testing on your own computer

Use:

- `DOMAIN=localhost`
- `PUBLIC_BASE_URL=http://localhost`
- `CORS_ORIGINS=http://localhost`

### For internet deployment (private to you)

Use your own domain (for example `ace.yourdomain.com`):

- `DOMAIN=ace.yourdomain.com`
- `PUBLIC_BASE_URL=https://ace.yourdomain.com`
- `CORS_ORIGINS=https://ace.yourdomain.com`

---

## 2) Create the basic-auth password hash

This is the first lock (before the app even opens).

```bash
docker run --rm caddy:2.8 caddy hash-password --plaintext "your-very-strong-password"
```

Copy the output and paste it into `BASIC_AUTH_HASH=` in `deploy/.env.private`.

**Important:** bcrypt hashes contain `$`. In `.env.private`, escape each `$` as `$$` so Docker Compose does not treat it as a variable.

Example:

```env
BASIC_AUTH_HASH=$$2a$$14$$...
```

Also set `BASIC_AUTH_USER` to your preferred username.

---

## 3) Start the app

From `deploy/` folder:

```bash
docker compose --env-file .env.private -f docker-compose.private.yml up -d --build
```

Check containers:

```bash
docker compose --env-file .env.private -f docker-compose.private.yml ps
```

Open browser:

- `http://localhost` (local)
- or your domain URL (server deployment)

You should first see the browser login prompt (basic auth), then your ACE app.

---

## 4) Create your app user (only you)

1. Sign up inside the app with your email.
2. Log in.

If you want access to `/admin`, set yourself as admin in MongoDB.

### Make yourself admin (one-time)

Replace `YOUR_EMAIL` with the same email you used to sign up:

```bash
docker compose --env-file .env.private -f docker-compose.private.yml exec mongo mongosh "mongodb://mongo:27017/ace_private" --eval 'db.users.updateOne({email:"YOUR_EMAIL"}, {$set:{is_admin:true}})'
```

Now re-login and open `/admin`.

---

## 5) Keep it private (important)

- Do **not** share your URL.
- Keep strong passwords (basic auth + app account).
- If deployed on a VPS, add firewall allowlist to your IP only.
- Keep `.env.private` secret and never commit it.

---

## 6) Update / restart commands

From `deploy/`:

```bash
# Pull latest code first, then rebuild
docker compose --env-file .env.private -f docker-compose.private.yml up -d --build

# View logs
docker compose --env-file .env.private -f docker-compose.private.yml logs -f backend
docker compose --env-file .env.private -f docker-compose.private.yml logs -f frontend
docker compose --env-file .env.private -f docker-compose.private.yml logs -f caddy

# Stop
docker compose --env-file .env.private -f docker-compose.private.yml down
```

---

## 7) Troubleshooting

### I get CORS errors
Check `CORS_ORIGINS` in `.env.private` exactly matches your frontend URL.

### Chat fails with AI error
Check `EMERGENT_LLM_KEY` is valid and present.

### Basic auth keeps rejecting
Regenerate hash and replace `BASIC_AUTH_HASH` (ensure `$` is escaped as `$$` in `.env.private`).


### Build fails with `failed to read dockerfile: open Dockerfile: no such file or directory`
This means your local branch is missing one or both Docker build files.

From repo root, verify:

```bash
ls backend/Dockerfile
ls frontend/Dockerfile
ls frontend/nginx.conf
```

If any file is missing, pull the branch that contains deployment assets and re-run the build:

```bash
git checkout <deployment-branch>
git pull origin <deployment-branch>
cd deploy
docker compose --env-file .env.private -f docker-compose.private.yml up -d --build
```

### `frontend/Dockerfile` or `frontend/nginx.conf` is missing (or is empty)
If you ran:

```bash
ls -la frontend/Dockerfile
ls -la frontend/nginx.conf
wc -c frontend/Dockerfile frontend/nginx.conf
```

and got `No such file or directory`, or your build output shows `transferring dockerfile: 2B`, recover both files with one command:

```bash
./deploy/scripts/recover_missing_frontend_files.sh
```

If you are currently inside `deploy/`, run this instead:

```bash
./scripts/recover_missing_frontend_files.sh
```

If you see `No such file or directory` for both paths, your local branch does not include the script yet. Pull latest changes on your active branch, or skip directly to manual file creation below.

If you prefer manual creation, use the file contents below.

Create `frontend/Dockerfile`:

```Dockerfile
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    else npm install; fi

COPY . .

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}

RUN if [ -f yarn.lock ]; then yarn build; else npm run build; fi

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
```

Create `frontend/nginx.conf`:

```nginx
server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri /index.html;
  }
}
```

Then rebuild from `deploy/`:

```bash
docker compose --env-file .env.private -f docker-compose.private.yml up -d --build
```

### I already have `frontend/Dockerfile` (for example: `-rw-r--r-- ... frontend/Dockerfile`)
Great. That means frontend Docker build config exists.

Run this next from repo root:

```bash
ls -la frontend/nginx.conf
```

- If it exists, start/rebuild the stack:

  ```bash
  cd deploy
  docker compose --env-file .env.private -f docker-compose.private.yml up -d --build
  docker compose --env-file .env.private -f docker-compose.private.yml ps
  ```

- If it is missing, create it with the `frontend/nginx.conf` block above, then run the same compose commands.

This repo's compose file now pins explicit Dockerfile paths (`backend/Dockerfile`, `frontend/Dockerfile`) so the build is less sensitive to path confusion.

### No HTTPS certificate
You need a real domain pointing to your server's public IP for automatic TLS.

---

## 8) What to do next

Once private deployment works, next improvements are:

1. Automated backups for MongoDB volume.
2. Add fail2ban/rate limiting.
3. Add monitoring/alerts.
4. Later, remove basic auth and rely on production-grade auth if you go public.
