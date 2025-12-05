**Deployment Guide — tasker-backend**

This document describes how to deploy the `tasker-backend` Django application in development and production. It covers local startup, environment variables, database considerations for the legacy schema, and two recommended production approaches: (1) gunicorn + nginx + systemd, and (2) Docker Compose.

**Prerequisites**
- Python 3.11+ (use pyenv/venv)
- pip (or pipx)
- MySQL server accessible to the application (legacy schema expects existing tables)
- Git
- For production: nginx, systemd (Linux), or Docker & Docker Compose

**Repository layout (relevant parts)**
- `manage.py` — Django entrypoint
- `backend/` — Django project settings and urls
- `apps/` — Django apps: `accounts`, `tasks`, `projects`, etc.
- `requirements.txt` — Python dependencies (if present)

IMPORTANT: Legacy tables are now fully managed by Django. Run `python manage.py migrate` on new environments to create the schema and seed baseline data (default `admin` user plus task/project status rows). If you already have a legacy database, back it up before migrating so you can reconcile differences.

**Environment**
Create a `.env` or environment variables for production. Example minimal variables (adjust to your environment):

- `DJANGO_SETTINGS_MODULE=backend.settings`
- `SECRET_KEY=replace-with-a-secure-secret`
- `DEBUG=False`
- `ALLOWED_HOSTS=example.com,api.example.com`
- `DATABASE_URL=mysql://dbuser:dbpassword@dbhost:3306/dbname`  # or configure DB settings in settings
- `CORS_ALLOWED_ORIGINS=http://localhost:3000` (dev)
- `SIMPLE_JWT_ACCESS_TOKEN_LIFETIME=3600` (seconds)

Example `.env` snippet:

```env
DJANGO_SETTINGS_MODULE=backend.settings
SECRET_KEY=changeme_to_a_secret
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,mydomain.example
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306
DATABASE_NAME=taskerdb
DATABASE_USER=taskeruser
DATABASE_PASSWORD=s3cret
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

How the app authenticates tokens/cookies:
- The project uses `rest_framework_simplejwt`. Tokens may be delivered in Authorization header or as `access_token`/`refresh_token` cookies. There is middleware that maps cookie to Authorization header for DRF.

Database notes (legacy):
- Tables are now managed by Django migrations. Running `python manage.py migrate` will create the full schema.
- The `accounts` app seeds three roles (`Admin`, `Manager`, `User`) and a default `admin` user (`admin@example.com` / `secret123`, change immediately).
- `tasks` and `projects` apps seed baseline statuses (`todo`, `in progress`, `completed`).
- If you still rely on an existing legacy database, verify table/column mappings before migrating and reconcile data after migration.

Local development (quickstart)

1. Create and activate a virtualenv (macOS/zsh):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Create `.env` with local DB settings and SECRET_KEY settings or ensure `backend/settings.py` points to local DB.

3. Apply migrations (creates tables, seeds default roles/statuses/admin user):

```bash
python manage.py migrate
```

4. Run Django server:

```bash
# from project root
python manage.py runserver
```

5. Open API at `http://127.0.0.1:8000/` and test endpoints.

Production: gunicorn + nginx + systemd (Linux)

1. Create a system user to run the app (optional):

```bash
sudo useradd -r -m -U -d /opt/tasker -s /bin/false tasker
```

2. Deploy code to server (e.g., `/opt/tasker/current`) and create a Python virtualenv under that user.

3. Install dependencies in venv:

```bash
python -m venv /opt/tasker/venv
source /opt/tasker/venv/bin/activate
pip install --upgrade pip
pip install -r /path/to/requirements.txt
```

4. Apply migrations (creates tables, seeds default roles/statuses/admin user) and collect static files (if applicable):

```bash
export DJANGO_SETTINGS_MODULE=backend.settings
export SECRET_KEY=...  # and other env vars
python manage.py migrate
python manage.py collectstatic --noinput
```

