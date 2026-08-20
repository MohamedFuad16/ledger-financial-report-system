#!/usr/bin/env bash
set -euo pipefail

exec > >(tee /var/log/ledger-bootstrap.log | logger -t ledger-bootstrap -s 2>/dev/console) 2>&1

REGION="${AWS_REGION:-ap-northeast-1}"
REPOSITORY="${LEDGER_REPOSITORY:-https://github.com/MohamedFuad16/ledger-financial-report-system.git}"
TOKEN_PARAMETER="${LEDGER_TOKEN_PARAMETER:-/ledger/backend/admin-token}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y awscli ca-certificates curl git libgl1 libglib2.0-0 python3-venv

if ! id ledger >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash ledger
fi

if ! swapon --show | grep -q /swapfile; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

rm -rf /opt/ledger
git clone --depth 1 "$REPOSITORY" /opt/ledger
chown -R ledger:ledger /opt/ledger

runuser -u ledger -- python3 -m venv /opt/ledger/.venv
runuser -u ledger -- /opt/ledger/.venv/bin/pip install --upgrade pip wheel
runuser -u ledger -- /opt/ledger/.venv/bin/pip install -r /opt/ledger/requirements.txt

install -d -m 0750 -o ledger -g ledger /etc/ledger
ADMIN_TOKEN="$(aws ssm get-parameter --region "$REGION" --name "$TOKEN_PARAMETER" --with-decryption --query 'Parameter.Value' --output text)"
{
  echo "AWS_REGION=$REGION"
  echo 'CORS_ALLOWED_ORIGINS=*'
  echo "LEDGER_ADMIN_TOKEN=$ADMIN_TOKEN"
  echo 'PYTHONUNBUFFERED=1'
} > /etc/ledger/backend.env
chmod 0640 /etc/ledger/backend.env
chown root:ledger /etc/ledger/backend.env

install -m 0644 /opt/ledger/deploy/aws/ledger-backend.service /etc/systemd/system/ledger-backend.service
systemctl daemon-reload
systemctl enable --now ledger-backend.service

for _ in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8000/api/health >/dev/null; then
    echo 'Ledger backend is healthy on 127.0.0.1:8000.'
    exit 0
  fi
  sleep 2
done

systemctl status ledger-backend.service --no-pager || true
journalctl -u ledger-backend.service -n 100 --no-pager || true
exit 1
