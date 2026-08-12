FROM node:22-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 age jq git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
# sops: pinned static release binary (bookworm has no sops package)
ARG SOPS_VER=v3.10.2
RUN set -eux; arch="$(dpkg --print-architecture)"; \
    curl -fsSL -o /usr/local/bin/sops \
      "https://github.com/getsops/sops/releases/download/${SOPS_VER}/sops-${SOPS_VER}.linux.${arch}"; \
    chmod +x /usr/local/bin/sops; sops --version
RUN npm install -g @anthropic-ai/claude-code && claude --version
COPY --chmod=755 dogfood.sh /usr/local/bin/dogfood.sh
RUN useradd -m dog
USER dog
WORKDIR /home/dog
CMD ["/usr/local/bin/dogfood.sh"]
