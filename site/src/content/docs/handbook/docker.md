---
title: Docker
description: Run the Sovereignty CLI and daemon in a container, with saves that persist and a desktop app that can attach.
sidebar:
  order: 6
---

Sovereignty ships a container image with the `sov` console and the audit/anchor daemon:

```
ghcr.io/mcp-tool-shop-org/sovereignty
```

It is built for `linux/amd64` and `linux/arm64`, tagged by version (`2.3.3`, `2.3`, `2`) and `latest`. Each release image carries a build-provenance attestation.

You don't need Docker to play. It suits two cases: you want the console without installing Python, or you want the daemon running as a supervised service that restarts on its own.

## Where your game lives

The game remembers everything in one folder, `.sov/`. In the image that folder is `/data/.sov`:

| Path | What it holds |
|---|---|
| `games/<game-id>/state.json` | The game itself |
| `games/<game-id>/proofs/` | One proof per round, plus `FINAL` |
| `games/<game-id>/anchors.json` | Which XRPL transaction anchored which round |
| `games/<game-id>/pending-anchors.json` | Rounds waiting to be anchored |
| `active-game` | Which save `sov turn` and `sov status` act on |
| `season.json` | Season standings across games |
| `wallet_seed.txt` | Your XRPL wallet seed, if you made one (owner-only permissions) |
| `daemon.json` | The running daemon's port and bearer token |

**Mount something on `/data`.** Without a volume, a container's `.sov/` is thrown away when the container is removed, and your game goes with it.

## Play from the console

A named volume keeps your saves between runs:

```bash
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty play campfire_v1
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty turn
docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty status
```

Every argument after the image name goes to `sov`, so any command in the [Reference](/sovereignty/handbook/reference/) works. To keep the files in a folder you can see instead, mount the folder:

```bash
docker run --rm -it -v "$PWD:/data" ghcr.io/mcp-tool-shop-org/sovereignty status
```

On Linux, add `--user "$(id -u):$(id -g)"` so the files the container writes belong to you.

## Run the daemon

The repository includes a [`compose.yaml`](https://github.com/mcp-tool-shop-org/sovereignty/blob/main/compose.yaml). From a checkout, or with that file copied into a folder:

```bash
docker compose up -d          # start the daemon
docker compose ps             # healthy once /health answers
docker compose logs -f        # follow the log
docker compose stop           # graceful shutdown
```

Compose runs `sov` commands against the same saves:

```bash
docker compose run --rm sov play campfire_v1
docker compose run --rm sov games
docker compose run --rm sov doctor
```

Out of the box the daemon is **readonly** (audit reads only, no wallet loaded), talks to **testnet**, and listens on **`127.0.0.1:47823`** on your machine. Nothing outside your computer can reach it. Every request also needs the bearer token from `.sov/daemon.json`:

```bash
TOKEN=$(docker compose exec -T sov python -c "import json;print(json.load(open('.sov/daemon.json'))['token'])")
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:47823/health
```

### Settings

Set these in your shell or in a `.env` file next to `compose.yaml`:

| Variable | Default | Effect |
|---|---|---|
| `SOV_DATA` | `sov-data` | Source of `/data`: a named volume, or a host folder such as `./`. |
| `SOV_DAEMON_PORT` | `47823` | Port inside the container and on the host. They must match, because clients dial the port recorded in the handshake. |
| `SOV_DAEMON_NETWORK` | `testnet` | `testnet`, `devnet`, or `mainnet`. |
| `SOV_DAEMON_READONLY` | `1` | `0` turns on the anchor endpoints. |
| `SOV_DAEMON_TOKEN` | fresh each start | A fixed token lets clients reconnect after a restart without re-reading the handshake. |
| `SOV_DAEMON_LOG_FORMAT` | `human` | `json` emits one structured line per event. |
| `SOV_LOG_LEVEL` | `WARNING` | Python log level for the daemon. |
| `SOV_IMAGE_TAG` | `latest` | Pin an image version, e.g. `2.3.3`. |

## Attach the desktop app

The Audit Viewer finds its daemon by reading `.sov/daemon.json` in the project folder it opens. Mount that folder as `/data`, and the containerized daemon writes its handshake where the app looks:

```bash
cd ~/games/friday-night
SOV_DATA=./ docker compose -f /path/to/sovereignty/compose.yaml up -d
```

The handshake records port `47823`, which Compose publishes on your loopback, so the app connects as if the daemon were local.

While the container owns the daemon, use `docker compose` to start, stop and check it. Don't use `sov daemon start`, `stop` or `status` from the host. The host CLI can't see processes inside the container, so it reports the handshake as stale, and `sov daemon start` clears a stale handshake before starting its own daemon.

## Anchor from a container

Anchoring writes XRPL transactions, so it needs a wallet. The simplest path keeps the seed in the volume, where `sov wallet` puts it:

```bash
docker compose run --rm sov wallet             # testnet wallet, funded from the faucet
SOV_DAEMON_READONLY=0 docker compose up -d     # daemon now loads .sov/wallet_seed.txt
```

To keep the seed out of the volume, pass it as a Docker secret. Uncomment the `secrets` blocks in `compose.yaml`, put the seed in `xrpl_seed.txt` beside it, and set:

```yaml
environment:
  SOV_DAEMON_READONLY: "0"
  SOV_DAEMON_SIGNER_FILE: /run/secrets/xrpl_seed
```

The daemon reads the seed once at start and holds it in memory. It never writes the seed to `daemon.json` or to the log. Before you set `SOV_DAEMON_NETWORK=mainnet`, remember that mainnet anchors cost real XRP.

## What the container locks down

- The daemon port is published to `127.0.0.1` only.
- Every request needs the bearer token; unauthenticated calls get `401`.
- The daemon is readonly unless you turn anchoring on.
- It runs as a non-root user (`uid 1000`) with a read-only root filesystem, no Linux capabilities, and `no-new-privileges`.
- The image has a healthcheck. Under Compose it also runs behind an init process and restarts unless you stop it.

Inside the container the daemon binds `0.0.0.0` so Docker can forward the port. That applies only when `SOV_DAEMON_HOST` is set, which the image does. A daemon you start with `sov daemon start` still binds `127.0.0.1` and never inherits that variable.

## Verify the image

```bash
gh attestation verify oci://ghcr.io/mcp-tool-shop-org/sovereignty:2.3.3 \
  --repo mcp-tool-shop-org/sovereignty
```

A clean result proves the image was built by this repository's release workflow from a specific commit.
