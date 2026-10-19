# ---- builder: uv and the build toolchain exist only in this stage ----
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS builder

ARG NLP_CONF_FILE=presidio_analyzer/conf/default.yaml
ARG ANALYZER_CONF_FILE=presidio_analyzer/conf/default_analyzer.yaml
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
# group, project itself not installed — it is run from the copied source).
# Splitting this from the source COPY keeps the dependency layer cached until
# pyproject.toml/uv.lock change.
RUN uv sync --locked --no-cache --no-default-groups --extra server --no-install-project

# install nlp models specified in NLP_CONF_FILE or via nlp_configuration in ANALYZER_CONF_FILE
COPY ${ANALYZER_CONF_FILE} /app/${ANALYZER_CONF_FILE}
COPY ${NLP_CONF_FILE} /app/${NLP_CONF_FILE}
COPY ./install_nlp_models.py /app/

RUN python install_nlp_models.py \
    --conf_file ${NLP_CONF_FILE} \
    --analyzer_conf_file ${ANALYZER_CONF_FILE}

# Strip packaging tooling here, after the spacy model download (which shells out
# to pip), so the layers the runtime stage copies never contain it. The runtime
# stage repeats the removal for the copies that ship in its own base image.
RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true \
    && rm -rf /usr/local/bin/pip* /usr/local/bin/wheel \
    /usr/local/lib/python3.12/site-packages/pip* \
    /usr/local/lib/python3.12/site-packages/setuptools* \
    /usr/local/lib/python3.12/site-packages/wheel* \
    /usr/local/lib/python3.12/site-packages/_distutils_hack \
    /usr/local/lib/python3.12/site-packages/distutils-precedence.pth

# ---- runtime ----
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS runtime

ARG NLP_CONF_FILE=presidio_analyzer/conf/default.yaml
ARG ANALYZER_CONF_FILE=presidio_analyzer/conf/default_analyzer.yaml
ARG RECOGNIZER_REGISTRY_CONF_FILE=presidio_analyzer/conf/default_recognizers.yaml

ENV ANALYZER_CONF_FILE=${ANALYZER_CONF_FILE}
ENV RECOGNIZER_REGISTRY_CONF_FILE=${RECOGNIZER_REGISTRY_CONF_FILE}
ENV NLP_CONF_FILE=${NLP_CONF_FILE}

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

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Remove the Python packaging tooling. It is only needed at build time, and this
# must run after every COPY from the builder: copying /usr/local/bin would
# otherwise reinstate the binaries that were just removed.
RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null || true \
    && rm -rf /usr/local/bin/pip* /usr/local/bin/uv* /usr/local/bin/wheel \
    /usr/local/lib/python3.12/site-packages/pip* \
    /usr/local/lib/python3.12/site-packages/setuptools* \
    /usr/local/lib/python3.12/site-packages/wheel* \
    /usr/local/lib/python3.12/site-packages/_distutils_hack \
    /usr/local/lib/python3.12/site-packages/distutils-precedence.pth

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
