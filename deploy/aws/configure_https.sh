#!/usr/bin/env bash
set -euo pipefail

HOSTNAME="${LEDGER_HOSTNAME:?Set LEDGER_HOSTNAME to the public DNS name}"
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y apt-transport-https debian-archive-keyring debian-keyring gnupg
curl --fail --silent --show-error --location \
  https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
  | gpg --dearmor --yes --output /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl --fail --silent --show-error --location \
  https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
  --output /etc/apt/sources.list.d/caddy-stable.list
chmod 0644 /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
  /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

{
  echo "$HOSTNAME {"
  echo '    encode zstd gzip'
  echo '    reverse_proxy 127.0.0.1:8000 {'
  echo '        flush_interval -1'
  echo '    }'
  echo '}'
} > /etc/caddy/Caddyfile

caddy validate --config /etc/caddy/Caddyfile
systemctl enable caddy
systemctl restart caddy

for _ in $(seq 1 60); do
  if curl --fail --silent --show-error "https://$HOSTNAME/api/health" >/dev/null; then
    echo "Ledger HTTPS endpoint is healthy at https://$HOSTNAME."
    exit 0
  fi
  sleep 2
done

journalctl -u caddy -n 100 --no-pager || true
exit 1
