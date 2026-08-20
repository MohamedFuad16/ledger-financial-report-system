#!/usr/bin/env bash
set -euo pipefail

exec > >(tee /var/log/ledger-bootstrap.log | logger -t ledger-bootstrap -s 2>/dev/console) 2>&1

REGION="${AWS_REGION:-ap-northeast-1}"
REPOSITORY="${LEDGER_REPOSITORY:-https://github.com/MohamedFuad16/ledger-financial-report-system.git}"
TOKEN_PARAMETER="${LEDGER_TOKEN_PARAMETER:-/ledger/backend/admin-token}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git libgl1 libglib2.0-0 python3-venv unzip

if ! command -v aws >/dev/null 2>&1; then
  curl --fail --silent --show-error --location \
    https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip \
    --output /tmp/awscliv2.zip
  rm -rf /tmp/aws /tmp/awscliv2
  unzip -q /tmp/awscliv2.zip -d /tmp/awscliv2
  /tmp/awscliv2/aws/install
fi

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
# The backend has no GPU. Installing the CPU wheel first prevents pip from
# pulling several gigabytes of unused CUDA libraries through Docling.
runuser -u ledger -- /opt/ledger/.venv/bin/pip install --no-cache-dir \
  torch torchvision --index-url https://download.pytorch.org/whl/cpu
runuser -u ledger -- /opt/ledger/.venv/bin/pip install --no-cache-dir -r /opt/ledger/requirements.txt

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
