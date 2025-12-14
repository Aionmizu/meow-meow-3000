#!/usr/bin/env bash
# Meow-Meow-3000 — Automated deploy on Kali/Debian-based Linux
# Usage (defaults OK for local DVWA on same VM):
#   bash deploy_kali.sh
# Or customize:
#   bash deploy_kali.sh \
#     --repo https://github.com/Aionmizu/meow-meow-3000.git \
#     --branch main \
#     --install-dir /opt/meow-meow-3000 \
#     --backend http://127.0.0.1:8080 \
#     --mode IPS \
#     --waf-port 80 \
#     --dash-port 5001

set -euo pipefail

# Defaults
REPO_URL="https://github.com/Aionmizu/meow-meow-3000.git"
BRANCH="main"
INSTALL_DIR="/opt/meow-meow-3000"
WAF_BACKEND="http://127.0.0.1:8080"
WAF_MODE="IPS"
WAF_LISTEN_HOST="0.0.0.0"
WAF_LISTEN_PORT="80"
WAF_DASHBOARD_HOST="0.0.0.0"
WAF_DASHBOARD_PORT="5001"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2;;
    --branch) BRANCH="$2"; shift 2;;
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --backend) WAF_BACKEND="$2"; shift 2;;
    --mode) WAF_MODE="$2"; shift 2;;
    --waf-host) WAF_LISTEN_HOST="$2"; shift 2;;
    --waf-port) WAF_LISTEN_PORT="$2"; shift 2;;
    --dash-host) WAF_DASHBOARD_HOST="$2"; shift 2;;
    --dash-port) WAF_DASHBOARD_PORT="$2"; shift 2;;
    -h|--help)
      grep '^#' "$0" | sed -e 's/^# \{0,1\}//'; exit 0;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# Root check
if [[ $EUID -ne 0 ]]; then
  echo "[i] This script needs root. Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

# 1) Install prerequisites
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip git curl ca-certificates ufw

# 2) Clone or update repo in INSTALL_DIR
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "[i] Repo exists, updating: $INSTALL_DIR"
  git -C "$INSTALL_DIR" fetch --all --prune
  git -C "$INSTALL_DIR" checkout "$BRANCH" || true
  git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
else
  echo "[i] Cloning $REPO_URL to $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

# 3) Create venv and install project
cd "$INSTALL_DIR"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
# Install project in editable mode to expose console scripts and run by module
pip install -e .

deactivate

# 4) Create environment file for services
ENV_FILE="/etc/default/meow-waf"
cat > "$ENV_FILE" <<EOF
# Environment for Meow-Meow-3000 WAF services
WAF_BACKEND=${WAF_BACKEND}
WAF_MODE=${WAF_MODE}
WAF_THRESHOLD_IDS=5
WAF_THRESHOLD_BLOCK=9
WAF_LISTEN_HOST=${WAF_LISTEN_HOST}
WAF_LISTEN_PORT=${WAF_LISTEN_PORT}
WAF_DASHBOARD_HOST=${WAF_DASHBOARD_HOST}
WAF_DASHBOARD_PORT=${WAF_DASHBOARD_PORT}
WAF_DATA_DIR=${INSTALL_DIR}/data
WAF_LOGS_FILE=${INSTALL_DIR}/data/logs.json
WAF_ALLOW_QUERY_MODE_SWITCH=1
EOF
chmod 0644 "$ENV_FILE"

# 5) Systemd services (write unit files)
cat > /etc/systemd/system/meow-waf.service <<EOF
[Unit]
Description=Meow-Meow-3000 WAF Proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/meow-waf
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/.venv/bin/python -m waf.run_waf
Restart=on-failure
RestartSec=3
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 /etc/systemd/system/meow-waf.service

cat > /etc/systemd/system/meow-waf-dashboard.service <<EOF
[Unit]
Description=Meow-Meow-3000 WAF Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/meow-waf
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/.venv/bin/python -m waf.run_dashboard
Restart=on-failure
RestartSec=3
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 /etc/systemd/system/meow-waf-dashboard.service

# 6) Firewall (UFW) — open ports if UFW is active
if ufw status | grep -q "Status: active"; then
  ufw allow "$WAF_LISTEN_PORT"/tcp || true
  ufw allow "$WAF_DASHBOARD_PORT"/tcp || true
fi

# 7) Start services
systemctl daemon-reload
systemctl enable meow-waf.service meow-waf-dashboard.service
systemctl restart meow-waf.service meow-waf-dashboard.service

# 8) Smoke tests
sleep 1
set +e
HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "http://127.0.0.1:${WAF_LISTEN_PORT}/healthz")
set -e

echo ""
echo "================ Deployment Complete ================"
echo "Repo:      $REPO_URL @ $BRANCH"
echo "Install:   $INSTALL_DIR"
echo "WAF:       http://<this-host>:${WAF_LISTEN_PORT}/  (healthz: /healthz)"
echo "Dashboard: http://<this-host>:${WAF_DASHBOARD_PORT}/dashboard"
echo "Backend:   ${WAF_BACKEND}"
echo "Mode:      ${WAF_MODE}"
echo "Health:    HTTP ${HTTP_CODE}"
echo "Logs:      ${INSTALL_DIR}/data/logs.json"
echo "Service:   meow-waf.service, meow-waf-dashboard.service"
echo "====================================================="
