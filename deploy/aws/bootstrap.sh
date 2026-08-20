#!/usr/bin/env bash
set -euo pipefail

exec > >(tee /var/log/ledger-bootstrap.log | logger -t ledger-bootstrap -s 2>/dev/console) 2>&1

REGION="${AWS_REGION:-ap-northeast-1}"
REPOSITORY="${LEDGER_REPOSITORY:-https://github.com/MohamedFuad16/ledger-financial-report-system.git}"
UPSTASH_URL_PARAMETER="${LEDGER_UPSTASH_URL_PARAMETER:-/ledger/traffic/upstash-rest-url}"
UPSTASH_TOKEN_PARAMETER="${LEDGER_UPSTASH_TOKEN_PARAMETER:-/ledger/traffic/upstash-rest-token}"
TRAFFIC_EMAIL_PARAMETER="${LEDGER_TRAFFIC_EMAIL_PARAMETER:-/ledger/traffic/notify-email}"
CORS_ORIGINS="${LEDGER_CORS_ALLOWED_ORIGINS:-https://ledger-financial-report-system.vercel.app,https://assignment.mohamedfuad.com}"

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
UPSTASH_REDIS_REST_URL="$(aws ssm get-parameter --region "$REGION" --name "$UPSTASH_URL_PARAMETER" --query 'Parameter.Value' --output text)"
UPSTASH_REDIS_REST_TOKEN="$(aws ssm get-parameter --region "$REGION" --name "$UPSTASH_TOKEN_PARAMETER" --with-decryption --query 'Parameter.Value' --output text)"
TRAFFIC_NOTIFY_EMAIL="$(aws ssm get-parameter --region "$REGION" --name "$TRAFFIC_EMAIL_PARAMETER" --query 'Parameter.Value' --output text)"
{
  echo "AWS_REGION=$REGION"
  echo "CORS_ALLOWED_ORIGINS=$CORS_ORIGINS"
  echo "UPSTASH_REDIS_REST_URL=$UPSTASH_REDIS_REST_URL"
  echo "UPSTASH_REDIS_REST_TOKEN=$UPSTASH_REDIS_REST_TOKEN"
  echo "TRAFFIC_NOTIFY_EMAIL=$TRAFFIC_NOTIFY_EMAIL"
  echo "TRAFFIC_FROM_EMAIL=$TRAFFIC_NOTIFY_EMAIL"
  echo 'PYTHONUNBUFFERED=1'
} > /etc/ledger/backend.env
chmod 0640 /etc/ledger/backend.env
chown root:ledger /etc/ledger/backend.env

install -m 0644 /opt/ledger/deploy/aws/ledger-backend.service /etc/systemd/system/ledger-backend.service
systemctl daemon-reload
systemctl enable --now ledger-backend.service
rm -rf /root/.cache/pip /tmp/awscliv2 /tmp/awscliv2.zip

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
