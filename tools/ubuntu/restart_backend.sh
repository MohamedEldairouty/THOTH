#!/usr/bin/env bash
# Restart the backend systemd service — use this after a backend code change.
# The Linux equivalent of restart_backend.bat (which kills uvicorn for the
# .bat auto-restart loop to respawn).

echo "Restarting thoth-backend service..."
systemctl --user restart thoth-backend

echo "Waiting 20 s for uvicorn + Whisper preload..."
sleep 20

status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health || echo "000")
if [ "$status" = "200" ]; then
    echo "[OK] Backend is back up (HTTP $status)."
else
    echo "[WARN] Backend not healthy (HTTP $status). Check $HOME/THOTH/thoth_backend.log"
    echo "       journalctl --user -u thoth-backend -n 50"
fi
