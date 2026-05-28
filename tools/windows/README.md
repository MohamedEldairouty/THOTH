# Windows demo launchers

Auto-start scripts used on the demo laptop (Windows side of the dual-boot).
They keep the THOTH backend + Cloudflare Tunnel running 24/7 so the
public URL `https://thoth.thoth-gem.com` always resolves.

> All paths are hard-coded to `D:\Prog\Thoth\...`. If you cloned this repo
> to a different drive or username, edit the paths inside each file.

## Files

| File | Purpose |
|---|---|
| `start_thoth_backend.bat` | Auto-restarting uvicorn loop. Activates the runtime venv, forces UTF-8 stdio, runs `uvicorn app.main:app --host 0.0.0.0 --port 8001`, restarts in 5 s if it exits for any reason. |
| `start_cloudflared.bat` | Auto-restarting cloudflared loop. Runs the named tunnel `thoth` defined in `%USERPROFILE%\.cloudflared\config.yml`. |
| `start_thoth_backend_hidden.vbs` | One-liner VBScript wrapper that launches the bat with no visible cmd window. Used in the Startup folder. |
| `start_cloudflared_hidden.vbs` | Same idea for the tunnel. |
| `restart_backend.bat` | Kills uvicorn on port 8001 so the restart loop respawns it (use after pushing a backend code change). |
| `restart_tunnel.bat` | Same idea for cloudflared. |

## One-time install on the demo laptop

1. **Postgres** — install via the official Windows installer, leave it as
   a service (auto-starts on boot).

2. **ffmpeg** — extract to `C:\ffmpeg\` so the resolver in
   `voice_service.py` finds it.

3. **Backend venv** — `python -m venv .venv` inside
   `web-app\backend\`, then `pip install -r requirements.txt`.

4. **Frontend build** — `npm install && npm run build` inside
   `web-app\frontend\`. The backend mounts `dist/` on startup so one
   port serves both API and UI.

5. **cloudflared** — download the MSI from
   <https://github.com/cloudflare/cloudflared/releases>, install,
   then `cloudflared tunnel login` and copy your tunnel UUID json +
   `cert.pem` + the `config.yml` template into
   `%USERPROFILE%\.cloudflared\`.

6. **Auto-start on login** — open `shell:startup` (Win+R), drop
   shortcuts to the two `*_hidden.vbs` files in there. Reboot to
   confirm both processes come up by themselves.

## Day-to-day workflow

| When | What to do |
|---|---|
| You pushed a backend `.py` change | Double-click `restart_backend.bat` |
| You rebuilt the frontend (`npm run build`) | Hard-refresh browser (Ctrl+F5). No process kill needed. |
| Tunnel acts up | Double-click `restart_tunnel.bat` |
| Something exotic | Both loops self-heal in ~5 s, so usually do nothing |

## Logs

Each loop appends to a log file at the repo root:

- `D:\Prog\Thoth\thoth_backend.log` — uvicorn stdout/stderr
- `D:\Prog\Thoth\cloudflared.log` — tunnel connection events

Both are gitignored.

## Linux equivalent

For the Ubuntu side of the dual-boot, the same architecture is
implemented as **systemd services** instead of `.bat` loops. See
`web-app/README.md` for those steps.
