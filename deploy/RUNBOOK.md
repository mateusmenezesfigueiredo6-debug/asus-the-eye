# Runbook — servir o THE EYE

O "servir" deixou de morar só na cabeça de uma máquina: está aqui, versionado.
Postura de segurança: **falha-fechada** — expor sem token é impossível por
construção.

## Local (desenvolvimento, sem exposição)

```bash
asus-theye serve            # http://127.0.0.1:8712, só loopback, sem token
```

## Exposto (rede) — exige token

Gere um token forte e sirva. Sem `THE_EYE_DASHBOARD_TOKEN`, o comando **recusa**:

```bash
export THE_EYE_DASHBOARD_TOKEN=$(openssl rand -hex 32)
asus-theye serve --expose --port 8712
```

Cliente:

```bash
curl -H "authorization: Bearer $THE_EYE_DASHBOARD_TOKEN" http://HOST:8712/markets
curl http://HOST:8712/health     # liveness é sempre livre (não expõe dado)
```

## Docker / Compose

```bash
export THE_EYE_DASHBOARD_TOKEN=$(openssl rand -hex 32)
docker compose -f deploy/compose.yaml up --build   # publica só em 127.0.0.1:8712
```

Container: não-root, `read_only`, `cap_drop: ALL`, `no-new-privileges`,
healthcheck em `/health`.

## systemd (produção numa VM)

```bash
sudo cp deploy/the-eye-dashboard.service /etc/systemd/system/
sudo systemctl edit the-eye-dashboard   # drop-in com Environment=THE_EYE_DASHBOARD_TOKEN=...
sudo systemctl enable --now the-eye-dashboard
```

Sem o token no drop-in, o serviço **não sobe** — é o comportamento desejado.

## Pendências do dono (fora deste runbook)

- **Passphrase da trava de publicação** (`scripts/publish_lock.py`) antes de
  qualquer publicação L3+.
- **Terminação TLS** (reverse proxy / Cloudflare) na frente, se exposto à
  internet aberta — este serviço fala HTTP; o token protege o acesso, não o
  transporte.
