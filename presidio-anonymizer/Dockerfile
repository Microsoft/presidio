# ---- builder: uv and the build toolchain exist only in this stage ----
FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS builder

ENV PIP_NO_CACHE_DIR=1
# Install the locked dependencies into the system environment (no venv).
ENV UV_PROJECT_ENVIRONMENT=/usr/local
ENV UV_COMPILE_BYTECODE=1

# uv is copied in as a static binary rather than installed with pip, so it never
# reaches the runtime image and its advisories never apply to it. It is staged in
# /usr/bin, outside the /usr/local tree the runtime stage copies from, so the
# ~45MB binary is never baked into a runtime layer.
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /usr/bin/uv

WORKDIR /app

COPY ./pyproject.toml ./uv.lock /app/
# Install exactly the locked dependency graph (main + server extra, no dev
# group); the project itself is run from the copied source, not installed.
RUN uv sync --locked --no-cache --no-default-groups --extra server --no-install-project

# Strip packaging tooling here so the layers the runtime stage copies never
# contain it. The runtime stage repeats the removal for the copies that ship in
# its own base image.
RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true \
    && rm -rf /usr/local/bin/pip* /usr/local/bin/wheel \
    /usr/local/lib/python3.14/site-packages/pip* \
    /usr/local/lib/python3.14/site-packages/setuptools* \
    /usr/local/lib/python3.14/site-packages/wheel* \
    /usr/local/lib/python3.14/site-packages/_distutils_hack \
    /usr/local/lib/python3.14/site-packages/distutils-precedence.pth

# ---- runtime ----
FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS runtime

ENV PORT=3000
ENV WORKERS=1
ENV PYTHONDONTWRITEBYTECODE=1

# Apply every Debian security update published since the base image was built.
# curl is deliberately not installed: it was only used by the health check, and
# it pulls in a large TLS/auth dependency tree (gnutls, krb5, libssh2, nghttp2,
# libtasn1, ldap, sasl) that dominates the image's vulnerability count.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Remove the Python packaging tooling. It is only needed at build time, and this
# must run after every COPY from the builder: copying /usr/local/bin would
# otherwise reinstate the binaries that were just removed.
RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true \
    && rm -rf /usr/local/bin/pip* /usr/local/bin/uv* /usr/local/bin/wheel \
    /usr/local/lib/python3.14/site-packages/pip* \
    /usr/local/lib/python3.14/site-packages/setuptools* \
    /usr/local/lib/python3.14/site-packages/wheel* \
    /usr/local/lib/python3.14/site-packages/_distutils_hack \
    /usr/local/lib/python3.14/site-packages/distutils-precedence.pth

WORKDIR /app

COPY . /app/

# Create a non-root user and set ownership
RUN useradd -m -u 1001 presidio && chown -R presidio:presidio /app

USER 1001

EXPOSE ${PORT}
# Uses the Python standard library rather than curl, which is no longer installed.
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:'+os.environ['PORT']+'/health',timeout=2).status==200 else 1)"
CMD ["./entrypoint.sh"]
