# syntax=docker/dockerfile:1
#
# Sovereignty container image: the `sov` CLI plus the audit/anchor daemon.
#
#   docker run --rm -it -v sov-data:/data ghcr.io/mcp-tool-shop-org/sovereignty tutorial
#   docker compose up -d        # daemon, see compose.yaml
#
# Persistent state is everything under /data/.sov (games, proofs, anchors,
# season, wallet seed, daemon handshake). Mount a volume or a host directory
# on /data or nothing survives the container.

ARG PYTHON_IMAGE=python:3.13-slim-trixie@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b

# --- build: produce the wheel from source --------------------------------
FROM ${PYTHON_IMAGE} AS build
WORKDIR /src
RUN pip install --no-cache-dir "build==1.3.0"
COPY pyproject.toml README.md LICENSE ./
COPY sov_engine/ sov_engine/
COPY sov_transport/ sov_transport/
COPY sov_cli/ sov_cli/
COPY sov_daemon/ sov_daemon/
RUN python -m build --wheel --outdir /dist

# --- runtime --------------------------------------------------------------
FROM ${PYTHON_IMAGE}

LABEL org.opencontainers.image.title="sovereignty" \
      org.opencontainers.image.description="Sovereignty: a strategy game about governance, trust, and trade. CLI plus the XRPL audit/anchor daemon." \
      org.opencontainers.image.source="https://github.com/mcp-tool-shop-org/sovereignty" \
      org.opencontainers.image.url="https://mcp-tool-shop-org.github.io/sovereignty/" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Daemon defaults. The bind is widened to the container's own network
    # namespace only; publish the port to 127.0.0.1 on the host.
    SOV_DAEMON_HOST=0.0.0.0 \
    SOV_DAEMON_PORT=47823 \
    SOV_DAEMON_NETWORK=testnet \
    SOV_DAEMON_READONLY=1

COPY --from=build /dist/*.whl /tmp/
RUN whl="$(ls /tmp/sovereignty_game-*.whl)" \
 && pip install --no-cache-dir "${whl}[xrpl,daemon]" \
 && rm -f /tmp/*.whl \
 && useradd --uid 1000 --user-group --home-dir /data --no-create-home --shell /usr/sbin/nologin sov \
 && mkdir -p /data \
 && chown sov:sov /data

COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/sov-entrypoint
COPY --chmod=0644 docker/healthcheck.py /usr/local/lib/sov-healthcheck.py

USER sov
WORKDIR /data
VOLUME ["/data"]
EXPOSE 47823

# Only meaningful for the daemon; CLI one-shots exit before the first probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "/usr/local/lib/sov-healthcheck.py"]

ENTRYPOINT ["/usr/local/bin/sov-entrypoint"]
CMD ["daemon"]
