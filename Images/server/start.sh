#!/usr/bin/env bash
set -euo pipefail

args=(--chdir /app --bind "0.0.0.0:${SERVER_PORT:-8080}" \
      --workers "${WORKERS:-2}" --worker-class sync \
      --timeout "${SERVER_TIMEOUT:-60}" --error-logfile -)

if [[ "${LOG_ACCESS:-0}" == "1" ]]; then
  args+=(--access-logfile -)
fi

if [[ -n "${TLS_CERT_FILE:-}" || -n "${TLS_KEY_FILE:-}" ]]; then
  if [[ -z "${TLS_CERT_FILE:-}" || -z "${TLS_KEY_FILE:-}" ]]; then
    echo 'TLS_CERT_FILE i TLS_KEY_FILE muszą być podane razem' >&2
    exit 2
  fi
  if [[ ! -r "$TLS_CERT_FILE" || ! -r "$TLS_KEY_FILE" ]]; then
    echo 'Certyfikat lub klucz TLS jest nieczytelny' >&2
    exit 2
  fi
  args+=(--certfile "$TLS_CERT_FILE" --keyfile "$TLS_KEY_FILE")
fi

exec gunicorn "${args[@]}" flask_app:app
