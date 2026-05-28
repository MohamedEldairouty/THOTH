#!/usr/bin/env bash
# Restart the cloudflared system service.
# The Linux equivalent of restart_tunnel.bat.

echo "Restarting cloudflared..."
sudo systemctl restart cloudflared

echo "Waiting 10 s for tunnel reconnect..."
sleep 10

if systemctl is-active --quiet cloudflared; then
    echo "[OK] cloudflared is back. URL should resolve within ~10 s."
else
    echo "[WARN] cloudflared not active. Check:"
    echo "       sudo journalctl -u cloudflared -n 30"
fi
