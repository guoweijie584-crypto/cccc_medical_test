# Server Deployment

This project is easiest to deploy on a Linux server with `systemd` and `nginx`.

## What Actually Runs

You need these long-running services:

1. `CCCC daemon`
2. `Memory Palace` backend
3. `CCCC Web`
4. `api_server.py`

You also need one one-shot initialization step:

5. `bootstrap_cccc_native.py`

## Why This Repo Was Patched

This repo vendors a patched `cccc` runtime under:

```bash
cccc_medical-main/src/cccc
```

Without an explicit guard, Python can import `cccc` from global `site-packages`.
The project now includes:

- `src/cccc_native/vendored_cccc.py`
- `scripts/run_cccc_daemon.py`
- `scripts/run_cccc_web.py`

Those entrypoints force the vendored `cccc` copy to the front of `sys.path` and
also export it back into `PYTHONPATH` for child processes.

Keep `PYTHONPATH` set on the server anyway as a second guardrail.

## Recommended Layout

```bash
/srv/cccc_test/
  app/     # this repo
  venv/    # Python virtualenv
```

## 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv nodejs npm nginx

cd /srv/cccc_test/app
python3.11 -m venv /srv/cccc_test/venv
source /srv/cccc_test/venv/bin/activate

pip install -r requirements.txt
pip install -r Memory-Palace-main/backend/requirements.txt
```

## 2. Build the UI

The React UI source lives under `cccc_medical-main/web`, but its production
build output is written into vendored CCCC web assets.

```bash
cd /srv/cccc_test/app/cccc_medical-main/web
npm ci
npm run build
```

## 3. Create the Runtime Env File

```bash
sudo cp /srv/cccc_test/app/deploy/server.env.example /etc/cccc-test.env
sudo nano /etc/cccc-test.env
```

At minimum, set:

- `PROJECT_ROOT`
- `VENV_DIR`
- `PYTHONPATH`
- `MCP_API_KEY`
- `LLM_API_KEY`
- `LLM_API_BASE`
- `LLM_MODEL`

## 4. Install systemd Units and the One-Command Launcher

```bash
sudo cp /srv/cccc_test/app/deploy/systemd/*.service /etc/systemd/system/
sudo cp /srv/cccc_test/app/deploy/systemd/*.target /etc/systemd/system/
sudo install -m 0755 /srv/cccc_test/app/deploy/bin/cccc-test /usr/local/bin/cccc-test
sudo systemctl daemon-reload
```

## 5. Start the Whole Project With One Command

```bash
sudo cccc-test up
```

Common operations:

```bash
sudo cccc-test up
sudo cccc-test down
sudo cccc-test restart
cccc-test status
cccc-test logs
```

`cccc-test up` starts:

- `cccc-test-daemon.service`
- `cccc-test-memory-palace.service`
- `cccc-test-bootstrap.service`
- `cccc-test-web.service`
- `cccc-test-api.service`

## 6. Configure Nginx

```bash
sudo cp /srv/cccc_test/app/deploy/nginx/cccc-test.conf /etc/nginx/sites-available/cccc-test.conf
sudo ln -s /etc/nginx/sites-available/cccc-test.conf /etc/nginx/sites-enabled/cccc-test.conf
sudo nginx -t
sudo systemctl reload nginx
```

Edit `server_name` first.

## 7. Verify

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/api/health
curl http://127.0.0.1:8001/api/cccc-native/status
curl http://127.0.0.1:8858/ui/
```

Then confirm the repo-local runtime is writing state under:

```bash
/srv/cccc_test/app/.cccc_home/groups/
```

## Operational Notes

- Do not run `npm run dev` in production.
- Do not run the Windows `start_cccc_test.bat` on the server.
- Do not rely on global `site-packages` for `cccc`.
- Back up `.cccc_home/` and Memory Palace persistent data together.
