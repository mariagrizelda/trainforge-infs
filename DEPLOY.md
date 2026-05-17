# Deploying TrainForge to a UQCloud Zone

This walks through getting TrainForge running on your UQCloud Zone at
`https://infs3202-YOURCODE.uqcloud.net/trainforge/`, with Gunicorn proxied
behind Nginx and Google OAuth working against the public URL.

All commands assume you are SSHed into the zone:

```bash
ssh sXXXXXXX@infs3202-YOURCODE.zones.eait.uq.edu.au
```

Replace **`sXXXXXXX`** with your UQ username and **`YOURCODE`** with the
zone code you can read from <https://coursemgr.uqcloud.net/infs3202>.

---

## 1. Get the code onto the zone

The convention from applied class 2 is that Django projects live under
`/var/www/djangoapps/`, never inside `htdocs`.

```bash
cd /var/www
mkdir -p djangoapps && cd djangoapps
git clone <YOUR_GIT_REMOTE> trainforge
cd trainforge
```

If you do not have a remote yet, you can SFTP the project directory across
with WinSCP / Cyberduck and skip the `git clone` step.

## 2. Python virtual environment

UQ Cloud ships Python 3.14:

```bash
python3.14 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Production `.env`

Create `/var/www/djangoapps/trainforge/.env` from `.env.example` and fill
it in:

```dotenv
DJANGO_SECRET_KEY=<paste a long random string>
DJANGO_DEBUG=0

OPENAI_API_KEY=<your UQ-provided key>
OPENAI_MODEL=gpt-5.4-mini

GOOGLE_OAUTH_CLIENT_ID=<from step 7>
GOOGLE_OAUTH_CLIENT_SECRET=<from step 7>

URL_PREFIX=trainforge
ALLOWED_HOSTS=infs3202-YOURCODE.uqcloud.net
CSRF_TRUSTED_ORIGINS=https://infs3202-YOURCODE.uqcloud.net
```

Setting `URL_PREFIX=trainforge` is what mounts the whole app under
`/trainforge/` and adjusts `STATIC_URL` and `MEDIA_URL` to match.

## 4. Migrate and collect static

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed              # optional: demo trainer + admin
```

After this you should have:

- `db.sqlite3` populated
- `staticfiles/` containing all CSS, fonts, and images

While still SSHed in, update the Sites row so allauth uses the right
domain for the Google callback URL:

```bash
python manage.py shell <<'PY'
from django.contrib.sites.models import Site
s, _ = Site.objects.get_or_create(pk=1)
s.domain = "infs3202-YOURCODE.uqcloud.net"
s.name = "TrainForge"
s.save()
PY
```

## 5. Gunicorn systemd service

Install Gunicorn into the venv:

```bash
source venv/bin/activate
pip install gunicorn
```

Create the service file (sudo required):

```bash
sudo nano /etc/systemd/system/trainforge.service
```

Paste:

```ini
[Unit]
Description=Gunicorn for TrainForge
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/djangoapps/trainforge
EnvironmentFile=/var/www/djangoapps/trainforge/.env

ExecStart=/var/www/djangoapps/trainforge/venv/bin/gunicorn \
          --workers 2 \
          --bind 127.0.0.1:8002 \
          trainforge.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

The port `8002` is just a convention. Applied class 2's resume builder
already uses `8001`, so pick something free on your zone.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trainforge
sudo systemctl start trainforge
sudo systemctl status trainforge      # should say "active (running)"
```

If it does not start, view the log:

```bash
sudo journalctl -u trainforge.service --no-pager -l | tail -50
```

## 6. Nginx reverse proxy

Edit the site config:

```bash
sudo nano /etc/nginx/sites-enabled/https-site
```

Add this block **before the final `}`** of the `server { ... }`:

```nginx
location /trainforge/static/ {
    alias /var/www/djangoapps/trainforge/staticfiles/;
    access_log off;
    expires 7d;
}

location /trainforge/media/ {
    alias /var/www/djangoapps/trainforge/media/;
    access_log off;
    expires 7d;
}

location /trainforge/ {
    proxy_pass http://127.0.0.1:8002;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
}
```

Check + reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Open `https://infs3202-YOURCODE.uqcloud.net/trainforge/` in a browser.
You should see the landing page.

## 7. Google OAuth on the live URL

Follow applied class 8's Google API Console steps, but use the live
callback URL:

1. <https://console.cloud.google.com/apis/credentials> → **Create
   credentials → OAuth client ID → Web application**.
2. Authorised redirect URI:

   ```
   https://infs3202-YOURCODE.uqcloud.net/trainforge/accounts/google/login/callback/
   ```
3. OAuth consent screen → **App name = TrainForge**, set support email,
   add your UQ Gmail address under **Test users** (or publish the app).
4. Copy the client id and secret into the live `.env`:

   ```dotenv
   GOOGLE_OAUTH_CLIENT_ID=...
   GOOGLE_OAUTH_CLIENT_SECRET=...
   ```
5. Restart the service so it picks the new env up:

   ```bash
   sudo systemctl restart trainforge
   ```

The "Continue with Google" button on the login and signup pages should
now bounce through to Google's consent screen ("Sign in to TrainForge")
and back into the app.

## 8. After code changes

```bash
cd /var/www/djangoapps/trainforge
source venv/bin/activate
git pull
pip install -r requirements.txt          # only if requirements changed
python manage.py migrate                 # only if there are new migrations
python manage.py collectstatic --noinput # only if static files changed
sudo systemctl restart trainforge
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| 502 Bad Gateway at `/trainforge/` | Gunicorn isn't running. `sudo systemctl status trainforge` + `journalctl -u trainforge`. |
| 404 on every `/trainforge/static/*.css` | `collectstatic` not run, or the nginx `alias` path doesn't match `STATIC_ROOT`. |
| Google sign-in redirects to `redirect_uri_mismatch` | The redirect URI in Google Cloud Console must be **exactly** `https://infs3202-YOURCODE.uqcloud.net/trainforge/accounts/google/login/callback/` (trailing slash, https, the zone hostname). |
| Logs say `DisallowedHost` | Add the zone hostname to `ALLOWED_HOSTS` in `.env` and restart. |
| CSRF verification failed on POST | Add `https://infs3202-YOURCODE.uqcloud.net` to `CSRF_TRUSTED_ORIGINS` in `.env` and restart. |
| Login redirects to `http://` instead of `https://` | `ACCOUNT_DEFAULT_HTTP_PROTOCOL` is set from `DEBUG`. Make sure `DJANGO_DEBUG=0` in production. |