5. Create a `gunicorn` systemd service file (`/etc/systemd/system/tasker.service`):

```ini
[Unit]
Description=Gunicorn instance to serve tasker-backend
After=network.target

[Service]
User=tasker
Group=www-data
WorkingDirectory=/opt/tasker/current
Environment=DJANGO_SETTINGS_MODULE=backend.settings
Environment=SECRET_KEY=YOUR_SECRET
Environment=DATABASE_HOST=127.0.0.1
ExecStart=/opt/tasker/venv/bin/gunicorn backend.wsgi:application \
    --workers 3 --bind unix:/run/tasker.sock --log-level=info

[Install]
WantedBy=multi-user.target
```

Then start/enable:

```bash
sudo systemctl daemon-reload
sudo systemctl start tasker
sudo systemctl enable tasker
```

6. Configure nginx to proxy to the unix socket and serve TLS. Example nginx server block:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location /static/ {
        alias /opt/tasker/current/static/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/tasker.sock;
    }
}
```

- Configure TLS with certbot or your SSL provider and redirect HTTP to HTTPS.
- Ensure `ALLOWED_HOSTS` contains your domain(s).

Production: Docker Compose (recommended for simple deployments)

Create a `Dockerfile` and `docker-compose.yml` (example sketch):

Dockerfile (very brief):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install -r requirements.txt
ENV PATH="/opt/venv/bin:$PATH"
CMD ["gunicorn", "backend.wsgi:application", "-b", "0.0.0.0:8000"]
```

docker-compose.yml (simplified):

```yaml
version: '3.8'
services:
  web:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - db
  db:
    image: mysql:8
    environment:
      MYSQL_DATABASE: taskerdb
      MYSQL_USER: tasker
      MYSQL_PASSWORD: example
      MYSQL_ROOT_PASSWORD: rootpass
    volumes:
      - db-data:/var/lib/mysql
volumes:
  db-data:
```

Notes:
- With Docker you still must ensure the legacy DB schema is present. You may want to mount a SQL initialization script or run a migration container to load the legacy dump.
- Use `docker-compose up -d` to start.

Security & operational notes
- Use `DEBUG=False` in production and set a strong `SECRET_KEY`.
- Change the seeded `admin` password immediately after first login (`admin@example.com` / `secret123`).
- Set `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` when serving over HTTPS.
- Use `ALLOWED_HOSTS` to restrict hosts.
- Consider setting `SameSite=None` and `Secure` flags for cookies if using cross-site frontend with credentials.
- To revoke tokens on password change consider using `rest_framework_simplejwt.token_blacklist` or other revocation strategies.

Troubleshooting
- No projects/tasks returned:
  - Verify the DB contains rows and that `deleted_at` is NULL for active rows.
  - For legacy tables, check that `db_table` and `db_column` in models match the real schema.
  - Check logs (gunicorn or runserver) for exceptions.

- Authentication failures when using cookies:
  - Ensure frontend sends cookies with credentials: `fetch(..., { credentials: 'include' })` or `axios({ withCredentials: true })`.
  - Ensure `CORS_ALLOW_CREDENTIALS = True` and the origin is listed in `CORS_ALLOWED_ORIGINS`.

Testing
- Use the provided endpoints to register a user, login (and inspect response cookies), then call protected endpoints with the cookie or header.

Maintenance & next steps
- Add unit and integration tests around auth flows (cookie vs header), role-based permissions, and legacy schema behavior.
- Consider adding a management command to validate legacy schema mappings at startup (check required columns exist and types are compatible).

Contact / Support
- If you have CI/CD or platform-specific (GCP/Azure/ECS) deployment targets, I can add examples for Github Actions, Azure Pipelines, or Kubernetes manifests.

---
This file was generated to provide a practical deploy checklist and commands for `tasker-backend`. If you want a shorter quickstart README (or a configured `docker-compose.yml` and `Dockerfile` committed), tell me which approach you prefer and I will add it to the repo.
