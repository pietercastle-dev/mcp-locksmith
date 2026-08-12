# node:22-bookworm, pinned by digest (multi-arch index: linux/amd64 + linux/arm64/v8).
# Bump consciously: `docker buildx imagetools inspect node:22-bookworm` for the
# current digest, re-verify it's what you expect, then update both the tag and
# this comment.
FROM node:22-bookworm@sha256:0557ac14e0d45d02ed563067b82856ca5e7aa3437fa28d98d4350ea9c3d9494a
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 age jq git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
# sops: pinned static release binary (bookworm has no sops package), verified
# against the checksums getsops publishes at
# https://github.com/getsops/sops/releases/download/${SOPS_VER}/sops-${SOPS_VER}.checksums.txt
ARG SOPS_VER=v3.10.2
ARG SOPS_SHA256_AMD64=79b0f844237bd4b0446e4dc884dbc1765fc7dedc3968f743d5949c6f2e701739
ARG SOPS_SHA256_ARM64=e91ddc04e6a78f5aed9e4fc347a279b539c43b74d99e6b8078e2f2f6f5b309f5
RUN set -eux; arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) sha="$SOPS_SHA256_AMD64" ;; \
      arm64) sha="$SOPS_SHA256_ARM64" ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /usr/local/bin/sops \
      "https://github.com/getsops/sops/releases/download/${SOPS_VER}/sops-${SOPS_VER}.linux.${arch}"; \
    echo "${sha}  /usr/local/bin/sops" | sha256sum -c -; \
    chmod +x /usr/local/bin/sops; sops --version
# Pinned to match CI's validate gate (.github/workflows/ci.yml); bump both together.
RUN npm install -g @anthropic-ai/claude-code@2.1.207 && claude --version
COPY --chmod=755 dogfood.sh /usr/local/bin/dogfood.sh
RUN useradd -m dog
# git 2.39 refuses to operate on a repo owned by a different uid; the bind-mounted
# /repo is owned by the host uid, which is backend-dependent (varies by Docker
# Desktop VM backend) and not guaranteed to match `dog`. Mark it safe so the
# fresh-clone step is deterministic across hosts.
RUN git config --system --add safe.directory /repo
USER dog
WORKDIR /home/dog
CMD ["/usr/local/bin/dogfood.sh"]
