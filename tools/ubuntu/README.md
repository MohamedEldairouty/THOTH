# Ubuntu demo launchers

Auto-start scripts used on the demo laptop (Ubuntu side of the dual-boot).
They keep the THOTH backend + Cloudflare Tunnel running 24/7 so the
public URL `https://thoth.thoth-gem.com` always resolves — same tunnel
UUID and DNS as the Windows side, so the same URL works regardless of
which OS you booted.

> Paths assume the repo lives at `$HOME/THOTH/`. If you cloned elsewhere,
> edit `thoth-backend.service` (the `ExecStart=` line) and the `cd`
> inside `start_thoth_backend.sh`.

## Files

| File | Purpose |
|---|---|
| `start_thoth_backend.sh` | Sources ROS + activates the runtime venv, sets UTF-8, runs `uvicorn app.main:app --host 0.0.0.0 --port 8001`. systemd's `Restart=always` auto-respawns it on exit — no shell loop needed (unlike the Windows `.bat`). |
| `thoth-backend.service` | systemd **user** unit that runs the launcher. Installed into `~/.config/systemd/user/`. |
| `restart_backend.sh` | Restarts the backend service. Use after pushing a backend code change. Linux counterpart of `restart_backend.bat`. |
| `restart_tunnel.sh` | Restarts the cloudflared system service. Linux counterpart of `restart_tunnel.bat`. |

> cloudflared itself is installed as a **system** service via
> `sudo cloudflared service install`, using the credentials/config in
> `/etc/cloudflared/`. No bash loop needed — systemd handles restart.

## One-time install on the demo laptop

1. **System packages**
   ```bash
   sudo apt update && sudo apt install -y postgresql postgresql-contrib \
     ffmpeg python3-venv build-essential git nodejs npm
   ```
   (Node 20+ — use NodeSource if apt ships an older version.)

2. **Backend venv** — `python3 -m venv .venv` inside `web-app/backend/`,
   then `pip install -r requirements.txt`. Copy your `.env` (with
   `GEMINI_API_KEY` and `DATABASE_URL`) into the same folder.

3. **Frontend build** — `npm install && npm run build` inside
   `web-app/frontend/`. The backend mounts `dist/` on startup so one
   port serves both API and UI.

4. **cloudflared** — install from the Cloudflare apt repo, then drop
   your tunnel credentials (`<UUID>.json`, `cert.pem`, and a `config.yml`
   pointing at `localhost:8001`) into `/etc/cloudflared/`.

5. **Install the backend systemd user service**
   ```bash
   chmod +x ~/THOTH/tools/ubuntu/*.sh
   mkdir -p ~/.config/systemd/user
   cp ~/THOTH/tools/ubuntu/thoth-backend.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now thoth-backend
   sudo loginctl enable-linger "$USER"   # runs at boot without login
   ```

6. **Install the cloudflared system service**
   ```bash
   sudo cloudflared --config /etc/cloudflared/config.yml service install
   sudo systemctl enable --now cloudflared
   ```

7. **Verify**
   ```bash
   systemctl --user status thoth-backend
   sudo systemctl status cloudflared
   curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/api/health
   curl -s -o /dev/null -w "%{http_code}\n" https://thoth.thoth-gem.com/api/health
   ```
   Both should return `200`.

## Day-to-day workflow

| When | What to run |
|---|---|
| Pushed a backend `.py` change | `~/THOTH/tools/ubuntu/restart_backend.sh` |
| Rebuilt the frontend (`npm run build`) | Hard-refresh the browser (Ctrl+F5). No service restart. |
| Tunnel acts up | `~/THOTH/tools/ubuntu/restart_tunnel.sh` |
| Something exotic | Both services self-heal via systemd; usually do nothing |

## Logs

- `~/THOTH/thoth_backend.log` — uvicorn stdout/stderr (appended by systemd)
- `journalctl --user -u thoth-backend -n 50` — backend systemd journal
- `sudo journalctl -u cloudflared -n 50` — tunnel connection events

## Don't have both OSes running cloudflared at once

You're dual-boot, so only one OS is up at a time — automatic. If you ever
run them in parallel (Ubuntu in a VM, etc.), stop one tunnel first:
- Windows: `sc stop Cloudflared`
- Ubuntu:  `sudo systemctl stop cloudflared`

## Windows counterpart

The Windows side uses `.bat` loops + `.vbs` hidden launchers in the
Startup folder. See `tools/windows/README.md`. Same tunnel UUID,
same DNS, same URL.
